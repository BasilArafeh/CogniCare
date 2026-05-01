import 'package:flutter/material.dart';

import '../../../theme/app_theme.dart';
import './wizard_form_card_widget.dart';

class StepPatientAccountWidget extends StatefulWidget {
  final GlobalKey<FormState> formKey;
  final Map<String, dynamic> data;

  const StepPatientAccountWidget({
    super.key,
    required this.formKey,
    required this.data,
  });

  @override
  State<StepPatientAccountWidget> createState() =>
      _StepPatientAccountWidgetState();
}

class _StepPatientAccountWidgetState extends State<StepPatientAccountWidget> {
  final _nameCtrl = TextEditingController();
  final _usernameCtrl = TextEditingController();
  final _pinCtrl = TextEditingController();
  final _ageCtrl = TextEditingController();
  String _gender = 'Female';

  @override
  void dispose() {
    _nameCtrl.dispose();
    _usernameCtrl.dispose();
    _pinCtrl.dispose();
    _ageCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Form(
      key: widget.formKey,
      child: Column(
        children: [
          WizardFormCardWidget(
            title: 'Patient Identity',
            subtitle: 'How they will be known in the app',
            icon: Icons.accessibility_new_rounded,
            children: [
              WizardTextField(
                label: 'Patient Full Name',
                hint: 'e.g. Eleanor Mitchell',
                controller: _nameCtrl,
                prefixIcon: const Icon(
                  Icons.person_rounded,
                  color: AppTheme.textMuted,
                  size: 20,
                ),
                validator: (v) =>
                    v == null || v.trim().isEmpty ? 'Name is required' : null,
                onSaved: (v) => widget.data['name'] = v,
              ),
              WizardTextField(
                label: 'Login ID / Username',
                hint: 'Simple word they can remember',
                controller: _usernameCtrl,
                prefixIcon: const Icon(
                  Icons.alternate_email_rounded,
                  color: AppTheme.textMuted,
                  size: 20,
                ),
                validator: (v) => v == null || v.trim().isEmpty
                    ? 'Username is required'
                    : null,
                onSaved: (v) => widget.data['username'] = v,
              ),
            ],
          ),
          WizardFormCardWidget(
            title: 'Login PIN',
            subtitle: 'A simple 4-digit PIN for patient login',
            icon: Icons.pin_rounded,
            children: [
              WizardTextField(
                label: 'PIN (4 digits)',
                hint: 'e.g. 1234',
                controller: _pinCtrl,
                keyboardType: TextInputType.number,
                obscureText: true,
                prefixIcon: const Icon(
                  Icons.lock_rounded,
                  color: AppTheme.textMuted,
                  size: 20,
                ),
                validator: (v) {
                  if (v == null || v.isEmpty) return 'PIN is required';
                  if (v.length != 4) return 'PIN must be exactly 4 digits';
                  return null;
                },
                onSaved: (v) => widget.data['pin'] = v,
              ),
            ],
          ),
          WizardFormCardWidget(
            title: 'Basic Details',
            subtitle: 'Age and gender',
            icon: Icons.info_outline_rounded,
            children: [
              WizardTextField(
                label: 'Age',
                hint: 'e.g. 74',
                controller: _ageCtrl,
                keyboardType: TextInputType.number,
                prefixIcon: const Icon(
                  Icons.cake_rounded,
                  color: AppTheme.textMuted,
                  size: 20,
                ),
                validator: (v) =>
                    v == null || v.trim().isEmpty ? 'Age is required' : null,
                onSaved: (v) => widget.data['age'] = v,
              ),
              // Gender selector
              Padding(
                padding: const EdgeInsets.only(bottom: 14),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: Text(
                        'Gender',
                        style: TextStyle(
                          fontSize: 14,
                          fontWeight: FontWeight.w500,
                          color: AppTheme.textSecondary,
                        ),
                      ),
                    ),
                    Row(
                      children: ['Female', 'Male', 'Other'].map((g) {
                        final selected = _gender == g;
                        return Expanded(
                          child: GestureDetector(
                            onTap: () {
                              setState(() => _gender = g);
                              widget.data['gender'] = g;
                            },
                            child: AnimatedContainer(
                              duration: const Duration(milliseconds: 200),
                              margin: const EdgeInsets.symmetric(horizontal: 3),
                              padding: const EdgeInsets.symmetric(vertical: 12),
                              decoration: BoxDecoration(
                                color: selected
                                    ? AppTheme.primary
                                    : Colors.white,
                                borderRadius: BorderRadius.circular(12),
                                border: Border.all(
                                  color: selected
                                      ? AppTheme.primary
                                      : const Color(0xFFD4CCE8),
                                  width: 1.5,
                                ),
                              ),
                              child: Text(
                                g,
                                textAlign: TextAlign.center,
                                style: TextStyle(
                                  fontSize: 13,
                                  fontWeight: FontWeight.w600,
                                  color: selected
                                      ? Colors.white
                                      : AppTheme.textSecondary,
                                ),
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
          const SizedBox(height: 20),
        ],
      ),
    );
  }
}
