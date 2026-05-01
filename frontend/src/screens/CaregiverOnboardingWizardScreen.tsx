import React, { useState, useRef } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  ScrollView,
  Animated,
  Alert,
  StyleSheet,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useNavigation } from '@react-navigation/native';
import type { StackNavigationProp } from '@react-navigation/stack';
import { colors, fonts, withAlpha } from '../theme/colors';
import type { RootStackParamList } from '../navigation/AppNavigator';
import apiService, { buildPayload } from '../services/apiService';
import WizardProgress from '../components/wizard/WizardProgress';
import StepCaregiverAccount, {
  CaregiverAccountData,
} from '../components/wizard/StepCaregiverAccount';
import StepPatientAccount, {
  PatientAccountData,
} from '../components/wizard/StepPatientAccount';
import StepMedications, {
  MedicationItem,
  initialMedications,
} from '../components/wizard/StepMedications';
import StepMeals, {
  MealItem,
  initialMeals,
} from '../components/wizard/StepMeals';
import StepActivities, {
  ActivityItem,
  initialActivities,
} from '../components/wizard/StepActivities';
import StepFamilyMembers, {
  FamilyMemberItem,
  initialFamilyMembers,
} from '../components/wizard/StepFamilyMembers';
import StepEmergencyContacts, {
  EmergencyContactItem,
  initialEmergencyContacts,
} from '../components/wizard/StepEmergencyContacts';
import StepReviewComplete from '../components/wizard/StepReviewComplete';

type NavProp = StackNavigationProp<RootStackParamList, 'CaregiverOnboarding'>;

const TOTAL_STEPS = 8;

const STEP_TITLES = [
  'Your Account',
  'Patient Account',
  'Medications',
  'Meals & Nutrition',
  'Daily Activities',
  'Family Members',
  'Emergency Contacts',
  'All Set!',
];

const STEP_ICONS = [
  'account-circle',
  'account-heart',
  'pill',
  'silverware-fork-knife',
  'run-fast',
  'account-group',
  'phone-alert',
  'check-circle',
];

export default function CaregiverOnboardingWizardScreen() {
  const navigation = useNavigation<NavProp>();
  const insets = useSafeAreaInsets();

  const [currentStep, setCurrentStep] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState('');

  const [caregiverData, setCaregiverData] = useState<CaregiverAccountData>({
    name: '',
    email: '',
    phone: '',
    password: '',
    confirmPassword: '',
  });
  const [patientData, setPatientData] = useState<PatientAccountData>({
    firstName: '',
    lastName: '',
    username: '',
    pin: '',
    contactNo: '',
    gender: '',
    diagnosisStage: '',
    dob: '',
    address: '',
    medicalNotes: '',
    allergies: '',
  });
  const [medications, setMedications] = useState<MedicationItem[]>(initialMedications());
  const [meals, setMeals] = useState<MealItem[]>(initialMeals());
  const [activities, setActivities] = useState<ActivityItem[]>(initialActivities());
  const [familyMembers, setFamilyMembers] = useState<FamilyMemberItem[]>(initialFamilyMembers());
  const [emergencyContacts, setEmergencyContacts] = useState<EmergencyContactItem[]>(
    initialEmergencyContacts(),
  );

  const stepOpacity = useRef(new Animated.Value(1)).current;
  const stepTranslateX = useRef(new Animated.Value(0)).current;
  const directionRef = useRef<1 | -1>(1);

  const animateStepChange = (callback: () => void) => {
    const outX = directionRef.current * -30;
    const inX = directionRef.current * 30;
    Animated.parallel([
      Animated.timing(stepOpacity, { toValue: 0, duration: 150, useNativeDriver: true }),
      Animated.timing(stepTranslateX, { toValue: outX, duration: 150, useNativeDriver: true }),
    ]).start(() => {
      stepTranslateX.setValue(inX);
      callback();
      Animated.parallel([
        Animated.timing(stepOpacity, { toValue: 1, duration: 220, useNativeDriver: true }),
        Animated.timing(stepTranslateX, { toValue: 0, duration: 220, useNativeDriver: true }),
      ]).start();
    });
  };

  const validateStep = (step: number): boolean => {
    switch (step) {
      case 0:
        if (!caregiverData.name.trim()) {
          Alert.alert('Required', 'Please enter your full name.'); return false;
        }
        if (!caregiverData.email.trim()) {
          Alert.alert('Required', 'Please enter your email address.'); return false;
        }
        if (!caregiverData.password.trim()) {
          Alert.alert('Required', 'Please create a password.'); return false;
        }
        if (caregiverData.password !== caregiverData.confirmPassword) {
          Alert.alert('Mismatch', 'Passwords do not match.'); return false;
        }
        return true;
      case 1:
        if (!patientData.firstName.trim()) {
          Alert.alert('Required', "Please enter the patient's first name."); return false;
        }
        if (!patientData.username.trim()) {
          Alert.alert('Required', 'Please choose a username.'); return false;
        }
        if (patientData.pin.length !== 4) {
          Alert.alert('Required', 'Please enter a 4-digit PIN.'); return false;
        }
        return true;
      case 2:
        if (medications.some((m) => !m.name.trim())) {
          Alert.alert('Required', 'Please enter a name for each medication.'); return false;
        }
        return true;
      case 3:
        if (meals.some((m) => !m.mealName.trim())) {
          Alert.alert('Required', 'Please enter a name for each meal.'); return false;
        }
        return true;
      case 4:
        if (activities.some((a) => !a.name.trim())) {
          Alert.alert('Required', 'Please enter a name for each activity.'); return false;
        }
        return true;
      case 5:
        if (familyMembers.some((f) => !f.firstName.trim())) {
          Alert.alert('Required', 'Please enter a first name for each family member.'); return false;
        }
        return true;
      case 6:
        if (emergencyContacts.some((c) => !c.name.trim() || !c.phone.trim())) {
          Alert.alert('Required', 'Please enter name and phone for each emergency contact.'); return false;
        }
        return true;
      default:
        return true;
    }
  };

  const handleContinue = () => {
    if (!validateStep(currentStep)) return;
    if (currentStep < TOTAL_STEPS - 1) {
      directionRef.current = 1;
      animateStepChange(() => setCurrentStep((s) => s + 1));
    }
  };

  const handleBack = () => {
    if (currentStep === 0) {
      navigation.goBack();
      return;
    }
    directionRef.current = -1;
    animateStepChange(() => setCurrentStep((s) => s - 1));
  };

  const handleSubmit = async () => {
    setIsSubmitting(true);
    setSubmitError('');
    try {
      const payload = buildPayload(
        caregiverData,
        patientData,
        medications,
        meals,
        activities,
        familyMembers,
        emergencyContacts,
      );
      await apiService.postSetup(payload);
    } catch (err: unknown) {
      console.warn('Setup API error (continuing):', err);
    } finally {
      setIsSubmitting(false);
      navigation.reset({ index: 0, routes: [{ name: 'PatientHome' }] });
    }
  };

  const changeCaregiverData = (key: keyof CaregiverAccountData, value: string) => {
    setCaregiverData((prev) => ({ ...prev, [key]: value }));
  };
  const changePatientData = (key: keyof PatientAccountData, value: string) => {
    setPatientData((prev) => ({ ...prev, [key]: value }));
  };

  const isLastStep = currentStep === TOTAL_STEPS - 1;
  const patientFullName = [patientData.firstName, patientData.lastName].filter(Boolean).join(' ');

  const renderStep = () => {
    switch (currentStep) {
      case 0:
        return <StepCaregiverAccount data={caregiverData} onChange={changeCaregiverData} />;
      case 1:
        return <StepPatientAccount data={patientData} onChange={changePatientData} />;
      case 2:
        return (
          <StepMedications medications={medications} onMedicationsChange={setMedications} />
        );
      case 3:
        return <StepMeals meals={meals} onMealsChange={setMeals} />;
      case 4:
        return (
          <StepActivities activities={activities} onActivitiesChange={setActivities} />
        );
      case 5:
        return (
          <StepFamilyMembers
            familyMembers={familyMembers}
            onFamilyMembersChange={setFamilyMembers}
          />
        );
      case 6:
        return (
          <StepEmergencyContacts
            contacts={emergencyContacts}
            onContactsChange={setEmergencyContacts}
          />
        );
      case 7:
        return (
          <StepReviewComplete
            caregiverName={caregiverData.name}
            patientName={patientFullName || 'Patient'}
            medicationCount={medications.length}
            mealCount={meals.length}
            activityCount={activities.length}
            familyCount={familyMembers.length}
            emergencyCount={emergencyContacts.length}
            isSubmitting={isSubmitting}
            submitError={submitError}
            onComplete={handleSubmit}
          />
        );
      default:
        return null;
    }
  };

  return (
    <LinearGradient
      colors={['#F0EAFF', '#F5F3FF']}
      style={[styles.container, { paddingTop: insets.top }]}
    >
      {/* Top Bar */}
      <View style={styles.topBar}>
        <TouchableOpacity onPress={handleBack} style={styles.backBtn}>
          <MaterialCommunityIcons name="chevron-left" size={26} color={colors.primary} />
        </TouchableOpacity>
        <View style={styles.topBarBrand}>
          <MaterialCommunityIcons name="heart-pulse" size={17} color={colors.primary} />
          <Text style={styles.topBarBrandText}>CogniCare</Text>
        </View>
        <View style={styles.stepBadge}>
          <Text style={styles.stepBadgeText}>{currentStep + 1}/{TOTAL_STEPS}</Text>
        </View>
      </View>

      {/* Progress */}
      <WizardProgress
        currentStep={currentStep}
        totalSteps={TOTAL_STEPS}
        stepTitles={STEP_TITLES}
        stepIcons={STEP_ICONS}
      />

      {/* Step Content */}
      <ScrollView
        style={styles.scroll}
        contentContainerStyle={styles.scrollContent}
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}
      >
        <Animated.View
          style={{
            opacity: stepOpacity,
            transform: [{ translateX: stepTranslateX }],
          }}
        >
          {renderStep()}
        </Animated.View>
      </ScrollView>

      {/* Bottom Navigation */}
      {!isLastStep && (
        <View
          style={[
            styles.bottomNav,
            { paddingBottom: Math.max(insets.bottom, 16) },
          ]}
        >
          <TouchableOpacity onPress={handleBack} style={styles.backButton}>
            <MaterialCommunityIcons name="chevron-left" size={20} color={colors.primary} />
            <Text style={styles.backButtonText}>Back</Text>
          </TouchableOpacity>

          <TouchableOpacity
            onPress={handleContinue}
            activeOpacity={0.85}
            style={styles.continueWrapper}
          >
            <LinearGradient
              colors={[colors.primary, colors.primaryMuted]}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 0 }}
              style={styles.continueBtn}
            >
              <Text style={styles.continueText}>
                {currentStep === TOTAL_STEPS - 2 ? 'Review' : 'Continue'}
              </Text>
              <MaterialCommunityIcons name="chevron-right" size={20} color={colors.white} />
            </LinearGradient>
          </TouchableOpacity>
        </View>
      )}
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  topBar: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
  },
  backBtn: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: withAlpha(colors.primary, 0.1),
    alignItems: 'center',
    justifyContent: 'center',
  },
  topBarBrand: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
  },
  topBarBrandText: {
    fontSize: 16,
    fontFamily: fonts.bold,
    color: colors.textPrimary,
    letterSpacing: 0.2,
  },
  stepBadge: {
    width: 48,
    height: 26,
    borderRadius: 13,
    backgroundColor: withAlpha(colors.primary, 0.12),
    alignItems: 'center',
    justifyContent: 'center',
  },
  stepBadgeText: {
    fontSize: 12,
    fontFamily: fonts.bold,
    color: colors.primary,
  },
  scroll: {
    flex: 1,
  },
  scrollContent: {
    padding: 20,
    paddingBottom: 32,
  },
  bottomNav: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingTop: 12,
    backgroundColor: withAlpha(colors.white, 0.8),
    borderTopWidth: 1,
    borderTopColor: withAlpha(colors.primaryMuted, 0.2),
    gap: 12,
  },
  backButton: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 18,
    paddingVertical: 14,
    borderRadius: 14,
    borderWidth: 1.5,
    borderColor: withAlpha(colors.primary, 0.3),
    backgroundColor: withAlpha(colors.primary, 0.05),
    gap: 4,
  },
  backButtonText: {
    fontSize: 15,
    fontFamily: fonts.semiBold,
    color: colors.primary,
  },
  continueWrapper: {
    flex: 1,
    borderRadius: 14,
    overflow: 'hidden',
    shadowColor: colors.primary,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.2,
    shadowRadius: 10,
    elevation: 5,
  },
  continueBtn: {
    height: 52,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    borderRadius: 14,
  },
  continueText: {
    fontSize: 16,
    fontFamily: fonts.bold,
    color: colors.white,
  },
});
