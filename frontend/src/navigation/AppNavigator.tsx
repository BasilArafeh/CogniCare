import React from 'react';
import { createStackNavigator } from '@react-navigation/stack';
import LoadingScreen from '../screens/LoadingScreen';
import WelcomeScreen from '../screens/WelcomeScreen';
import CaregiverOnboardingWizardScreen from '../screens/CaregiverOnboardingWizardScreen';
import CaregiverSignInScreen from '../screens/CaregiverSignInScreen';
import PatientLoginScreen from '../screens/PatientLoginScreen';
import PatientHomeScreen from '../screens/PatientHomeScreen';
import CaregiverDashboardScreen from '../screens/CaregiverDashboardScreen';
import ReportViewerScreen from '../screens/ReportViewerScreen';
import PdfViewerScreen from '../screens/PdfViewerScreen';

export type RootStackParamList = {
  Loading: undefined;
  Welcome: undefined;
  CaregiverOnboarding: undefined;
  CaregiverSignIn: undefined;
  PatientLogin: undefined;
  PatientHome: { patientId: number; patientName: string };
  CaregiverDashboard: {
    patientId: number;
    caregiverId: number;
    caregiverName: string;
    patientName: string;
  };
  ReportViewer: {
    title: string;
    period: string;
    reportDate: string;
    pdfUrl: string;
  };
  PdfViewer: {
    title: string;
    pdfUrl: string;
  };
};

const Stack = createStackNavigator<RootStackParamList>();

export default function AppNavigator() {
  return (
    <Stack.Navigator
      initialRouteName="Loading"
      screenOptions={{ headerShown: false }}
    >
      <Stack.Screen name="Loading" component={LoadingScreen} />
      <Stack.Screen name="Welcome" component={WelcomeScreen} />
      <Stack.Screen name="CaregiverOnboarding" component={CaregiverOnboardingWizardScreen} />
      <Stack.Screen name="CaregiverSignIn" component={CaregiverSignInScreen} />
      <Stack.Screen name="PatientLogin" component={PatientLoginScreen} />
      <Stack.Screen name="PatientHome" component={PatientHomeScreen} />
      <Stack.Screen name="CaregiverDashboard" component={CaregiverDashboardScreen} />
      <Stack.Screen name="ReportViewer" component={ReportViewerScreen} />
      <Stack.Screen name="PdfViewer" component={PdfViewerScreen} />
    </Stack.Navigator>
  );
}
