import 'package:flutter/material.dart';
import '../../../theme/app_theme.dart';

/// Voice Orb — based on reference image: large gradient blurred orb with
/// concentric glow rings, microphone icon center, pulsing animation on active
class VoiceOrbWidget extends StatefulWidget {
  final bool isListening;
  final bool isProcessing;
  final VoidCallback onTap;
  final double size;

  const VoiceOrbWidget({
    super.key,
    required this.isListening,
    required this.onTap,
    this.isProcessing = false,
    this.size = 190,
  });

  @override
  State<VoiceOrbWidget> createState() => _VoiceOrbWidgetState();
}

class _VoiceOrbWidgetState extends State<VoiceOrbWidget>
    with TickerProviderStateMixin {
  late AnimationController _pulseController;
  late AnimationController _rippleController;
  late AnimationController _rotateController;
  late Animation<double> _pulse1;
  late Animation<double> _pulse2;
  late Animation<double> _ripple1;
  late Animation<double> _ripple2;
  late Animation<double> _rotate;
  late Animation<double> _innerPulse;

  @override
  void initState() {
    super.initState();

    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2000),
    )..repeat(reverse: true);

    _rippleController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1400),
    );

    _rotateController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 8),
    )..repeat();

    _pulse1 = Tween<double>(begin: 1.0, end: 1.08).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );
    _pulse2 = Tween<double>(begin: 1.0, end: 1.14).animate(
      CurvedAnimation(
        parent: _pulseController,
        curve: const Interval(0.2, 1.0, curve: Curves.easeInOut),
      ),
    );
    _innerPulse = Tween<double>(begin: 0.95, end: 1.05).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );

    _ripple1 = Tween<double>(begin: 1.0, end: 1.6).animate(
      CurvedAnimation(parent: _rippleController, curve: Curves.easeOut),
    );
    _ripple2 = Tween<double>(begin: 1.0, end: 1.9).animate(
      CurvedAnimation(
        parent: _rippleController,
        curve: const Interval(0.15, 1.0, curve: Curves.easeOut),
      ),
    );

    _rotate = Tween<double>(begin: 0, end: 1).animate(_rotateController);
  }

  @override
  void didUpdateWidget(VoiceOrbWidget oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.isListening && !oldWidget.isListening) {
      _rippleController.repeat(period: const Duration(milliseconds: 1400));
    } else if (!widget.isListening && oldWidget.isListening) {
      _rippleController.stop();
      _rippleController.reset();
    }
  }

  @override
  void dispose() {
    _pulseController.dispose();
    _rippleController.dispose();
    _rotateController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final s = widget.size;

    return GestureDetector(
      onTap: widget.isProcessing ? null : widget.onTap,
      child: SizedBox(
        width: s * 1.6,
        height: s * 1.6,
        child: AnimatedBuilder(
          animation: Listenable.merge([
            _pulseController,
            _rippleController,
            _rotateController,
          ]),
          builder: (_, __) {
            return Stack(
              alignment: Alignment.center,
              children: [
                // Outermost ambient glow
                Transform.scale(
                  scale: _pulse2.value,
                  child: Container(
                    width: s * 1.5,
                    height: s * 1.5,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: RadialGradient(
                        colors: [
                          AppTheme.primary.withOpacity(
                            widget.isListening ? 0.18 : 0.10,
                          ),
                          AppTheme.primaryMuted.withAlpha(15),
                          Colors.transparent,
                        ],
                        stops: const [0.0, 0.5, 1.0],
                      ),
                    ),
                  ),
                ),

                // Ripple rings when listening
                if (widget.isListening) ...[
                  Opacity(
                    opacity: (1.0 - (_ripple1.value - 1.0) / 0.6).clamp(
                      0.0,
                      0.4,
                    ),
                    child: Transform.scale(
                      scale: _ripple1.value,
                      child: Container(
                        width: s,
                        height: s,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          border: Border.all(
                            color: AppTheme.primary.withAlpha(77),
                            width: 2,
                          ),
                        ),
                      ),
                    ),
                  ),
                  Opacity(
                    opacity: (1.0 - (_ripple2.value - 1.0) / 0.9).clamp(
                      0.0,
                      0.25,
                    ),
                    child: Transform.scale(
                      scale: _ripple2.value,
                      child: Container(
                        width: s,
                        height: s,
                        decoration: BoxDecoration(
                          shape: BoxShape.circle,
                          border: Border.all(
                            color: AppTheme.primaryMuted.withAlpha(51),
                            width: 1.5,
                          ),
                        ),
                      ),
                    ),
                  ),
                ],

                // Middle ring
                Transform.scale(
                  scale: _pulse1.value,
                  child: Container(
                    width: s * 1.15,
                    height: s * 1.15,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: RadialGradient(
                        colors: [
                          AppTheme.primary.withOpacity(
                            widget.isListening ? 0.22 : 0.12,
                          ),
                          AppTheme.secondary.withAlpha(20),
                          Colors.transparent,
                        ],
                        stops: const [0.0, 0.6, 1.0],
                      ),
                    ),
                  ),
                ),

                // Main orb body
                Transform.scale(
                  scale: _innerPulse.value,
                  child: Container(
                    width: s,
                    height: s,
                    decoration: BoxDecoration(
                      shape: BoxShape.circle,
                      gradient: SweepGradient(
                        transform: GradientRotation(_rotate.value * 6.28),
                        colors: [
                          Colors.white,
                          AppTheme.primary.withOpacity(
                            widget.isListening ? 0.35 : 0.18,
                          ),
                          AppTheme.secondary.withOpacity(
                            widget.isListening ? 0.22 : 0.10,
                          ),
                          const Color(0xFFE8D5FF).withAlpha(128),
                          Colors.white,
                        ],
                      ),
                      boxShadow: [
                        BoxShadow(
                          color: AppTheme.primary.withOpacity(
                            widget.isListening ? 0.30 : 0.15,
                          ),
                          blurRadius: widget.isListening ? 40 : 24,
                          spreadRadius: widget.isListening ? 4 : 0,
                        ),
                        const BoxShadow(
                          color: Colors.white,
                          blurRadius: 20,
                          spreadRadius: -4,
                        ),
                      ],
                    ),
                  ),
                ),

                // Inner frosted layer + icon
                Container(
                  width: s * 0.72,
                  height: s * 0.72,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    color: Colors.white.withAlpha(179),
                  ),
                  child: widget.isProcessing
                      ? const Center(
                          child: SizedBox(
                            width: 36,
                            height: 36,
                            child: CircularProgressIndicator(
                              color: AppTheme.primary,
                              strokeWidth: 3,
                            ),
                          ),
                        )
                      : Icon(
                          widget.isListening
                              ? Icons.stop_rounded
                              : Icons.mic_rounded,
                          color: widget.isListening
                              ? AppTheme.error
                              : AppTheme.primary,
                          size: s * 0.22,
                        ),
                ),
              ],
            );
          },
        ),
      ),
    );
  }
}
