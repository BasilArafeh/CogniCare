import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { colors, fonts, withAlpha } from '../../theme/colors';
import WizardFormCard from './WizardFormCard';
import WizardTextField from './WizardTextField';

export interface PatientInfoData {
  diagnosisStage: string;
  dob: string;
  address: string;
  medicalNotes: string;
  allergies: string;
  cognitiveNeeds: string;
  commPref: string;
}

interface Props {
  data: PatientInfoData;
  onChange: (key: keyof PatientInfoData, value: string) => void;
}

const STAGES = [
  { label: 'Mild', color: colors.success },
  { label: 'Moderate', color: colors.warning },
  { label: 'Severe', color: colors.error },
];

const COMM_PREFS = ['Voice', 'Text', 'Both'];

export default function StepPatientInfo({ data, onChange }: Props) {
  return (
    <View>
      {/* Diagnosis */}
      <WizardFormCard
        title="Diagnosis"
        subtitle="Alzheimer's stage and clinical details"
        icon="brain"
        iconColor={colors.primaryDark}
      >
        <Text style={styles.selectLabel}>Alzheimer's Stage</Text>
        <View style={styles.stageRow}>
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
        <WizardTextField
          label="Date of Birth"
          hint="MM/DD/YYYY"
          value={data.dob}
          onChangeText={(v) => onChange('dob', v)}
          prefixIconName="calendar"
          style={{ marginTop: 14, marginBottom: 0 }}
        />
      </WizardFormCard>

      {/* Address & Notes */}
      <WizardFormCard
        title="Address & Notes"
        subtitle="Medical history and location"
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

      {/* Care Preferences */}
      <WizardFormCard
        title="Care Preferences"
        subtitle="Communication and cognitive needs"
        icon="heart-settings"
        iconColor={colors.primary}
      >
        <WizardTextField
          label="Cognitive Needs"
          hint="Describe specific cognitive requirements..."
          value={data.cognitiveNeeds}
          onChangeText={(v) => onChange('cognitiveNeeds', v)}
          prefixIconName="head-cog"
          multiline
          numberOfLines={2}
        />
        <Text style={styles.selectLabel}>Communication Preference</Text>
        <View style={styles.commRow}>
          {COMM_PREFS.map((p) => {
            const selected = data.commPref === p;
            return (
              <TouchableOpacity
                key={p}
                onPress={() => onChange('commPref', p)}
                style={[
                  styles.commPill,
                  selected && styles.commPillSelected,
                ]}
              >
                <Text style={[styles.commText, selected && styles.commTextSelected]}>
                  {p}
                </Text>
              </TouchableOpacity>
            );
          })}
        </View>
      </WizardFormCard>
    </View>
  );
}

const styles = StyleSheet.create({
  selectLabel: {
    fontSize: 13,
    fontFamily: fonts.semiBold,
    color: colors.textSecondary,
    marginBottom: 8,
  },
  stageRow: {
    flexDirection: 'row',
    gap: 10,
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
  commRow: {
    flexDirection: 'row',
    gap: 10,
  },
  commPill: {
    flex: 1,
    paddingVertical: 10,
    borderRadius: 10,
    borderWidth: 1.5,
    borderColor: withAlpha(colors.textMuted, 0.4),
    alignItems: 'center',
    backgroundColor: withAlpha(colors.textMuted, 0.06),
  },
  commPillSelected: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  commText: {
    fontSize: 13,
    fontFamily: fonts.semiBold,
    color: colors.textSecondary,
  },
  commTextSelected: {
    color: colors.white,
  },
});
