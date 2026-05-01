import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../../theme/app_theme.dart';
import './wizard_form_card_widget.dart';

class StepActivitiesWidget extends StatefulWidget {
  final GlobalKey<FormState> formKey;
  final List<Map<String, dynamic>> activities;

  const StepActivitiesWidget({
    super.key,
    required this.formKey,
    required this.activities,
  });

  @override
  State<StepActivitiesWidget> createState() => _StepActivitiesWidgetState();
}

class _StepActivitiesWidgetState extends State<StepActivitiesWidget> {
  final List<Map<String, TextEditingController>> _controllers = [];

  @override
  void initState() {
    super.initState();
    if (widget.activities.isEmpty) _addActivity();
  }

  void _addActivity() {
    final ctrls = {
      'name': TextEditingController(),
      'time': TextEditingController(),
      'description': TextEditingController(),
    };
    setState(() {
      _controllers.add(ctrls);
      widget.activities.add({'reminderType': 'Notification'});
    });
  }

  void _removeActivity(int i) {
    if (_controllers.length <= 1) return;
    for (final c in _controllers[i].values) {
      c.dispose();
    }
    setState(() {
      _controllers.removeAt(i);
      widget.activities.removeAt(i);
    });
  }

  @override
  void dispose() {
    for (final m in _controllers) {
      for (final c in m.values) {
        c.dispose();
      }
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Form(
      key: widget.formKey,
      child: Column(
        children: [
          _buildBanner(),
          const SizedBox(height: 12),
          ...List.generate(_controllers.length, (i) => _buildActivityCard(i)),
          _buildAddButton(),
          const SizedBox(height: 20),
        ],
      ),
    );
  }

  Widget _buildBanner() {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: const Color(0xFFF0EAFF),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppTheme.primary.withAlpha(38), width: 1),
      ),
      child: Row(
        children: [
          const Icon(
            Icons.self_improvement_rounded,
            color: AppTheme.primary,
            size: 22,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              'Structure daily routines to support cognitive stability.',
              style: GoogleFonts.nunitoSans(
                fontSize: 13,
                fontWeight: FontWeight.w500,
                color: AppTheme.textSecondary,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildActivityCard(int index) {
    final ctrls = _controllers[index];
    final reminderOptions = ['Notification', 'Voice', 'Both', 'None'];
    String currentReminder =
        widget.activities[index]['reminderType'] ?? 'Notification';

    return Container(
      margin: const EdgeInsets.only(bottom: 14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: AppTheme.primary.withAlpha(31), width: 1.5),
        boxShadow: [
          BoxShadow(
            color: AppTheme.primary.withAlpha(13),
            blurRadius: 12,
            offset: const Offset(0, 3),
          ),
        ],
      ),
      child: Padding(
        padding: const EdgeInsets.all(18),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Container(
                  width: 36,
                  height: 36,
                  decoration: BoxDecoration(
                    color: AppTheme.primaryLight,
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: const Icon(
                    Icons.event_note_rounded,
                    color: AppTheme.primary,
                    size: 18,
                  ),
                ),
                const SizedBox(width: 10),
                Text(
                  'Activity ${index + 1}',
                  style: GoogleFonts.nunitoSans(
                    fontSize: 15,
                    fontWeight: FontWeight.w700,
                    color: AppTheme.textPrimary,
                  ),
                ),
                const Spacer(),
                if (_controllers.length > 1)
                  GestureDetector(
                    onTap: () => _removeActivity(index),
                    child: Container(
                      padding: const EdgeInsets.all(6),
                      decoration: BoxDecoration(
                        color: AppTheme.error.withAlpha(26),
                        borderRadius: BorderRadius.circular(8),
                      ),
                      child: const Icon(
                        Icons.close_rounded,
                        color: AppTheme.error,
                        size: 16,
                      ),
                    ),
                  ),
              ],
            ),
            const SizedBox(height: 14),
            WizardTextField(
              label: 'Activity Name',
              hint: 'e.g. Morning Walk',
              controller: ctrls['name'],
              onSaved: (v) => widget.activities[index]['name'] = v,
            ),
            WizardTextField(
              label: 'Time',
              hint: 'e.g. 9:00 AM',
              controller: ctrls['time'],
              onSaved: (v) => widget.activities[index]['time'] = v,
            ),
            WizardTextField(
              label: 'Description',
              hint: 'e.g. 20-minute walk in the garden',
              controller: ctrls['description'],
              maxLines: 2,
              onSaved: (v) => widget.activities[index]['description'] = v,
            ),
            // Reminder type
            Padding(
              padding: const EdgeInsets.only(bottom: 4),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: Text(
                      'Reminder Type',
                      style: TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w500,
                        color: AppTheme.textSecondary,
                      ),
                    ),
                  ),
                  Wrap(
                    spacing: 8,
                    children: reminderOptions.map((r) {
                      final selected = currentReminder == r;
                      return GestureDetector(
                        onTap: () {
                          setState(() {
                            widget.activities[index]['reminderType'] = r;
                          });
                        },
                        child: AnimatedContainer(
                          duration: const Duration(milliseconds: 180),
                          padding: const EdgeInsets.symmetric(
                            horizontal: 14,
                            vertical: 8,
                          ),
                          decoration: BoxDecoration(
                            color: selected ? AppTheme.primary : Colors.white,
                            borderRadius: BorderRadius.circular(20),
                            border: Border.all(
                              color: selected
                                  ? AppTheme.primary
                                  : const Color(0xFFD4CCE8),
                              width: 1.5,
                            ),
                          ),
                          child: Text(
                            r,
                            style: TextStyle(
                              fontSize: 12,
                              fontWeight: FontWeight.w600,
                              color: selected
                                  ? Colors.white
                                  : AppTheme.textSecondary,
                            ),
                          ),
                        ),
                      );
                    }).toList(),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildAddButton() {
    return GestureDetector(
      onTap: _addActivity,
      child: Container(
        width: double.infinity,
        height: 52,
        decoration: BoxDecoration(
          color: AppTheme.primaryLight.withAlpha(128),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AppTheme.primary.withAlpha(64), width: 1.5),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(
              Icons.add_circle_outline_rounded,
              color: AppTheme.primary,
              size: 20,
            ),
            const SizedBox(width: 8),
            Text(
              'Add Another Activity',
              style: GoogleFonts.nunitoSans(
                fontSize: 14,
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
