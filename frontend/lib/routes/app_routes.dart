import 'package:flutter/material.dart';

import '../presentation/caregiver_onboarding_wizard_screen/caregiver_onboarding_wizard_screen.dart';
import '../presentation/patient_home_screen/patient_home_screen.dart';
import '../presentation/welcome_screen/welcome_screen.dart';

class AppRoutes {
  static const String initial = '/';
  static const String welcomeScreen = '/welcome-screen';
  static const String caregiverOnboardingWizardScreen =
      '/caregiver-onboarding-wizard-screen';
  static const String patientHomeScreen = '/patient-home-screen';

  static Map<String, WidgetBuilder> routes = {
    initial: (context) => const WelcomeScreen(),
    welcomeScreen: (context) => const WelcomeScreen(),
    caregiverOnboardingWizardScreen: (context) =>
        const CaregiverOnboardingWizardScreen(),
    patientHomeScreen: (context) => const PatientHomeScreen(),
  };
}
