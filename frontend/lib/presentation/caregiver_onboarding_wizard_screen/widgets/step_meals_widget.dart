import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../../theme/app_theme.dart';
import './wizard_form_card_widget.dart';

class StepMealsWidget extends StatefulWidget {
  final GlobalKey<FormState> formKey;
  final List<Map<String, dynamic>> meals;

  const StepMealsWidget({
    super.key,
    required this.formKey,
    required this.meals,
  });

  @override
  State<StepMealsWidget> createState() => _StepMealsWidgetState();
}

class _StepMealsWidgetState extends State<StepMealsWidget> {
  final List<Map<String, TextEditingController>> _controllers = [];

  @override
  void initState() {
    super.initState();
    if (widget.meals.isEmpty) {
      _addMeal();
    }
  }

  void _addMeal() {
    final ctrls = {
      'name': TextEditingController(),
      'time': TextEditingController(),
      'dietary': TextEditingController(),
      'preferred': TextEditingController(),
      'notes': TextEditingController(),
    };
    setState(() {
      _controllers.add(ctrls);
      widget.meals.add({});
    });
  }

  void _removeMeal(int index) {
    if (_controllers.length <= 1) return;
    for (final c in _controllers[index].values) {
      c.dispose();
    }
    setState(() {
      _controllers.removeAt(index);
      widget.meals.removeAt(index);
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
          ...List.generate(_controllers.length, (i) => _buildMealCard(i)),
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
            Icons.restaurant_rounded,
            color: AppTheme.secondary,
            size: 22,
          ),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              'Set up meal times and dietary preferences for your loved one.',
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

  Widget _buildMealCard(int index) {
    final ctrls = _controllers[index];
    final mealNames = ['Breakfast', 'Lunch', 'Dinner', 'Snack'];
    final mealIcons = [
      Icons.wb_sunny_rounded,
      Icons.restaurant_rounded,
      Icons.nights_stay_rounded,
      Icons.cookie_rounded,
    ];
    final mealColors = [
      const Color(0xFFFFF3CD),
      const Color(0xFFE6F2EC),
      const Color(0xFFEDE8F8),
      const Color(0xFFFFE4E4),
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
                  width: 36,
                  height: 36,
                  decoration: BoxDecoration(
                    color: mealColors[index % mealColors.length],
                    borderRadius: BorderRadius.circular(10),
                  ),
                  child: Icon(
                    mealIcons[index % mealIcons.length],
                    color: AppTheme.secondary,
                    size: 18,
                  ),
                ),
                const SizedBox(width: 10),
                Text(
                  index < mealNames.length
                      ? mealNames[index]
                      : 'Meal ${index + 1}',
                  style: GoogleFonts.nunitoSans(
                    fontSize: 15,
                    fontWeight: FontWeight.w700,
                    color: AppTheme.textPrimary,
                  ),
                ),
                const Spacer(),
                if (_controllers.length > 1)
                  GestureDetector(
                    onTap: () => _removeMeal(index),
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
              label: 'Meal Name',
              hint: 'e.g. Oatmeal with berries',
              controller: ctrls['name'],
              onSaved: (v) => widget.meals[index]['name'] = v,
            ),
            WizardTextField(
              label: 'Meal Time',
              hint: 'e.g. 8:00 AM',
              controller: ctrls['time'],
              onSaved: (v) => widget.meals[index]['time'] = v,
            ),
            WizardTextField(
              label: 'Dietary Restrictions',
              hint: 'e.g. Low sodium, no dairy',
              controller: ctrls['dietary'],
              onSaved: (v) => widget.meals[index]['dietary'] = v,
            ),
            WizardTextField(
              label: 'Preferred Foods',
              hint: 'e.g. Soft foods, warm soups',
              controller: ctrls['preferred'],
              onSaved: (v) => widget.meals[index]['preferred'] = v,
            ),
            WizardTextField(
              label: 'Notes',
              hint: 'e.g. Needs assistance cutting food',
              controller: ctrls['notes'],
              onSaved: (v) => widget.meals[index]['notes'] = v,
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildAddButton() {
    return GestureDetector(
      onTap: _addMeal,
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
              Icons.add_circle_outline_rounded,
              color: AppTheme.secondary,
              size: 20,
            ),
            const SizedBox(width: 8),
            Text(
              'Add Another Meal',
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