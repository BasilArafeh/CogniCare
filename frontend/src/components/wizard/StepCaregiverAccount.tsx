import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { colors, fonts } from '../../theme/colors';
import WizardFormCard from './WizardFormCard';
import WizardTextField from './WizardTextField';

export interface CaregiverAccountData {
  name: string;
  email: string;
  phone: string;
  password: string;
  confirmPassword: string;
}

interface Props {
  data: CaregiverAccountData;
  onChange: (key: keyof CaregiverAccountData, value: string) => void;
}

export default function StepCaregiverAccount({ data, onChange }: Props) {
  return (
    <View>
      {/* Intro Banner */}
      <LinearGradient
        colors={[colors.primary, colors.primaryMuted]}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 1 }}
        style={styles.banner}
      >
        <MaterialCommunityIcons name="heart-circle" size={28} color={colors.white} />
        <View style={styles.bannerText}>
          <Text style={styles.bannerTitle}>Welcome to CogniCare</Text>
          <Text style={styles.bannerSub}>
            Create your caregiver account to get started
          </Text>
        </View>
      </LinearGradient>

      {/* Personal Details */}
      <WizardFormCard
        title="Personal Details"
        subtitle="Your contact information"
        icon="account-circle"
        iconColor={colors.primary}
      >
        <WizardTextField
          label="Full Name"
          hint="Enter your full name"
          value={data.name}
          onChangeText={(v) => onChange('name', v)}
          prefixIconName="account"
        />
        <WizardTextField
          label="Email Address"
          hint="your@email.com"
          value={data.email}
          onChangeText={(v) => onChange('email', v)}
          keyboardType="email-address"
          prefixIconName="email"
        />
        <WizardTextField
          label="Phone Number"
          hint="+1 (555) 000-0000"
          value={data.phone}
          onChangeText={(v) => onChange('phone', v)}
          keyboardType="phone-pad"
          prefixIconName="phone"
        />
      </WizardFormCard>

      {/* Create Password */}
      <WizardFormCard
        title="Create Password"
        subtitle="Secure your account"
        icon="lock"
        iconColor={colors.primaryDark}
      >
        <WizardTextField
          label="Password"
          hint="Min. 8 characters"
          value={data.password}
          onChangeText={(v) => onChange('password', v)}
          secureTextEntry
          prefixIconName="lock"
        />
        <WizardTextField
          label="Confirm Password"
          hint="Re-enter your password"
          value={data.confirmPassword}
          onChangeText={(v) => onChange('confirmPassword', v)}
          secureTextEntry
          prefixIconName="lock-check"
          style={{ marginBottom: 0 }}
        />
      </WizardFormCard>
    </View>
  );
}

const styles = StyleSheet.create({
  banner: {
    flexDirection: 'row',
    alignItems: 'center',
    borderRadius: 16,
    padding: 16,
    marginBottom: 16,
    gap: 12,
  },
  bannerText: {
    flex: 1,
  },
  bannerTitle: {
    fontSize: 15,
    fontFamily: fonts.bold,
    color: colors.white,
  },
  bannerSub: {
    fontSize: 12,
    fontFamily: fonts.regular,
    color: colors.white,
    opacity: 0.85,
    marginTop: 2,
  },
});
