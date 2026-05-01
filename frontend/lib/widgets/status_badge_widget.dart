import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

enum BadgeStatus { active, inactive, warning, success, info }

class StatusBadgeWidget extends StatelessWidget {
  final String label;
  final BadgeStatus status;

  const StatusBadgeWidget({
    super.key,
    required this.label,
    this.status = BadgeStatus.active,
  });

  @override
  Widget build(BuildContext context) {
    final colors = _colors();
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 5),
      decoration: BoxDecoration(
        color: colors.$1,
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(
        label,
        style: GoogleFonts.nunitoSans(
          fontSize: 12,
          fontWeight: FontWeight.w700,
          color: colors.$2,
        ),
      ),
    );
  }

  (Color, Color) _colors() {
    switch (status) {
      case BadgeStatus.active:
        return (const Color(0xFFEDE8F8), const Color(0xFF7C5CBF));
      case BadgeStatus.inactive:
        return (const Color(0xFFF0EEF8), const Color(0xFFB0A8C8));
      case BadgeStatus.warning:
        return (const Color(0xFFFEF3E2), const Color(0xFFB45309));
      case BadgeStatus.success:
        return (const Color(0xFFE6F2EC), const Color(0xFF2D7A4F));
      case BadgeStatus.info:
        return (const Color(0xFFE6F2EC), const Color(0xFF7BAE8E));
    }
  }
}
