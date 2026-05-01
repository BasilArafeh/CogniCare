import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../../theme/app_theme.dart';
import './wizard_form_card_widget.dart';

class StepCaregiverAccountWidget extends StatefulWidget {
  final GlobalKey<FormState> formKey;
  final Map<String, dynamic> data;

  const StepCaregiverAccountWidget({
    super.key,
    required this.formKey,
    required this.data,
  });

  @override
  State<StepCaregiverAccountWidget> createState() =>
      _StepCaregiverAccountWidgetState();
}

class _StepCaregiverAccountWidgetState
    extends State<StepCaregiverAccountWidget> {
  final _nameCtrl = TextEditingController();
  final _emailCtrl = TextEditingController();
  final _phoneCtrl = TextEditingController();
  final _passwordCtrl = TextEditingController();
  final _confirmCtrl = TextEditingController();

  @override
  void dispose() {
    _nameCtrl.dispose();
    _emailCtrl.dispose();
    _phoneCtrl.dispose();
    _passwordCtrl.dispose();
    _confirmCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Form(
      key: widget.formKey,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildIntroText(),
          const SizedBox(height: 16),
          WizardFormCardWidget(
            title: 'Personal Details',
            subtitle: 'Tell us about yourself',
            icon: Icons.person_outline_rounded,
            children: [
              WizardTextField(
                label: 'Full Name',
                hint: 'e.g. Sarah Mitchell',
                controller: _nameCtrl,
                prefixIcon: const Icon(
                  Icons.badge_rounded,
                  color: AppTheme.textMuted,
                  size: 20,
                ),
                validator: (v) =>
                    v == null || v.trim().isEmpty ? 'Name is required' : null,
                onSaved: (v) => widget.data['name'] = v,
              ),
              WizardTextField(
                label: 'Email Address',
                hint: 'e.g. sarah@example.com',
                controller: _emailCtrl,
                keyboardType: TextInputType.emailAddress,
                prefixIcon: const Icon(
                  Icons.email_outlined,
                  color: AppTheme.textMuted,
                  size: 20,
                ),
                validator: (v) {
                  if (v == null || v.trim().isEmpty) return 'Email is required';
                  if (!v.contains('@')) return 'Enter a valid email';
                  return null;
                },
                onSaved: (v) => widget.data['email'] = v,
              ),
              WizardTextField(
                label: 'Phone Number',
                hint: 'e.g. +1 (555) 234-5678',
                controller: _phoneCtrl,
                keyboardType: TextInputType.phone,
                prefixIcon: const Icon(
                  Icons.phone_outlined,
                  color: AppTheme.textMuted,
                  size: 20,
                ),
                validator: (v) =>
                    v == null || v.trim().isEmpty ? 'Phone is required' : null,
                onSaved: (v) => widget.data['phone'] = v,
              ),
            ],
          ),
          WizardFormCardWidget(
            title: 'Create Password',
            subtitle: 'Keep your account secure',
            icon: Icons.lock_outline_rounded,
            children: [
              WizardTextField(
                label: 'Password',
                hint: 'Minimum 8 characters',
                controller: _passwordCtrl,
                obscureText: true,
                validator: (v) {
                  if (v == null || v.isEmpty) return 'Password is required';
                  if (v.length < 8) return 'Must be at least 8 characters';
                  return null;
                },
                onSaved: (v) => widget.data['password'] = v,
              ),
              WizardTextField(
                label: 'Confirm Password',
                hint: 'Re-enter your password',
                controller: _confirmCtrl,
                obscureText: true,
                validator: (v) {
                  if (v != _passwordCtrl.text) return 'Passwords do not match';
                  return null;
                },
                onSaved: (v) => widget.data['confirmPassword'] = v,
              ),
            ],
          ),
          const SizedBox(height: 20),
        ],
      ),
    );
  }

  Widget _buildIntroText() {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          colors: [
            AppTheme.primary.withAlpha(20),
            AppTheme.secondary.withAlpha(15),
          ],
        ),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppTheme.primary.withAlpha(31), width: 1),
      ),
      child: Row(
        children: [
          const Icon(Icons.favorite_rounded, color: AppTheme.primary, size: 24),
          const SizedBox(width: 12),
          Expanded(
            child: Text(
              'Welcome! Let\'s set up CogniCare\nfor your loved one.',
              style: GoogleFonts.nunitoSans(
                fontSize: 14,
                fontWeight: FontWeight.w500,
                color: AppTheme.textSecondary,
                height: 1.5,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
