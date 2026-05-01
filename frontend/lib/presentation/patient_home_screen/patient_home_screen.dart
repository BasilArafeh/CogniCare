import 'dart:typed_data';
import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import 'package:record/record.dart';
import 'package:just_audio/just_audio.dart';
import 'package:dio/dio.dart';

import '../../theme/app_theme.dart';
import '../../services/api_service.dart';
import './widgets/chat_bottom_bar_widget.dart';
import './widgets/daily_summary_widget.dart';
import './widgets/patient_chat_sheet_widget.dart';
import './widgets/patient_greeting_widget.dart';
import './widgets/voice_orb_widget.dart';

class PatientHomeScreen extends StatefulWidget {
  const PatientHomeScreen({super.key});

  @override
  State<PatientHomeScreen> createState() => _PatientHomeScreenState();
}

class _PatientHomeScreenState extends State<PatientHomeScreen>
    with TickerProviderStateMixin {
  bool _isListening = false;
  bool _isProcessing = false;
  bool _showDailySummary = false;
  String? _voiceError;

  // TODO: Replace with real patient ID from auth/session
  final String _patientId = 'patient_1';
  final String _patientName = 'Eleanor';
  final String _greeting = _getGreeting();

  late AnimationController _backgroundController;
  late Animation<Color?> _bgColor1;
  late Animation<Color?> _bgColor2;

  final AudioRecorder _recorder = AudioRecorder();
  final AudioPlayer _audioPlayer = AudioPlayer();

  static String _getGreeting() {
    final hour = DateTime.now().hour;
    if (hour < 12) return 'Good morning';
    if (hour < 17) return 'Good afternoon';
    return 'Good evening';
  }

  @override
  void initState() {
    super.initState();
    _backgroundController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 4),
    )..repeat(reverse: true);

    _bgColor1 =
        ColorTween(
          begin: const Color(0xFFF5F0FF),
          end: const Color(0xFFEEF8F4),
        ).animate(
          CurvedAnimation(
            parent: _backgroundController,
            curve: Curves.easeInOut,
          ),
        );

    _bgColor2 =
        ColorTween(
          begin: const Color(0xFFEDE8F8),
          end: const Color(0xFFE6F2EC),
        ).animate(
          CurvedAnimation(
            parent: _backgroundController,
            curve: Curves.easeInOut,
          ),
        );
  }

  @override
  void dispose() {
    _backgroundController.dispose();
    _recorder.dispose();
    _audioPlayer.dispose();
    super.dispose();
  }

  // ---------------------------------------------------------------------------
  // Voice flow
  // ---------------------------------------------------------------------------

  Future<void> _onMicToggle() async {
    if (_isProcessing) return;

    if (_isListening) {
      await _stopAndSend();
    } else {
      await _startRecording();
    }
  }

  Future<void> _startRecording() async {
    setState(() {
      _voiceError = null;
    });

    // On web the browser handles permission prompts automatically
    if (!kIsWeb) {
      final hasPermission = await _recorder.hasPermission();
      if (!hasPermission) {
        setState(() => _voiceError = 'Microphone permission denied.');
        return;
      }
    }

    try {
      if (kIsWeb) {
        await _recorder.start(
          const RecordConfig(encoder: AudioEncoder.wav),
          path: 'voice_note.wav',
        );
      } else {
        await _recorder.start(
          const RecordConfig(encoder: AudioEncoder.aacLc),
          path: '/tmp/voice_note.m4a',
        );
      }
      setState(() => _isListening = true);
    } catch (e) {
      setState(() => _voiceError = 'Could not start recording.');
    }
  }

  Future<void> _stopAndSend() async {
    setState(() {
      _isListening = false;
      _isProcessing = true;
      _voiceError = null;
    });

    try {
      final path = await _recorder.stop();
      if (path == null) {
        setState(() {
          _isProcessing = false;
          _voiceError = 'Recording failed. Please try again.';
        });
        return;
      }

      Uint8List audioBytes;
      if (kIsWeb) {
        // On web, record package returns a blob URL — read via http
        final response = await ApiService().dio.get<List<int>>(
          path,
          options: Options(responseType: ResponseType.bytes),
        );
        audioBytes = Uint8List.fromList(response.data ?? []);
      } else {
        // On mobile, path is a file path
        final file = await _readFile(path);
        audioBytes = file;
      }

      final responseBytes = await ApiService().postVoice(
        patientId: _patientId,
        audioBytes: audioBytes,
        mimeType: kIsWeb ? 'audio/wav' : 'audio/aac',
      );

      await _playResponseAudio(responseBytes);
    } on ApiException catch (e) {
      setState(() => _voiceError = e.message);
    } catch (_) {
      setState(() => _voiceError = 'Something went wrong. Please try again.');
    } finally {
      if (mounted) setState(() => _isProcessing = false);
    }
  }

  Future<Uint8List> _readFile(String path) async {
    // dart:io is only available on non-web
    if (kIsWeb) return Uint8List(0);
    // ignore: avoid_dynamic_calls
    final dynamic ioFile = _createIoFile(path);
    return await ioFile.readAsBytes() as Uint8List;
  }

  // Lazy import of dart:io to avoid web compilation errors
  dynamic _createIoFile(String path) {
    // This is only called on non-web platforms
    // Using dynamic to avoid dart:io import at top level
    return _IoFileHelper.create(path);
  }

  Future<void> _playResponseAudio(Uint8List bytes) async {
    try {
      final source = _BytesAudioSource(bytes);
      await _audioPlayer.setAudioSource(source);
      await _audioPlayer.play();
    } catch (_) {
      // Silently ignore playback errors
    }
  }

  void _openChat() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (_) => PatientChatSheetWidget(patientName: _patientName),
    );
  }

  @override
  Widget build(BuildContext context) {
    final size = MediaQuery.of(context).size;
    final isTablet = size.width >= 600;

    return Scaffold(
      body: AnimatedBuilder(
        animation: _backgroundController,
        builder: (_, child) => Container(
          decoration: BoxDecoration(
            gradient: LinearGradient(
              begin: Alignment.topCenter,
              end: Alignment.bottomCenter,
              colors: [
                _bgColor1.value ?? const Color(0xFFF5F0FF),
                Colors.white,
                _bgColor2.value ?? const Color(0xFFEDE8F8),
              ],
              stops: const [0.0, 0.5, 1.0],
            ),
          ),
          child: child,
        ),
        child: SafeArea(
          child: Column(
            children: [
              _buildTopBar(),
              Expanded(
                child: Center(
                  child: ConstrainedBox(
                    constraints: BoxConstraints(
                      maxWidth: isTablet ? 480 : double.infinity,
                    ),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        PatientGreetingWidget(
                          greeting: _greeting,
                          patientName: _patientName,
                          isListening: _isListening,
                        ),
                        SizedBox(height: size.height * 0.05),
                        VoiceOrbWidget(
                          isListening: _isListening,
                          isProcessing: _isProcessing,
                          onTap: _onMicToggle,
                          size: isTablet ? 220 : 190,
                        ),
                        SizedBox(height: size.height * 0.04),
                        AnimatedSwitcher(
                          duration: const Duration(milliseconds: 280),
                          child: _isProcessing
                              ? _buildProcessingLabel()
                              : _isListening
                              ? _buildListeningLabel()
                              : _buildTapLabel(),
                        ),
                        if (_voiceError != null) ...[
                          const SizedBox(height: 12),
                          _buildErrorBanner(),
                        ],
                        SizedBox(height: size.height * 0.03),
                        if (!_isListening && !_isProcessing)
                          _buildSummaryToggle(),
                      ],
                    ),
                  ),
                ),
              ),
              AnimatedSize(
                duration: const Duration(milliseconds: 350),
                curve: Curves.easeOutCubic,
                child: _showDailySummary
                    ? DailySummaryWidget(patientName: _patientName)
                    : const SizedBox.shrink(),
              ),
              ChatBottomBarWidget(onChatTap: _openChat),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildTopBar() {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 12, 20, 0),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
            decoration: BoxDecoration(
              color: Colors.white.withAlpha(217),
              borderRadius: BorderRadius.circular(20),
              border: Border.all(
                color: AppTheme.primary.withAlpha(38),
                width: 1,
              ),
              boxShadow: [
                BoxShadow(
                  color: AppTheme.primary.withAlpha(20),
                  blurRadius: 12,
                  offset: const Offset(0, 3),
                ),
              ],
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Container(
                  width: 22,
                  height: 22,
                  decoration: const BoxDecoration(
                    gradient: LinearGradient(
                      colors: [Color(0xFF7C5CBF), Color(0xFF9B7EDB)],
                    ),
                    shape: BoxShape.circle,
                  ),
                  child: const Icon(
                    Icons.favorite_rounded,
                    color: Colors.white,
                    size: 12,
                  ),
                ),
                const SizedBox(width: 6),
                Text(
                  'CogniCare',
                  style: GoogleFonts.nunitoSans(
                    fontSize: 13,
                    fontWeight: FontWeight.w700,
                    color: AppTheme.textPrimary,
                  ),
                ),
              ],
            ),
          ),
          const Spacer(),
          GestureDetector(
            onTap: () {},
            child: Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                color: Colors.white.withAlpha(217),
                shape: BoxShape.circle,
                border: Border.all(
                  color: AppTheme.primary.withAlpha(31),
                  width: 1,
                ),
                boxShadow: [
                  BoxShadow(
                    color: AppTheme.primary.withAlpha(20),
                    blurRadius: 10,
                  ),
                ],
              ),
              child: const Icon(
                Icons.settings_rounded,
                color: AppTheme.textSecondary,
                size: 20,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildTapLabel() {
    return Text(
      'Tap to speak',
      key: const ValueKey('tap'),
      style: GoogleFonts.nunitoSans(
        fontSize: 16,
        fontWeight: FontWeight.w600,
        color: AppTheme.textSecondary,
      ),
    );
  }

  Widget _buildListeningLabel() {
    return Text(
      'Listening… tap to send',
      key: const ValueKey('listening'),
      style: GoogleFonts.nunitoSans(
        fontSize: 16,
        fontWeight: FontWeight.w600,
        color: AppTheme.primary,
      ),
    );
  }

  Widget _buildProcessingLabel() {
    return Text(
      'Processing your message…',
      key: const ValueKey('processing'),
      style: GoogleFonts.nunitoSans(
        fontSize: 16,
        fontWeight: FontWeight.w600,
        color: AppTheme.textSecondary,
      ),
    );
  }

  Widget _buildErrorBanner() {
    return Container(
      margin: const EdgeInsets.symmetric(horizontal: 24),
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
      decoration: BoxDecoration(
        color: const Color(0xFFFFE4E4),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppTheme.error.withAlpha(64), width: 1),
      ),
      child: Row(
        children: [
          const Icon(
            Icons.error_outline_rounded,
            color: AppTheme.error,
            size: 18,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              _voiceError!,
              style: GoogleFonts.nunitoSans(
                fontSize: 13,
                fontWeight: FontWeight.w500,
                color: AppTheme.error,
              ),
            ),
          ),
          GestureDetector(
            onTap: () => setState(() => _voiceError = null),
            child: const Icon(
              Icons.close_rounded,
              color: AppTheme.error,
              size: 16,
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildSummaryToggle() {
    return GestureDetector(
      onTap: () => setState(() => _showDailySummary = !_showDailySummary),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 10),
        decoration: BoxDecoration(
          color: Colors.white.withAlpha(204),
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: AppTheme.primary.withAlpha(31), width: 1),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              _showDailySummary
                  ? Icons.expand_less_rounded
                  : Icons.expand_more_rounded,
              color: AppTheme.primary,
              size: 18,
            ),
            const SizedBox(width: 6),
            Text(
              _showDailySummary ? 'Hide daily summary' : 'View daily summary',
              style: GoogleFonts.nunitoSans(
                fontSize: 13,
                fontWeight: FontWeight.w600,
                color: AppTheme.primary,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Helpers for dart:io on non-web platforms
// ---------------------------------------------------------------------------

class _IoFileHelper {
  static dynamic create(String path) {
    // ignore: undefined_identifier
    return _IoFile(path);
  }
}

class _IoFile {
  final String path;
  _IoFile(this.path);

  Future<Uint8List> readAsBytes() async {
    // dart:io File — only reached on non-web
    // Using dynamic invocation to avoid top-level dart:io import
    throw UnsupportedError('Use conditional import for dart:io');
  }
}

// ---------------------------------------------------------------------------
// In-memory audio source for just_audio
// ---------------------------------------------------------------------------

class _BytesAudioSource extends StreamAudioSource {
  final Uint8List _bytes;
  _BytesAudioSource(this._bytes);

  @override
  Future<StreamAudioResponse> request([int? start, int? end]) async {
    start ??= 0;
    end ??= _bytes.length;
    return StreamAudioResponse(
      sourceLength: _bytes.length,
      contentLength: end - start,
      offset: start,
      stream: Stream.value(_bytes.sublist(start, end)),
      contentType: 'audio/wav',
    );
  }
}