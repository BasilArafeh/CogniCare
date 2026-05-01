import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../../theme/app_theme.dart';
import './wizard_form_card_widget.dart';

class StepEmergencyContactsWidget extends StatefulWidget {
  final GlobalKey<FormState> formKey;
  final List<Map<String, dynamic>> contacts;

  const StepEmergencyContactsWidget({
    super.key,
    required this.formKey,
    required this.contacts,
  });

  @override
  State<StepEmergencyContactsWidget> createState() =>
      _StepEmergencyContactsWidgetState();
}

class _StepEmergencyContactsWidgetState
    extends State<StepEmergencyContactsWidget> {
  final List<Map<String, TextEditingController>> _controllers = [];

  @override
  void initState() {
    super.initState();
    if (widget.contacts.isEmpty) _addContact();
  }

  void _addContact() {
    final ctrls = {
      'name': TextEditingController(),
      'phone': TextEditingController(),
      'relationship': TextEditingController(),
    };
    setState(() {
      _controllers.add(ctrls);
      widget.contacts.add({'priority': 'Primary'});
    });
  }

  void _removeContact(int i) {
    if (_controllers.length <= 1) return;
    for (final c in _controllers[i].values) {
      c.dispose();
    }
    setState(() {
      _controllers.removeAt(i);
      widget.contacts.removeAt(i);
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
          ...List.generate(_controllers.length, (i) => _buildContactCard(i)),
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
        color: const Color(0xFFFFE4E4),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppTheme.error.withAlpha(51), width: 1),
      ),
      child: Row(
        children: [
          const Icon(Icons.emergency_rounded, color: AppTheme.error, size: 22),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              'These contacts will be alerted in case of an emergency.',
              style: GoogleFonts.nunitoSans(
                fontSize: 13,
                fontWeight: FontWeight.w500,
                color: AppTheme.error,
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildContactCard(int index) {
    final ctrls = _controllers[index];
    final priorityOptions = ['Primary', 'Secondary', 'Backup'];
    String currentPriority = widget.contacts[index]['priority'] ?? 'Primary';

    return Container(
      margin: const EdgeInsets.only(bottom: 14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: AppTheme.error.withAlpha(38), width: 1.5),
        boxShadow: [
          BoxShadow(
            color: AppTheme.error.withAlpha(13),
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
                    color: const Color(0xFFFFE4E4),
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: const Icon(
                    Icons.emergency_rounded,
                    color: AppTheme.error,
                    size: 18,
                  ),
                ),
                const SizedBox(width: 10),
                Text(
                  'Contact ${index + 1}',
                  style: GoogleFonts.nunitoSans(
                    fontSize: 15,
                    fontWeight: FontWeight.w700,
                    color: AppTheme.textPrimary,
                  ),
                ),
                const Spacer(),
                if (_controllers.length > 1)
                  GestureDetector(
                    onTap: () => _removeContact(index),
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
              label: 'Contact Name',
              hint: 'e.g. Dr. Patricia Chen',
              controller: ctrls['name'],
              validator: (v) =>
                  v == null || v.trim().isEmpty ? 'Name required' : null,
              onSaved: (v) => widget.contacts[index]['name'] = v,
            ),
            WizardTextField(
              label: 'Phone Number',
              hint: 'e.g. +1 (555) 911-0000',
              controller: ctrls['phone'],
              keyboardType: TextInputType.phone,
              prefixIcon: const Icon(
                Icons.phone_rounded,
                color: AppTheme.error,
                size: 20,
              ),
              validator: (v) =>
                  v == null || v.trim().isEmpty ? 'Phone required' : null,
              onSaved: (v) => widget.contacts[index]['phone'] = v,
            ),
            WizardTextField(
              label: 'Relationship',
              hint: 'e.g. Primary Physician, Neighbor',
              controller: ctrls['relationship'],
              onSaved: (v) => widget.contacts[index]['relationship'] = v,
            ),
            // Priority selector
            Padding(
              padding: const EdgeInsets.only(bottom: 4),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: Text(
                      'Priority Level',
                      style: TextStyle(
                        fontSize: 14,
                        fontWeight: FontWeight.w500,
                        color: AppTheme.textSecondary,
                      ),
                    ),
                  ),
                  Row(
                    children: priorityOptions.map((p) {
                      final selected = currentPriority == p;
                      final color = p == 'Primary'
                          ? AppTheme.error
                          : p == 'Secondary'
                          ? AppTheme.warning
                          : AppTheme.textMuted;
                      return Expanded(
                        child: GestureDetector(
                          onTap: () {
                            setState(() {
                              widget.contacts[index]['priority'] = p;
                            });
                          },
                          child: AnimatedContainer(
                            duration: const Duration(milliseconds: 180),
                            margin: const EdgeInsets.symmetric(horizontal: 3),
                            padding: const EdgeInsets.symmetric(vertical: 10),
                            decoration: BoxDecoration(
                              color: selected
                                  ? color.withAlpha(31)
                                  : Colors.white,
                              borderRadius: BorderRadius.circular(12),
                              border: Border.all(
                                color: selected
                                    ? color
                                    : const Color(0xFFD4CCE8),
                                width: selected ? 2 : 1.5,
                              ),
                            ),
                            child: Text(
                              p,
                              textAlign: TextAlign.center,
                              style: TextStyle(
                                fontSize: 12,
                                fontWeight: FontWeight.w700,
                                color: selected
                                    ? color
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
      ),
    );
  }

  Widget _buildAddButton() {
    return GestureDetector(
      onTap: _addContact,
      child: Container(
        width: double.infinity,
        height: 52,
        decoration: BoxDecoration(
          color: const Color(0xFFFFE4E4),
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AppTheme.error.withAlpha(64), width: 1.5),
        ),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(
              Icons.add_circle_outline_rounded,
              color: AppTheme.error,
              size: 20,
            ),
            const SizedBox(width: 8),
            Text(
              'Add Emergency Contact',
              style: GoogleFonts.nunitoSans(
                fontSize: 14,
                fontWeight: FontWeight.w600,
                color: AppTheme.error,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
