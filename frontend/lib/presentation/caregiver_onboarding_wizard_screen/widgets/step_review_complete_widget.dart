import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../../theme/app_theme.dart';

class StepReviewCompleteWidget extends StatefulWidget {
  final Map<String, dynamic> caregiverData;
  final Map<String, dynamic> patientData;
  final int medicationCount;
  final int mealCount;
  final int activityCount;
  final int familyCount;
  final int emergencyCount;
  final VoidCallback onComplete;
  final bool isSubmitting;
  final String? submitError;

  const StepReviewCompleteWidget({
    super.key,
    required this.caregiverData,
    required this.patientData,
    required this.medicationCount,
    required this.mealCount,
    required this.activityCount,
    required this.familyCount,
    required this.emergencyCount,
    required this.onComplete,
    this.isSubmitting = false,
    this.submitError,
  });

  @override
  State<StepReviewCompleteWidget> createState() =>
      _StepReviewCompleteWidgetState();
}

class _StepReviewCompleteWidgetState extends State<StepReviewCompleteWidget>
    with TickerProviderStateMixin {
  late AnimationController _checkController;
  late AnimationController _pulseController;
  late Animation<double> _checkScale;
  late Animation<double> _checkOpacity;
  late Animation<double> _pulseAnim;
  late Animation<double> _contentFade;

  @override
  void initState() {
    super.initState();
    _checkController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 800),
    );
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 1600),
    )..repeat(reverse: true);

    _checkScale = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _checkController, curve: Curves.elasticOut),
    );
    _checkOpacity = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(
        parent: _checkController,
        curve: const Interval(0.0, 0.3, curve: Curves.easeOut),
      ),
    );
    _pulseAnim = Tween<double>(begin: 0.95, end: 1.05).animate(
      CurvedAnimation(parent: _pulseController, curve: Curves.easeInOut),
    );
    _contentFade = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(
        parent: _checkController,
        curve: const Interval(0.5, 1.0, curve: Curves.easeOut),
      ),
    );

    Future.delayed(
      const Duration(milliseconds: 300),
      () => _checkController.forward(),
    );
  }

  @override
  void dispose() {
    _checkController.dispose();
    _pulseController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        const SizedBox(height: 20),

        // Animated checkmark orb
        AnimatedBuilder(
          animation: Listenable.merge([_checkController, _pulseController]),
          builder: (_, __) => ScaleTransition(
            scale: _pulseAnim,
            child: FadeTransition(
              opacity: _checkOpacity,
              child: ScaleTransition(
                scale: _checkScale,
                child: Container(
                  width: 120,
                  height: 120,
                  decoration: BoxDecoration(
                    shape: BoxShape.circle,
                    gradient: const LinearGradient(
                      colors: [Color(0xFF7C5CBF), Color(0xFF9B7EDB)],
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                    ),
                    boxShadow: [
                      BoxShadow(
                        color: AppTheme.primary.withAlpha(89),
                        blurRadius: 30,
                        offset: const Offset(0, 10),
                      ),
                    ],
                  ),
                  child: const Icon(
                    Icons.check_rounded,
                    color: Colors.white,
                    size: 56,
                  ),
                ),
              ),
            ),
          ),
        ),

        const SizedBox(height: 24),

        FadeTransition(
          opacity: _contentFade,
          child: Column(
            children: [
              Text(
                'CogniCare is Ready!',
                style: GoogleFonts.nunitoSans(
                  fontSize: 26,
                  fontWeight: FontWeight.w800,
                  color: AppTheme.textPrimary,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 10),
              Text(
                'CogniCare is ready to support your\nloved one with gentle daily care.',
                style: GoogleFonts.nunitoSans(
                  fontSize: 15,
                  fontWeight: FontWeight.w500,
                  color: AppTheme.textSecondary,
                  height: 1.6,
                ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 28),

              // Summary cards
              _buildSummaryGrid(),

              const SizedBox(height: 28),

              // Error message
              if (widget.submitError != null) ...[
                Container(
                  padding: const EdgeInsets.all(14),
                  margin: const EdgeInsets.only(bottom: 16),
                  decoration: BoxDecoration(
                    color: const Color(0xFFFFE4E4),
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(
                      color: AppTheme.error.withAlpha(77),
                      width: 1,
                    ),
                  ),
                  child: Row(
                    children: [
                      const Icon(
                        Icons.error_outline_rounded,
                        color: AppTheme.error,
                        size: 20,
                      ),
                      const SizedBox(width: 10),
                      Expanded(
                        child: Text(
                          widget.submitError!,
                          style: GoogleFonts.nunitoSans(
                            fontSize: 13,
                            fontWeight: FontWeight.w500,
                            color: AppTheme.error,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ],

              // Complete button
              _buildCompleteButton(),

              const SizedBox(height: 24),

              // Footer message
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: AppTheme.secondaryLight,
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Row(
                  children: [
                    const Icon(
                      Icons.favorite_rounded,
                      color: AppTheme.secondary,
                      size: 20,
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: Text(
                        'You\'ve taken a wonderful step in caring for your loved one.',
                        style: GoogleFonts.nunitoSans(
                          fontSize: 13,
                          fontWeight: FontWeight.w500,
                          color: AppTheme.secondaryDark,
                          height: 1.5,
                        ),
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 20),
            ],
          ),
        ),
      ],
    );
  }

  Widget _buildSummaryGrid() {
    final items = [
      {
        'icon': Icons.medication_rounded,
        'label': 'Medications',
        'count': widget.medicationCount,
        'color': AppTheme.primary,
        'bg': AppTheme.primaryLight,
      },
      {
        'icon': Icons.restaurant_rounded,
        'label': 'Meals',
        'count': widget.mealCount,
        'color': AppTheme.secondary,
        'bg': AppTheme.secondaryLight,
      },
      {
        'icon': Icons.self_improvement_rounded,
        'label': 'Activities',
        'count': widget.activityCount,
        'color': const Color(0xFF7C5CBF),
        'bg': const Color(0xFFEDE8F8),
      },
      {
        'icon': Icons.family_restroom_rounded,
        'label': 'Family',
        'count': widget.familyCount,
        'color': const Color(0xFF7BAE8E),
        'bg': const Color(0xFFE6F2EC),
      },
      {
        'icon': Icons.emergency_rounded,
        'label': 'Emergency',
        'count': widget.emergencyCount,
        'color': AppTheme.error,
        'bg': const Color(0xFFFFE4E4),
      },
    ];

    return Wrap(
      spacing: 10,
      runSpacing: 10,
      alignment: WrapAlignment.center,
      children: items.map((item) {
        return Container(
          width: 100,
          padding: const EdgeInsets.symmetric(vertical: 14, horizontal: 10),
          decoration: BoxDecoration(
            color: (item['bg'] as Color),
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
              color: (item['color'] as Color).withAlpha(51),
              width: 1.5,
            ),
          ),
          child: Column(
            children: [
              Icon(
                item['icon'] as IconData,
                color: item['color'] as Color,
                size: 24,
              ),
              const SizedBox(height: 6),
              Text(
                '${item['count']}',
                style: GoogleFonts.nunitoSans(
                  fontSize: 20,
                  fontWeight: FontWeight.w800,
                  color: item['color'] as Color,
                ),
              ),
              Text(
                item['label'] as String,
                style: GoogleFonts.nunitoSans(
                  fontSize: 11,
                  fontWeight: FontWeight.w600,
                  color: AppTheme.textSecondary,
                ),
                textAlign: TextAlign.center,
              ),
            ],
          ),
        );
      }).toList(),
    );
  }

  Widget _buildCompleteButton() {
    return GestureDetector(
      onTap: widget.isSubmitting ? null : widget.onComplete,
      child: Container(
        width: double.infinity,
        height: 60,
        decoration: BoxDecoration(
          gradient: LinearGradient(
            colors: widget.isSubmitting
                ? [const Color(0xFFB0A0D8), const Color(0xFFC4B0E8)]
                : [const Color(0xFF7C5CBF), const Color(0xFF9B7EDB)],
          ),
          borderRadius: BorderRadius.circular(30),
          boxShadow: [
            BoxShadow(
              color: AppTheme.primary.withAlpha(89),
              blurRadius: 20,
              offset: const Offset(0, 8),
            ),
          ],
        ),
        child: widget.isSubmitting
            ? const Center(
                child: SizedBox(
                  width: 26,
                  height: 26,
                  child: CircularProgressIndicator(
                    color: Colors.white,
                    strokeWidth: 2.5,
                  ),
                ),
              )
            : Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  const Icon(
                    Icons.rocket_launch_rounded,
                    color: Colors.white,
                    size: 22,
                  ),
                  const SizedBox(width: 10),
                  Text(
                    'Begin CogniCare',
                    style: GoogleFonts.nunitoSans(
                      fontSize: 18,
                      fontWeight: FontWeight.w700,
                      color: Colors.white,
                    ),
                  ),
                ],
              ),
      ),
    );
  }
}
