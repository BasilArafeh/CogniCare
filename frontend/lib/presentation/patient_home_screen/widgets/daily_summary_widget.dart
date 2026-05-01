import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';
import '../../../theme/app_theme.dart';

class DailySummaryWidget extends StatelessWidget {
  final String patientName;

  const DailySummaryWidget({super.key, required this.patientName});

  @override
  Widget build(BuildContext context) {
    final now = DateTime.now();
    final items = _getSummaryItems(now);

    return Container(
      margin: const EdgeInsets.fromLTRB(16, 0, 16, 12),
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        color: Colors.white.withAlpha(224),
        borderRadius: BorderRadius.circular(24),
        border: Border.all(color: AppTheme.primary.withAlpha(31), width: 1.5),
        boxShadow: [
          BoxShadow(
            color: AppTheme.primary.withAlpha(20),
            blurRadius: 20,
            offset: const Offset(0, 4),
          ),
        ],
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(
                Icons.wb_sunny_rounded,
                color: AppTheme.warning,
                size: 18,
              ),
              const SizedBox(width: 8),
              Text(
                'Today\'s Plan',
                style: GoogleFonts.nunitoSans(
                  fontSize: 15,
                  fontWeight: FontWeight.w700,
                  color: AppTheme.textPrimary,
                ),
              ),
              const Spacer(),
              Text(
                _formatDate(now),
                style: GoogleFonts.nunitoSans(
                  fontSize: 12,
                  fontWeight: FontWeight.w500,
                  color: AppTheme.textMuted,
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
          ...items.map((item) => _buildSummaryRow(item)),
        ],
      ),
    );
  }

  List<Map<String, dynamic>> _getSummaryItems(DateTime now) {
    return [
      {
        'icon': Icons.medication_rounded,
        'color': AppTheme.primary,
        'bg': AppTheme.primaryLight,
        'title': 'Donepezil 10mg',
        'subtitle': '8:00 PM tonight',
        'done': false,
      },
      {
        'icon': Icons.restaurant_rounded,
        'color': AppTheme.secondary,
        'bg': AppTheme.secondaryLight,
        'title': 'Lunch',
        'subtitle': 'Chicken soup • 12:30 PM',
        'done': now.hour >= 13,
      },
      {
        'icon': Icons.self_improvement_rounded,
        'color': const Color(0xFF7C5CBF),
        'bg': const Color(0xFFEDE8F8),
        'title': 'Morning Walk',
        'subtitle': '9:00 AM • 20 minutes',
        'done': now.hour >= 10,
      },
      {
        'icon': Icons.phone_rounded,
        'color': const Color(0xFF7BAE8E),
        'bg': const Color(0xFFE6F2EC),
        'title': 'Call with Sarah',
        'subtitle': '3:00 PM this afternoon',
        'done': false,
      },
    ];
  }

  String _formatDate(DateTime dt) {
    const months = [
      '',
      'Jan',
      'Feb',
      'Mar',
      'Apr',
      'May',
      'Jun',
      'Jul',
      'Aug',
      'Sep',
      'Oct',
      'Nov',
      'Dec',
    ];
    return '${months[dt.month]} ${dt.day}, ${dt.year}';
  }

  Widget _buildSummaryRow(Map<String, dynamic> item) {
    final bool done = item['done'] as bool;

    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Row(
        children: [
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              color: done ? const Color(0xFFE6F2EC) : item['bg'] as Color,
              borderRadius: BorderRadius.circular(10),
            ),
            child: Icon(
              done ? Icons.check_rounded : item['icon'] as IconData,
              color: done ? AppTheme.success : item['color'] as Color,
              size: 18,
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  item['title'] as String,
                  style: GoogleFonts.nunitoSans(
                    fontSize: 14,
                    fontWeight: FontWeight.w600,
                    color: done ? AppTheme.textMuted : AppTheme.textPrimary,
                    decoration: done ? TextDecoration.lineThrough : null,
                  ),
                ),
                Text(
                  item['subtitle'] as String,
                  style: GoogleFonts.nunitoSans(
                    fontSize: 12,
                    fontWeight: FontWeight.w400,
                    color: AppTheme.textMuted,
                  ),
                ),
              ],
            ),
          ),
          if (done)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
              decoration: BoxDecoration(
                color: const Color(0xFFE6F2EC),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Text(
                'Done',
                style: GoogleFonts.nunitoSans(
                  fontSize: 11,
                  fontWeight: FontWeight.w700,
                  color: AppTheme.success,
                ),
              ),
            ),
        ],
      ),
    );
  }
}
