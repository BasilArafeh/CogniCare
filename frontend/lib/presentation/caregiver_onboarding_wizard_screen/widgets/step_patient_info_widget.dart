import 'package:flutter/material.dart';

import '../../../theme/app_theme.dart';
import './wizard_form_card_widget.dart';

class StepPatientInfoWidget extends StatefulWidget {
  final GlobalKey<FormState> formKey;
  final Map<String, dynamic> data;

  const StepPatientInfoWidget({
    super.key,
    required this.formKey,
    required this.data,
  });

  @override
  State<StepPatientInfoWidget> createState() => _StepPatientInfoWidgetState();
}

class _StepPatientInfoWidgetState extends State<StepPatientInfoWidget> {
  final _dobCtrl = TextEditingController();
  final _addressCtrl = TextEditingController();
  final _medNotesCtrl = TextEditingController();
  final _allergiesCtrl = TextEditingController();
  final _cognitiveCtrl = TextEditingController();
  String _diagnosisStage = 'Mild';
  String _commPref = 'Voice';

  @override
  void dispose() {
    _dobCtrl.dispose();
    _addressCtrl.dispose();
    _medNotesCtrl.dispose();
    _allergiesCtrl.dispose();
    _cognitiveCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Form(
      key: widget.formKey,
      child: Column(
        children: [
          WizardFormCardWidget(
            title: 'Diagnosis',
            subtitle: 'Current Alzheimer\'s stage',
            icon: Icons.medical_information_rounded,
            children: [
              _buildStageSelector(),
              const SizedBox(height: 8),
              WizardTextField(
                label: 'Date of Birth',
                hint: 'MM/DD/YYYY',
                controller: _dobCtrl,
                keyboardType: TextInputType.datetime,
                prefixIcon: const Icon(
                  Icons.calendar_today_rounded,
                  color: AppTheme.textMuted,
                  size: 20,
                ),
                onSaved: (v) => widget.data['dob'] = v,
              ),
            ],
          ),
          WizardFormCardWidget(
            title: 'Address & Notes',
            subtitle: 'Home address and medical background',
            icon: Icons.home_outlined,
            children: [
              WizardTextField(
                label: 'Home Address',
                hint: 'Street, City, State, ZIP',
                controller: _addressCtrl,
                maxLines: 2,
                prefixIcon: const Icon(
                  Icons.location_on_outlined,
                  color: AppTheme.textMuted,
                  size: 20,
                ),
                onSaved: (v) => widget.data['address'] = v,
              ),
              WizardTextField(
                label: 'Medical Notes',
                hint: 'Any relevant medical history...',
                controller: _medNotesCtrl,
                maxLines: 3,
                onSaved: (v) => widget.data['medicalNotes'] = v,
              ),
              WizardTextField(
                label: 'Known Allergies',
                hint: 'e.g. Penicillin, Peanuts',
                controller: _allergiesCtrl,
                prefixIcon: const Icon(
                  Icons.warning_amber_rounded,
                  color: AppTheme.warning,
                  size: 20,
                ),
                onSaved: (v) => widget.data['allergies'] = v,
              ),
            ],
          ),
          WizardFormCardWidget(
            title: 'Care Preferences',
            subtitle: 'How to best support them',
            icon: Icons.favorite_outline_rounded,
            children: [
              WizardTextField(
                label: 'Cognitive Needs',
                hint: 'e.g. Needs visual cues, short sentences...',
                controller: _cognitiveCtrl,
                maxLines: 2,
                onSaved: (v) => widget.data['cognitiveNeeds'] = v,
              ),
              _buildCommPrefSelector(),
            ],
          ),
          const SizedBox(height: 20),
        ],
      ),
    );
  }

  Widget _buildStageSelector() {
    final stages = ['Mild', 'Moderate', 'Severe'];
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Text(
              'Diagnosis Stage',
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w500,
                color: AppTheme.textSecondary,
              ),
            ),
          ),
          Row(
            children: stages.map((s) {
              final selected = _diagnosisStage == s;
              Color stageColor = s == 'Mild'
                  ? AppTheme.success
                  : s == 'Moderate'
                  ? AppTheme.warning
                  : AppTheme.error;
              return Expanded(
                child: GestureDetector(
                  onTap: () {
                    setState(() => _diagnosisStage = s);
                    widget.data['diagnosisStage'] = s;
                  },
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 200),
                    margin: const EdgeInsets.symmetric(horizontal: 3),
                    padding: const EdgeInsets.symmetric(vertical: 12),
                    decoration: BoxDecoration(
                      color: selected ? stageColor.withAlpha(31) : Colors.white,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                        color: selected ? stageColor : const Color(0xFFD4CCE8),
                        width: selected ? 2 : 1.5,
                      ),
                    ),
                    child: Text(
                      s,
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w700,
                        color: selected ? stageColor : AppTheme.textSecondary,
                      ),
                    ),
                  ),
                ),
              );
            }).toList(),
          ),
        ],
      ),
    );
  }

  Widget _buildCommPrefSelector() {
    final prefs = ['Voice', 'Text', 'Both'];
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Text(
              'Communication Preference',
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w500,
                color: AppTheme.textSecondary,
              ),
            ),
          ),
          Row(
            children: prefs.map((p) {
              final selected = _commPref == p;
              return Expanded(
                child: GestureDetector(
                  onTap: () {
                    setState(() => _commPref = p);
                    widget.data['commPref'] = p;
                  },
                  child: AnimatedContainer(
                    duration: const Duration(milliseconds: 200),
                    margin: const EdgeInsets.symmetric(horizontal: 3),
                    padding: const EdgeInsets.symmetric(vertical: 12),
                    decoration: BoxDecoration(
                      color: selected ? AppTheme.primary : Colors.white,
                      borderRadius: BorderRadius.circular(12),
                      border: Border.all(
                        color: selected
                            ? AppTheme.primary
                            : const Color(0xFFD4CCE8),
                        width: 1.5,
                      ),
                    ),
                    child: Text(
                      p,
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        color: selected ? Colors.white : AppTheme.textSecondary,
                      ),
                    ),
                  ),
                ),
              );
            }).toList(),
          ),
        ],
      ),
    );
  }
}
