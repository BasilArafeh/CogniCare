import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../../theme/app_theme.dart';
import './wizard_form_card_widget.dart';

class StepFamilyMembersWidget extends StatefulWidget {
  final GlobalKey<FormState> formKey;
  final List<Map<String, dynamic>> familyMembers;

  const StepFamilyMembersWidget({
    super.key,
    required this.formKey,
    required this.familyMembers,
  });

  @override
  State<StepFamilyMembersWidget> createState() =>
      _StepFamilyMembersWidgetState();
}

class _StepFamilyMembersWidgetState extends State<StepFamilyMembersWidget> {
  final List<Map<String, TextEditingController>> _controllers = [];

  @override
  void initState() {
    super.initState();
    if (widget.familyMembers.isEmpty) _addMember();
  }

  void _addMember() {
    final ctrls = {
      'name': TextEditingController(),
      'relationship': TextEditingController(),
      'phone': TextEditingController(),
    };
    setState(() {
      _controllers.add(ctrls);
      widget.familyMembers.add({});
    });
  }

  void _removeMember(int i) {
    if (_controllers.length <= 1) return;
    for (final c in _controllers[i].values) {
      c.dispose();
    }
    setState(() {
      _controllers.removeAt(i);
      widget.familyMembers.removeAt(i);
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
          ...List.generate(_controllers.length, (i) => _buildMemberCard(i)),
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
        color: AppTheme.secondaryLight,
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppTheme.secondary.withAlpha(64), width: 1),
      ),
      child: Row(
        children: [
          const Icon(
            Icons.family_restroom_rounded,
            color: AppTheme.secondary,
            size: 22,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              'Add family members who are part of the care circle.',
              style: GoogleFonts.nunitoSans(
                fontSize: 13,
                fontWeight: FontWeight.w500,
                color: AppTheme.secondaryDark,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildMemberCard(int index) {
    final ctrls = _controllers[index];
    final avatarColors = [
      const Color(0xFFEDE8F8),
      const Color(0xFFE6F2EC),
      const Color(0xFFFFF3CD),
      const Color(0xFFFFE4E4),
    ];
    final avatarIcons = [
      Icons.person_rounded,
      Icons.person_2_rounded,
      Icons.person_3_rounded,
      Icons.person_4_rounded,
    ];

    return Container(
      margin: const EdgeInsets.only(bottom: 14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: AppTheme.secondary.withAlpha(38), width: 1.5),
        boxShadow: [
          BoxShadow(
            color: AppTheme.secondary.withAlpha(15),
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
                  width: 44,
                  height: 44,
                  decoration: BoxDecoration(
                    color: avatarColors[index % avatarColors.length],
                    shape: BoxShape.circle,
                  ),
                  child: Icon(
                    avatarIcons[index % avatarIcons.length],
                    color: AppTheme.primary,
                    size: 22,
                  ),
                ),
                const SizedBox(width: 10),
                Text(
                  'Family Member ${index + 1}',
                  style: GoogleFonts.nunitoSans(
                    fontSize: 15,
                    fontWeight: FontWeight.w700,
                    color: AppTheme.textPrimary,
                  ),
                ),
                const Spacer(),
                if (_controllers.length > 1)
                  GestureDetector(
                    onTap: () => _removeMember(index),
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
              label: 'Full Name',
              hint: 'e.g. James Mitchell',
              controller: ctrls['name'],
              validator: (v) =>
                  v == null || v.trim().isEmpty ? 'Name required' : null,
              onSaved: (v) => widget.familyMembers[index]['name'] = v,
            ),
            WizardTextField(
              label: 'Relationship',
              hint: 'e.g. Son, Daughter, Spouse',
              controller: ctrls['relationship'],
              onSaved: (v) => widget.familyMembers[index]['relationship'] = v,
            ),
            WizardTextField(
              label: 'Phone Number',
              hint: 'e.g. +1 (555) 345-6789',
              controller: ctrls['phone'],
              keyboardType: TextInputType.phone,
              prefixIcon: const Icon(
                Icons.phone_rounded,
                color: AppTheme.textMuted,
                size: 20,
              ),
              onSaved: (v) => widget.familyMembers[index]['phone'] = v,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildAddButton() {
    return GestureDetector(
      onTap: _addMember,
      child: Container(
        width: double.infinity,
        height: 52,
        decoration: BoxDecoration(
          color: AppTheme.secondaryLight,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(
            color: AppTheme.secondary.withAlpha(77),
            width: 1.5,
          ),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(
              Icons.person_add_rounded,
              color: AppTheme.secondary,
              size: 20,
            ),
            const SizedBox(width: 8),
            Text(
              'Add Family Member',
              style: GoogleFonts.nunitoSans(
                fontSize: 14,
                fontWeight: FontWeight.w600,
                color: AppTheme.secondaryDark,
              ),
            ),
          ],
        ),
      ),
    );
  }
}