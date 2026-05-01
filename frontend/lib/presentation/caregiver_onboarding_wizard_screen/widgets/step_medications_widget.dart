import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../../theme/app_theme.dart';
import './wizard_form_card_widget.dart';

class StepMedicationsWidget extends StatefulWidget {
  final GlobalKey<FormState> formKey;
  final List<Map<String, dynamic>> medications;

  const StepMedicationsWidget({
    super.key,
    required this.formKey,
    required this.medications,
  });

  @override
  State<StepMedicationsWidget> createState() => _StepMedicationsWidgetState();
}

class _StepMedicationsWidgetState extends State<StepMedicationsWidget> {
  final List<Map<String, TextEditingController>> _controllers = [];

  @override
  void initState() {
    super.initState();
    // Pre-populate with one entry
    if (widget.medications.isEmpty) {
      _addMedication();
    }
  }

  void _addMedication() {
    final ctrls = {
      'name': TextEditingController(),
      'dosage': TextEditingController(),
      'time': TextEditingController(),
      'frequency': TextEditingController(),
      'notes': TextEditingController(),
    };
    setState(() {
      _controllers.add(ctrls);
      widget.medications.add({});
    });
  }

  void _removeMedication(int index) {
    if (_controllers.length <= 1) return;
    for (final c in _controllers[index].values) {
      c.dispose();
    }
    setState(() {
      _controllers.removeAt(index);
      widget.medications.removeAt(index);
    });
  }

  @override
  void dispose() {
    for (final ctrlMap in _controllers) {
      for (final c in ctrlMap.values) {
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
          _buildInfoBanner(),
          const SizedBox(height: 12),
          ...List.generate(_controllers.length, (i) => _buildMedCard(i)),
          _buildAddButton(),
          const SizedBox(height: 20),
        ],
      ),
    );
  }

  Widget _buildInfoBanner() {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppTheme.primaryLight.withAlpha(153),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppTheme.primary.withAlpha(38), width: 1),
      ),
      child: Row(
        children: [
          const Icon(
            Icons.medication_rounded,
            color: AppTheme.primary,
            size: 22,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              'Add all medications your loved one takes daily.',
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

  Widget _buildMedCard(int index) {
    final ctrls = _controllers[index];
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
                  width: 32,
                  height: 32,
                  decoration: BoxDecoration(
                    color: AppTheme.primaryLight,
                    shape: BoxShape.circle,
                  ),
                  child: Center(
                    child: Text(
                      '${index + 1}',
                      style: GoogleFonts.nunitoSans(
                        fontSize: 14,
                        fontWeight: FontWeight.w700,
                        color: AppTheme.primary,
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 10),
                Text(
                  'Medication ${index + 1}',
                  style: GoogleFonts.nunitoSans(
                    fontSize: 15,
                    fontWeight: FontWeight.w700,
                    color: AppTheme.textPrimary,
                  ),
                ),
                const Spacer(),
                if (_controllers.length > 1)
                  GestureDetector(
                    onTap: () => _removeMedication(index),
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
              label: 'Medication Name',
              hint: 'e.g. Donepezil',
              controller: ctrls['name'],
              validator: (v) => v == null || v.trim().isEmpty
                  ? 'Medication name required'
                  : null,
              onSaved: (v) => widget.medications[index]['name'] = v,
            ),
            Row(
              children: [
                Expanded(
                  child: WizardTextField(
                    label: 'Dosage',
                    hint: 'e.g. 10mg',
                    controller: ctrls['dosage'],
                    onSaved: (v) => widget.medications[index]['dosage'] = v,
                  ),
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: WizardTextField(
                    label: 'Time',
                    hint: 'e.g. 8:00 AM',
                    controller: ctrls['time'],
                    onSaved: (v) => widget.medications[index]['time'] = v,
                  ),
                ),
              ],
            ),
            WizardTextField(
              label: 'Frequency',
              hint: 'e.g. Once daily, Twice daily',
              controller: ctrls['frequency'],
              onSaved: (v) => widget.medications[index]['frequency'] = v,
            ),
            WizardTextField(
              label: 'Notes (optional)',
              hint: 'e.g. Take with food',
              controller: ctrls['notes'],
              onSaved: (v) => widget.medications[index]['notes'] = v,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildAddButton() {
    return GestureDetector(
      onTap: _addMedication,
      child: Container(
        width: double.infinity,
        height: 52,
        decoration: BoxDecoration(
          color: AppTheme.primaryLight.withAlpha(128),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: AppTheme.primary.withAlpha(64),
            width: 1.5,
            style: BorderStyle.solid,
          ),
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
              'Add Another Medication',
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
