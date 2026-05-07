/**
 * CogniCare mock backend server
 * Mimics the Python RAG API so the app can be tested without the real backend.
 *
 * Usage:
 *   node mock_server.js
 *
 * Test with curl:
 *   curl http://localhost:8000/health
 *   curl -X POST http://localhost:8000/chat \
 *        -H "Content-Type: application/json" \
 *        -d '{"patient_id":1,"message":"What are early signs of Alzheimer?"}'
 *   curl -X POST http://localhost:8000/voice \
 *        -F "patient_id=1" -F "audio=@/tmp/any.wav"
 *   curl -X POST http://localhost:8000/reports/generate/1
 */

const http         = require('http');
const fs           = require('fs');
const path         = require('path');
const os           = require('os');
const { execSync } = require('child_process');

const PORT       = 8000;
const STATIC_DIR = path.join(__dirname, 'mock_static');
if (!fs.existsSync(STATIC_DIR)) fs.mkdirSync(STATIC_DIR);

// ── Detect LAN IP (shown at startup so you know what to put in .env) ──────────
function getLanIp() {
  for (const ifaces of Object.values(os.networkInterfaces())) {
    for (const iface of ifaces) {
      if (iface.family === 'IPv4' && !iface.internal) return iface.address;
    }
  }
  return 'localhost';
}
const LAN_IP = getLanIp();

// ── Fake RAG replies ──────────────────────────────────────────────────────────
const FAKE_REPLIES = [
  "Alzheimer's disease is a progressive neurological disorder that causes brain cells to degenerate, leading to memory loss and cognitive decline.",
  "Maintaining a consistent daily routine helps reduce confusion and anxiety in people with Alzheimer's.",
  "Early signs often include forgetting recently learned information, asking the same questions repeatedly, and difficulty completing familiar tasks.",
  "Regular physical activity, social engagement, and mental stimulation can help support cognitive health.",
  "It's okay to ask for help when you need it. Caregiving is a demanding role and support is available.",
];
function randomReply() { return FAKE_REPLIES[Math.floor(Math.random() * FAKE_REPLIES.length)]; }

// ── Generate speech WAV using macOS say + afconvert ───────────────────────────
function generateSpeechWav(text, outPath) {
  const aiffPath = outPath.replace('.wav', '.aiff');
  try {
    execSync(`say -o "${aiffPath}" "${text.replace(/"/g, '\\"')}"`, { stdio: 'pipe' });
    execSync(`afconvert "${aiffPath}" "${outPath}" -d LEI16 -f WAVE -r 16000`, { stdio: 'pipe' });
    fs.unlinkSync(aiffPath);
    return true;
  } catch {
    if (fs.existsSync(aiffPath)) fs.unlinkSync(aiffPath);
    return false;
  }
}

// Pre-generate one WAV per reply at startup so /voice responds instantly
console.log('Generating speech files...');
const WAV_FILES = FAKE_REPLIES.map((reply, i) => {
  const outPath = path.join(STATIC_DIR, `response_${i}.wav`);
  const ok = generateSpeechWav(reply, outPath);
  if (ok) process.stdout.write(`   🔊 ${i + 1}/${FAKE_REPLIES.length} done\r`);
  return { reply, wavPath: outPath, generated: ok };
});
console.log('');

// ── Helpers ───────────────────────────────────────────────────────────────────
function delay(ms) { return new Promise(r => setTimeout(r, ms)); }

function readBody(req) {
  return new Promise(resolve => {
    const chunks = [];
    req.on('data', c => chunks.push(c));
    req.on('end', () => resolve(Buffer.concat(chunks).toString()));
  });
}

function json(res, statusCode, obj) {
  const body = JSON.stringify(obj);
  res.writeHead(statusCode, {
    'Content-Type': 'application/json',
    'Content-Length': Buffer.byteLength(body),
  });
  res.end(body);
}

// ── Server ────────────────────────────────────────────────────────────────────
const server = http.createServer(async (req, res) => {
  // CORS — needed when Expo web dev tools call the API
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
  res.setHeader('Access-Control-Allow-Headers', 'Content-Type');

  if (req.method === 'OPTIONS') { res.writeHead(204); res.end(); return; }

  const { pathname } = new URL(req.url, `http://${req.headers.host}`);
  const timestamp = new Date().toLocaleTimeString();
  console.log(`[${timestamp}] ${req.method} ${pathname}`);

  // ── GET /health ─────────────────────────────────────────────────────────────
  if (req.method === 'GET' && pathname === '/health') {
    return json(res, 200, { status: 'ok', service: 'CogniCare mock server' });
  }

  // ── GET /static/response_N.wav ──────────────────────────────────────────────
  if (req.method === 'GET' && pathname.startsWith('/static/response_')) {
    const filename = pathname.replace('/static/', '');
    const filePath = path.join(STATIC_DIR, filename);
    if (!fs.existsSync(filePath)) return json(res, 404, { error: 'file not found' });
    const buf = fs.readFileSync(filePath);
    res.writeHead(200, { 'Content-Type': 'audio/wav', 'Content-Length': buf.length });
    return res.end(buf);
  }

  // ── POST /chat ──────────────────────────────────────────────────────────────
  if (req.method === 'POST' && pathname === '/chat') {
    let body = {};
    try { body = JSON.parse(await readBody(req)); } catch {}
    console.log(`   patient_id=${body.patient_id} message="${body.message}"`);
    await delay(900);   // simulate RAG latency
    return json(res, 200, { reply: randomReply() });
  }

  // ── POST /voice ─────────────────────────────────────────────────────────────
  if (req.method === 'POST' && pathname === '/voice') {
    await readBody(req);
    await delay(1500);

    const pick     = WAV_FILES[Math.floor(Math.random() * WAV_FILES.length)];
    const filename = path.basename(pick.wavPath);
    const host     = req.headers.host || `localhost:${PORT}`;
    const audioUrl = `http://${host}/static/${filename}`;

    return json(res, 200, {
      transcript: "What should I know about Alzheimer's care?",
      reply_text: pick.reply,
      audio_url:  audioUrl,
    });
  }

  // ── POST /reports/generate/:patient_id ─────────────────────────────────────
  if (req.method === 'POST' && pathname.startsWith('/reports/generate/')) {
    const patientId = Number(pathname.split('/').pop());
    await delay(300);
    return json(res, 200, {
      status:     'scheduled',
      patient_id: patientId,
      message:    'Report generation triggered (mock).',
    });
  }

  // ── 404 ─────────────────────────────────────────────────────────────────────
  return json(res, 404, { error: 'Not found', path: pathname });
});

server.listen(PORT, '0.0.0.0', () => {
  console.log(`
✅  CogniCare mock server running

   Simulator / web:    http://localhost:${PORT}
   Physical device:    http://${LAN_IP}:${PORT}

   Endpoints:
     GET  /health
     POST /chat              { patient_id, message }  → { reply }
     POST /voice             multipart { patient_id, audio }  → { transcript, reply_text, audio_url }
     POST /reports/generate/:patient_id  → { status }

   Quick tests (run in another terminal):
     curl http://localhost:${PORT}/health
     curl -X POST http://localhost:${PORT}/chat \\
          -H "Content-Type: application/json" \\
          -d '{"patient_id":1,"message":"What are early signs of Alzheimer?"}'
     curl -X POST http://localhost:${PORT}/reports/generate/1

   Press Ctrl+C to stop.
`);
});
