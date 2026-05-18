/**
 * HTTP client for speech on the CogniCare **ai_agent** service only
 * (`EXPO_PUBLIC_AI_AGENT_URL` → `getAiAgentBaseUrl()`).
 *
 * Do not route these paths through `EXPO_PUBLIC_RAG_URL`.
 */

import axios, { AxiosInstance } from 'axios';
import * as FileSystem from 'expo-file-system/legacy';

import { getAiAgentBaseUrl } from './backendUrls';

const AI_AGENT_BASE_URL = getAiAgentBaseUrl();
console.log('[aiAgentSpeech] base URL =', AI_AGENT_BASE_URL);

const client: AxiosInstance = axios.create({
  baseURL: AI_AGENT_BASE_URL,
  timeout: 120_000,
});

export async function pingAiAgentSpeechHealth(): Promise<boolean> {
  try {
    const { data } = await client.get<{ status: string }>('/health', { timeout: 5_000 });
    return data.status === 'ok';
  } catch {
    return false;
  }
}

/** multipart: patient_id + file — aligns with CogniCare `POST /speech/stt`. */
export async function postSpeechStt(
  patientId: number,
  audioUri: string,
  recordingFileName = 'recording.wav',
  mimeType = 'audio/wav',
): Promise<{ patient_id: number; text: string; language?: string | null }> {
  const url = `${AI_AGENT_BASE_URL}/speech/stt`;
  console.log('[aiAgentSpeech STT]', url, 'patientId=', patientId);

  const form = new FormData();
  form.append('patient_id', String(patientId));
  form.append('file', { uri: audioUri, name: recordingFileName, type: mimeType } as unknown as Blob);

  const { data } = await client.post<{
    patient_id: number;
    text: string;
    language?: string | null;
  }>('/speech/stt', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120_000,
  });
  return data;
}

/** JSON — aligns with CogniCare `POST /speech/tts` (binary audio body). */
export async function postSpeechTts(payload: {
  patient_id: number;
  text: string;
  language: string;
}): Promise<{ data: ArrayBuffer; contentType?: string }> {
  const url = `${AI_AGENT_BASE_URL}/speech/tts`;
  console.log('[aiAgentSpeech TTS]', url, 'patient_id=', payload.patient_id);

  const res = await client.post<ArrayBuffer>(`/speech/tts`, payload, {
    responseType: 'arraybuffer',
    timeout: 120_000,
  });
  const contentType =
    typeof res.headers['content-type'] === 'string' ? res.headers['content-type'] : undefined;
  return { data: res.data, contentType };
}

/**
 * multipart: patient_id + audio — full pipeline aligned with CogniCare `POST /speech/voice`
 * `{ transcript, reply_text, audio_url }`.
 */
export async function sendVoiceRecordingPipeline(
  patientId: number,
  audioUri: string,
): Promise<{ transcript: string; replyText: string; audioUri: string }> {
  const url = `${AI_AGENT_BASE_URL}/speech/voice`;
  console.log('[aiAgentSpeech voice]', url, '| patientId:', patientId, '| audioUri:', audioUri);

  const form = new FormData();
  form.append('patient_id', String(patientId));
  form.append('audio', { uri: audioUri, name: 'recording.wav', type: 'audio/wav' } as unknown as Blob);

  const res = await client.post<{
    transcript: string;
    reply_text: string;
    audio_url: string;
  }>('/speech/voice', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120_000,
  });

  const data = res.data;
  console.log('[aiAgentSpeech voice] transcript:', data.transcript, '| audio_url:', data.audio_url);

  const ext = data.audio_url.endsWith('.wav') ? '.wav' : '.mp3';
  const destUri = `${FileSystem.documentDirectory}response_${patientId}_${Date.now()}${ext}`;
  await FileSystem.downloadAsync(data.audio_url, destUri);

  return {
    transcript: data.transcript,
    replyText: data.reply_text,
    audioUri: destUri,
  };
}

export const aiAgentSpeechService = {
  baseUrl: AI_AGENT_BASE_URL,
  pingAiAgentSpeechHealth,
  sendVoiceRecordingPipeline,
};

export default aiAgentSpeechService;
