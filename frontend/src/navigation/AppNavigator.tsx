import React from 'react';
import { createStackNavigator } from '@react-navigation/stack';
import WelcomeScreen from '../screens/WelcomeScreen';
import CaregiverOnboardingWizardScreen from '../screens/CaregiverOnboardingWizardScreen';
import PatientHomeScreen from '../screens/PatientHomeScreen';

export type RootStackParamList = {
  Welcome: undefined;
  CaregiverOnboarding: undefined;
  PatientHome: undefined;
};

const Stack = createStackNavigator<RootStackParamList>();

export default function AppNavigator() {
  return (
    <Stack.Navigator
      initialRouteName="Welcome"
      screenOptions={{ headerShown: false }}
    >
      <Stack.Screen name="Welcome" component={WelcomeScreen} />
      <Stack.Screen name="CaregiverOnboarding" component={CaregiverOnboardingWizardScreen} />
      <Stack.Screen name="PatientHome" component={PatientHomeScreen} />
    </Stack.Navigator>
  );
}
