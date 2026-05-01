import 'package:flutter/material.dart';
import 'package:google_fonts/google_fonts.dart';

import '../../routes/app_routes.dart';
import '../../theme/app_theme.dart';
import '../../services/api_service.dart';
import './widgets/step_activities_widget.dart';
import './widgets/step_caregiver_account_widget.dart';
import './widgets/step_emergency_contacts_widget.dart';
import './widgets/step_family_members_widget.dart';
import './widgets/step_meals_widget.dart';
import './widgets/step_medications_widget.dart';
import './widgets/step_patient_account_widget.dart';
import './widgets/step_patient_info_widget.dart';
import './widgets/step_review_complete_widget.dart';
import './widgets/wizard_progress_widget.dart';

class CaregiverOnboardingWizardScreen extends StatefulWidget {
  const CaregiverOnboardingWizardScreen({super.key});

  @override
  State<CaregiverOnboardingWizardScreen> createState() =>
      _CaregiverOnboardingWizardScreenState();
}

class _CaregiverOnboardingWizardScreenState
    extends State<CaregiverOnboardingWizardScreen>
    with TickerProviderStateMixin {
  // TODO: Replace with Riverpod/Bloc for production
  int _currentStep = 0;
  final int _totalSteps = 9;
  late AnimationController _pageController;
  late Animation<double> _pageAnim;
  bool _isNavigatingForward = true;
  bool _isSubmitting = false;
  String? _submitError;

  final List<GlobalKey<FormState>> _formKeys = List.generate(
    9,
    (_) => GlobalKey<FormState>(),
  );

  // Collected data maps
  final Map<String, dynamic> _caregiverData = {};
  final Map<String, dynamic> _patientData = {};
  final Map<String, dynamic> _patientInfoData = {};
  final List<Map<String, dynamic>> _medications = [];
  final List<Map<String, dynamic>> _meals = [];
  final List<Map<String, dynamic>> _activities = [];
  final List<Map<String, dynamic>> _familyMembers = [];
  final List<Map<String, dynamic>> _emergencyContacts = [];

  final List<String> _stepTitles = [
    'Your Account',
    'Patient Account',
    'Patient Information',
    'Medications',
    'Meals & Nutrition',
    'Daily Activities',
    'Family Members',
    'Emergency Contacts',
    'All Set!',
  ];

  final List<IconData> _stepIcons = [
    Icons.person_rounded,
    Icons.accessibility_new_rounded,
    Icons.medical_information_rounded,
    Icons.medication_rounded,
    Icons.restaurant_rounded,
    Icons.self_improvement_rounded,
    Icons.family_restroom_rounded,
    Icons.emergency_rounded,
    Icons.check_circle_rounded,
  ];

  @override
  void initState() {
    super.initState();
    _pageController = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 320),
    );
    _pageAnim = Tween<double>(begin: 0, end: 1).animate(
      CurvedAnimation(parent: _pageController, curve: Curves.easeOutCubic),
    );
    _pageController.value = 1.0;
  }

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  void _goNext() {
    final formValid = _formKeys[_currentStep].currentState?.validate() ?? true;
    if (!formValid) return;
    _formKeys[_currentStep].currentState?.save();

    if (_currentStep < _totalSteps - 1) {
      setState(() {
        _isNavigatingForward = true;
        _currentStep++;
      });
      _pageController.forward(from: 0);
    }
  }

  void _goBack() {
    if (_currentStep > 0) {
      setState(() {
        _isNavigatingForward = false;
        _currentStep--;
      });
      _pageController.forward(from: 0);
    } else {
      Navigator.pop(context);
    }
  }

  @override
  Widget build(BuildContext context) {
    final size = MediaQuery.of(context).size;
    final isTablet = size.width >= 600;
    final isLastStep = _currentStep == _totalSteps - 1;

    return Scaffold(
      body: Container(
        decoration: const BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topCenter,
            end: Alignment.bottomCenter,
            colors: [Color(0xFFF0EAFF), Color(0xFFF5F3FF)],
          ),
        ),
        child: SafeArea(
          child: Column(
            children: [
              // Top bar
              _buildTopBar(context),

              // Progress widget
              WizardProgressWidget(
                currentStep: _currentStep,
                totalSteps: _totalSteps,
                stepTitles: _stepTitles,
                stepIcons: _stepIcons,
              ),

              // Step content
              Expanded(
                child: AnimatedBuilder(
                  animation: _pageAnim,
                  builder: (_, child) => Opacity(
                    opacity: _pageAnim.value,
                    child: Transform.translate(
                      offset: Offset(
                        _isNavigatingForward
                            ? (1 - _pageAnim.value) * 30
                            : -(1 - _pageAnim.value) * 30,
                        0,
                      ),
                      child: child,
                    ),
                  ),
                  child: SingleChildScrollView(
                    padding: EdgeInsets.symmetric(
                      horizontal: isTablet ? 40 : 20,
                      vertical: 8,
                    ),
                    child: Center(
                      child: ConstrainedBox(
                        constraints: BoxConstraints(
                          maxWidth: isTablet ? 560 : double.infinity,
                        ),
                        child: _buildCurrentStep(),
                      ),
                    ),
                  ),
                ),
              ),

              // Navigation buttons
              if (!isLastStep) _buildNavigationButtons(isTablet),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildTopBar(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 16, 0),
      child: Row(
        children: [
          GestureDetector(
            onTap: _goBack,
            child: Container(
              width: 44,
              height: 44,
              decoration: BoxDecoration(
                color: Colors.white,
                shape: BoxShape.circle,
                boxShadow: [
                  BoxShadow(
                    color: AppTheme.primary.withAlpha(26),
                    blurRadius: 12,
                    offset: const Offset(0, 3),
                  ),
                ],
              ),
              child: const Icon(
                Icons.arrow_back_rounded,
                color: AppTheme.textPrimary,
                size: 20,
              ),
            ),
          ),
          const Spacer(),
          Text(
            'Step ${_currentStep + 1} of $_totalSteps',
            style: GoogleFonts.nunitoSans(
              fontSize: 13,
              fontWeight: FontWeight.w600,
              color: AppTheme.textSecondary,
            ),
          ),
          const Spacer(),
          const SizedBox(width: 44),
        ],
      ),
    );
  }

  Widget _buildCurrentStep() {
    switch (_currentStep) {
      case 0:
        return StepCaregiverAccountWidget(
          formKey: _formKeys[0],
          data: _caregiverData,
        );
      case 1:
        return StepPatientAccountWidget(
          formKey: _formKeys[1],
          data: _patientData,
        );
      case 2:
        return StepPatientInfoWidget(
          formKey: _formKeys[2],
          data: _patientInfoData,
        );
      case 3:
        return StepMedicationsWidget(
          formKey: _formKeys[3],
          medications: _medications,
        );
      case 4:
        return StepMealsWidget(formKey: _formKeys[4], meals: _meals);
      case 5:
        return StepActivitiesWidget(
          formKey: _formKeys[5],
          activities: _activities,
        );
      case 6:
        return StepFamilyMembersWidget(
          formKey: _formKeys[6],
          familyMembers: _familyMembers,
        );
      case 7:
        return StepEmergencyContactsWidget(
          formKey: _formKeys[7],
          contacts: _emergencyContacts,
        );
      case 8:
        return StepReviewCompleteWidget(
          caregiverData: _caregiverData,
          patientData: _patientData,
          medicationCount: _medications.length,
          mealCount: _meals.length,
          activityCount: _activities.length,
          familyCount: _familyMembers.length,
          emergencyCount: _emergencyContacts.length,
          isSubmitting: _isSubmitting,
          submitError: _submitError,
          onComplete: _submitSetup,
        );
      default:
        return const SizedBox.shrink();
    }
  }

  Widget _buildNavigationButtons(bool isTablet) {
    final isFirstStep = _currentStep == 0;
    return Container(
      padding: EdgeInsets.fromLTRB(
        isTablet ? 40 : 20,
        12,
        isTablet ? 40 : 20,
        20,
      ),
      decoration: BoxDecoration(
        color: Colors.white.withAlpha(204),
        border: Border(
          top: BorderSide(color: AppTheme.primary.withAlpha(26), width: 1),
        ),
      ),
      child: Center(
        child: ConstrainedBox(
          constraints: BoxConstraints(
            maxWidth: isTablet ? 560 : double.infinity,
          ),
          child: Row(
            children: [
              if (!isFirstStep) ...[
                Expanded(
                  child: OutlinedButton(
                    onPressed: _goBack,
                    style: OutlinedButton.styleFrom(
                      foregroundColor: AppTheme.primary,
                      side: const BorderSide(color: AppTheme.primary, width: 2),
                      minimumSize: const Size(0, 54),
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(27),
                      ),
                    ),
                    child: Text(
                      'Back',
                      style: GoogleFonts.nunitoSans(
                        fontSize: 16,
                        fontWeight: FontWeight.w700,
                      ),
                    ),
                  ),
                ),
                const SizedBox(width: 14),
              ],
              Expanded(
                flex: isFirstStep ? 1 : 2,
                child: ElevatedButton(
                  onPressed: _goNext,
                  style: ElevatedButton.styleFrom(
                    backgroundColor: AppTheme.primary,
                    foregroundColor: Colors.white,
                    minimumSize: const Size(0, 54),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(27),
                    ),
                    elevation: 0,
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(
                        _currentStep == _totalSteps - 2 ? 'Review' : 'Continue',
                        style: GoogleFonts.nunitoSans(
                          fontSize: 16,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      const SizedBox(width: 6),
                      const Icon(Icons.arrow_forward_rounded, size: 18),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }

  Future<void> _submitSetup() async {
    setState(() {
      _isSubmitting = true;
      _submitError = null;
    });

    try {
      final payload = buildPayload(
        caregiverData: _caregiverData,
        patientData: _patientData,
        medications: _medications,
        meals: _meals,
        activities: _activities,
        familyMembers: _familyMembers,
        emergencyContacts: _emergencyContacts,
      );

      await ApiService().postSetup(payload);

      if (!mounted) return;
      Navigator.pushNamedAndRemoveUntil(
        context,
        AppRoutes.patientHomeScreen,
        (route) => false,
      );
    } on ApiException catch (e) {
      setState(() {
        _isSubmitting = false;
        _submitError = e.message;
      });
    } catch (e) {
      setState(() {
        _isSubmitting = false;
        _submitError = 'Something went wrong. Please try again.';
      });
    }
  }
}
