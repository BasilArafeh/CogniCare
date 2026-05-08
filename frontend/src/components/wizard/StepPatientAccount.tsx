import React, { useState } from 'react';
import { View, Text, TouchableOpacity, Platform, StyleSheet } from 'react-native';
import DateTimePicker from '@react-native-community/datetimepicker';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { colors, fonts, withAlpha } from '../../theme/colors';
import WizardFormCard from './WizardFormCard';
import WizardTextField from './WizardTextField';

export interface PatientAccountData {
  firstName: string;
  lastName: string;
  username: string;
  pin: string;
  contactNo: string;
  gender: string;
  diagnosisStage: string;
  dob: string;
  address: string;
  medicalNotes: string;
  allergies: string;
}

interface Props {
  data: PatientAccountData;
  onChange: (key: keyof PatientAccountData, value: string) => void;
}

const GENDERS = ['Female', 'Male'];
const STAGES = [
  { label: 'Mild', color: colors.success },
  { label: 'Moderate', color: colors.warning },
];

function parseDob(dob: string): Date {
  if (dob && /^\d{4}-\d{2}-\d{2}$/.test(dob)) {
    return new Date(dob + 'T12:00:00');
  }
  return new Date(1950, 0, 1);
}

function formatDobDisplay(dob: string): string {
  if (!dob) return '';
  const [y, m, d] = dob.split('-').map(Number);
  return new Date(y, m - 1, d).toLocaleDateString('en-US', {
    month: 'long', day: 'numeric', year: 'numeric',
  });
}

export default function StepPatientAccount({ data, onChange }: Props) {
  const [showDobPicker, setShowDobPicker] = useState(false);

  const onDobChange = (_: unknown, selectedDate?: Date) => {
    if (Platform.OS === 'android') setShowDobPicker(false);
    if (selectedDate) {
      const y = selectedDate.getFullYear();
      const m = (selectedDate.getMonth() + 1).toString().padStart(2, '0');
      const d = selectedDate.getDate().toString().padStart(2, '0');
      onChange('dob', `${y}-${m}-${d}`);
    }
  };

  return (
    <View>
      {/* Patient Identity */}
      <WizardFormCard
        title="Patient Identity"
        subtitle="Personal information about the person in your care"
        icon="account-heart"
        iconColor={colors.secondary}
      >
        <View style={styles.row}>
          <View style={{ flex: 1, marginRight: 8 }}>
            <WizardTextField
              label="First Name *"
              hint="First name"
              value={data.firstName}
              onChangeText={(v) => onChange('firstName', v)}
              prefixIconName="account"
            />
          </View>
          <View style={{ flex: 1 }}>
            <WizardTextField
              label="Last Name"
              hint="Last name"
              value={data.lastName}
              onChangeText={(v) => onChange('lastName', v)}
              prefixIconName="account-outline"
            />
          </View>
        </View>
        <WizardTextField
          label="Contact Number"
          hint="+1 (555) 000-0000"
          value={data.contactNo}
          onChangeText={(v) => onChange('contactNo', v)}
          keyboardType="phone-pad"
          prefixIconName="phone"
        />
        <Text style={styles.selectLabel}>Gender</Text>
        <View style={[styles.pillRow, { marginBottom: 0 }]}>
          {GENDERS.map((g) => {
            const selected = data.gender === g;
            return (
              <TouchableOpacity
                key={g}
                onPress={() => onChange('gender', g)}
                style={[styles.pill, selected && styles.pillSelected]}
              >
                <Text style={[styles.pillText, selected && styles.pillTextSelected]}>{g}</Text>
              </TouchableOpacity>
            );
          })}
        </View>
      </WizardFormCard>

      {/* Login Credentials */}
      <WizardFormCard
        title="Login Credentials"
        subtitle="Username and PIN for patient login"
        icon="numeric"
        iconColor={colors.primaryDark}
      >
        <WizardTextField
          label="Username"
          hint="Choose a simple username"
          value={data.username}
          onChangeText={(v) => onChange('username', v)}
          prefixIconName="at"
        />
        <WizardTextField
          label="4-Digit PIN"
          hint="e.g. 1234"
          value={data.pin}
          onChangeText={(v) => onChange('pin', v.replace(/\D/g, '').slice(0, 4))}
          keyboardType="numeric"
          secureTextEntry
          prefixIconName="lock-outline"
          style={{ marginBottom: 0 }}
        />
      </WizardFormCard>

      {/* Diagnosis */}
      <WizardFormCard
        title="Diagnosis"
        subtitle="Alzheimer's stage and clinical details"
        icon="brain"
        iconColor={colors.primaryDark}
      >
        <Text style={styles.selectLabel}>Alzheimer's Stage</Text>
        <View style={styles.pillRow}>
          {STAGES.map((s) => {
            const selected = data.diagnosisStage === s.label;
            return (
              <TouchableOpacity
                key={s.label}
                onPress={() => onChange('diagnosisStage', s.label)}
                style={[
                  styles.stagePill,
                  { borderColor: selected ? s.color : withAlpha(colors.textMuted, 0.3) },
                  selected && { backgroundColor: withAlpha(s.color, 0.12) },
                ]}
              >
                <View style={[styles.stageDot, { backgroundColor: s.color }]} />
                <Text style={[styles.stageText, { color: selected ? s.color : colors.textSecondary }]}>
                  {s.label}
                </Text>
              </TouchableOpacity>
            );
          })}
        </View>

        <Text style={[styles.selectLabel, { marginTop: 14 }]}>Date of Birth</Text>
        <TouchableOpacity
          onPress={() => setShowDobPicker(true)}
          style={styles.pickerBtn}
        >
          <MaterialCommunityIcons
            name="calendar"
            size={18}
            color={data.dob ? colors.primary : colors.textMuted}
            style={styles.pickerIcon}
          />
          <Text style={[styles.pickerText, !data.dob && styles.pickerPlaceholder]}>
            {data.dob ? formatDobDisplay(data.dob) : 'Select date of birth'}
          </Text>
          <MaterialCommunityIcons name="chevron-down" size={18} color={colors.textMuted} />
        </TouchableOpacity>

        {showDobPicker && (
          <>
            <DateTimePicker
              value={parseDob(data.dob)}
              mode="date"
              display={Platform.OS === 'ios' ? 'spinner' : 'default'}
              maximumDate={new Date()}
              onChange={onDobChange}
            />
            {Platform.OS === 'ios' && (
              <TouchableOpacity
                onPress={() => setShowDobPicker(false)}
                style={styles.doneBtn}
              >
                <Text style={styles.doneBtnText}>Done</Text>
              </TouchableOpacity>
            )}
          </>
        )}
      </WizardFormCard>

      {/* Address & Medical Notes */}
      <WizardFormCard
        title="Address & Medical Notes"
        subtitle="Home address and health information"
        icon="map-marker"
        iconColor={colors.secondary}
      >
        <WizardTextField
          label="Home Address"
          hint="Full home address"
          value={data.address}
          onChangeText={(v) => onChange('address', v)}
          prefixIconName="home"
          multiline
          numberOfLines={2}
        />
        <WizardTextField
          label="Medical Notes"
          hint="Any important medical information..."
          value={data.medicalNotes}
          onChangeText={(v) => onChange('medicalNotes', v)}
          prefixIconName="clipboard-text"
          multiline
          numberOfLines={3}
        />
        <WizardTextField
          label="Known Allergies"
          hint="List any allergies or write 'None'"
          value={data.allergies}
          onChangeText={(v) => onChange('allergies', v)}
          prefixIconName="alert-circle"
          style={{ marginBottom: 0 }}
        />
      </WizardFormCard>
    </View>
  );
}

const styles = StyleSheet.create({
  row: {
    flexDirection: 'row',
  },
  selectLabel: {
    fontSize: 13,
    fontFamily: fonts.semiBold,
    color: colors.textSecondary,
    marginBottom: 8,
  },
  pillRow: {
    flexDirection: 'row',
    gap: 10,
    marginBottom: 4,
  },
  pill: {
    flex: 1,
    paddingVertical: 10,
    borderRadius: 10,
    borderWidth: 1.5,
    borderColor: withAlpha(colors.textMuted, 0.4),
    alignItems: 'center',
    backgroundColor: withAlpha(colors.textMuted, 0.06),
  },
  pillSelected: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  pillText: {
    fontSize: 14,
    fontFamily: fonts.semiBold,
    color: colors.textSecondary,
  },
  pillTextSelected: {
    color: colors.white,
  },
  stagePill: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 10,
    borderRadius: 10,
    borderWidth: 1.5,
    gap: 6,
  },
  stageDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  stageText: {
    fontSize: 13,
    fontFamily: fonts.semiBold,
  },
  pickerBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1.5,
    borderRadius: 12,
    borderColor: withAlpha(colors.textMuted, 0.4),
    backgroundColor: withAlpha(colors.textMuted, 0.06),
    paddingHorizontal: 14,
    paddingVertical: 2,
    minHeight: 50,
    marginBottom: 4,
  },
  pickerIcon: {
    marginRight: 8,
  },
  pickerText: {
    flex: 1,
    fontSize: 15,
    fontFamily: fonts.regular,
    color: colors.textPrimary,
  },
  pickerPlaceholder: {
    color: colors.textMuted,
  },
  doneBtn: {
    alignSelf: 'flex-end',
    paddingHorizontal: 16,
    paddingVertical: 8,
    marginTop: 4,
  },
  doneBtnText: {
    fontSize: 15,
    fontFamily: fonts.semiBold,
    color: colors.primary,
  },
});
