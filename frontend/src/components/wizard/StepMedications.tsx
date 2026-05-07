import React, { useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { colors, fonts, withAlpha } from '../../theme/colors';
import WizardTextField from './WizardTextField';
import TimePickerModal from '../TimePickerModal';

export interface MedicationItem {
  id: string;
  name: string;
  dosage: string;
  time: string;
  notes: string;
}

function makeId() {
  return Math.random().toString(36).slice(2, 9);
}

function emptyMed(): MedicationItem {
  return { id: makeId(), name: '', dosage: '', time: '', notes: '' };
}

function formatTime12h(timeStr: string): string {
  if (!timeStr) return '';
  const [hStr, mStr] = timeStr.split(':');
  const h = parseInt(hStr, 10);
  const period = h >= 12 ? 'PM' : 'AM';
  const h12 = h % 12 || 12;
  return `${h12}:${mStr} ${period}`;
}

interface Props {
  medications: MedicationItem[];
  onMedicationsChange: (items: MedicationItem[]) => void;
}

function MedCard({
  item,
  index,
  canRemove,
  onUpdate,
  onRemove,
}: {
  item: MedicationItem;
  index: number;
  canRemove: boolean;
  onUpdate: (field: keyof MedicationItem, value: string) => void;
  onRemove: () => void;
}) {
  const [showTimePicker, setShowTimePicker] = useState(false);

  return (
    <View style={styles.card}>
      <View style={styles.cardHeader}>
        <View style={styles.indexBadge}>
          <Text style={styles.indexText}>{index + 1}</Text>
        </View>
        <Text style={styles.cardTitle}>
          {item.name.trim() || `Medication ${index + 1}`}
        </Text>
        {canRemove && (
          <TouchableOpacity onPress={onRemove} style={styles.removeBtn}>
            <MaterialCommunityIcons name="close-circle" size={20} color={colors.error} />
          </TouchableOpacity>
        )}
      </View>

      <WizardTextField
        label="Medication Name *"
        hint="e.g. Donepezil"
        value={item.name}
        onChangeText={(v) => onUpdate('name', v)}
        prefixIconName="pill"
      />

      <View style={styles.row}>
        <View style={{ flex: 1, marginRight: 8 }}>
          <WizardTextField
            label="Dosage"
            hint="e.g. 10"
            value={item.dosage}
            onChangeText={(v) => onUpdate('dosage', v)}
            keyboardType="decimal-pad"
            prefixIconName="weight"
          />
        </View>
        <View style={{ flex: 1 }}>
          <Text style={styles.fieldLabel}>Time</Text>
          <TouchableOpacity
            onPress={() => setShowTimePicker(true)}
            style={styles.pickerBtn}
          >
            <MaterialCommunityIcons
              name="clock-outline"
              size={18}
              color={item.time ? colors.primary : colors.textMuted}
              style={styles.pickerIcon}
            />
            <Text style={[styles.pickerText, !item.time && styles.pickerPlaceholder]}>
              {item.time ? formatTime12h(item.time) : 'Select time'}
            </Text>
          </TouchableOpacity>
        </View>
      </View>

      <TimePickerModal
        visible={showTimePicker}
        initialTime={item.time}
        title="Medication Time"
        onConfirm={(t) => { onUpdate('time', t); setShowTimePicker(false); }}
        onCancel={() => setShowTimePicker(false)}
      />

      <WizardTextField
        label="Notes"
        hint="Any special instructions..."
        value={item.notes}
        onChangeText={(v) => onUpdate('notes', v)}
        prefixIconName="note-text"
        multiline
        numberOfLines={2}
        style={{ marginBottom: 0 }}
      />
    </View>
  );
}

export default function StepMedications({ medications, onMedicationsChange }: Props) {
  const handleUpdate = (id: string, field: keyof MedicationItem, value: string) => {
    onMedicationsChange(
      medications.map((m) => (m.id === id ? { ...m, [field]: value } : m)),
    );
  };

  const handleRemove = (id: string) => {
    onMedicationsChange(medications.filter((m) => m.id !== id));
  };

  const handleAdd = () => {
    onMedicationsChange([...medications, emptyMed()]);
  };

  return (
    <View>
      <Text style={styles.sectionHint}>
        Add all medications the patient takes regularly.
      </Text>
      {medications.map((med, i) => (
        <MedCard
          key={med.id}
          item={med}
          index={i}
          canRemove={medications.length > 1}
          onUpdate={(f, v) => handleUpdate(med.id, f, v)}
          onRemove={() => handleRemove(med.id)}
        />
      ))}
      <TouchableOpacity onPress={handleAdd} style={styles.addBtn}>
        <MaterialCommunityIcons name="plus-circle" size={20} color={colors.primary} />
        <Text style={styles.addBtnText}>Add Another Medication</Text>
      </TouchableOpacity>
    </View>
  );
}

export function initialMedications(): MedicationItem[] {
  return [emptyMed()];
}

const styles = StyleSheet.create({
  sectionHint: {
    fontSize: 13,
    fontFamily: fonts.regular,
    color: colors.textSecondary,
    marginBottom: 16,
    lineHeight: 19,
  },
  card: {
    backgroundColor: colors.white,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: withAlpha(colors.primary, 0.12),
    padding: 16,
    marginBottom: 14,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.06,
    shadowRadius: 8,
    elevation: 2,
  },
  cardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  indexBadge: {
    width: 26,
    height: 26,
    borderRadius: 13,
    backgroundColor: colors.primaryLight,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 10,
  },
  indexText: {
    fontSize: 13,
    fontFamily: fonts.bold,
    color: colors.primary,
  },
  cardTitle: {
    flex: 1,
    fontSize: 14,
    fontFamily: fonts.semiBold,
    color: colors.textPrimary,
  },
  removeBtn: {
    padding: 4,
  },
  row: {
    flexDirection: 'row',
  },
  fieldLabel: {
    fontSize: 13,
    fontFamily: fonts.semiBold,
    color: colors.textSecondary,
    marginBottom: 6,
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
    marginBottom: 14,
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
  addBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    paddingVertical: 14,
    borderRadius: 14,
    borderWidth: 1.5,
    borderStyle: 'dashed',
    borderColor: colors.primaryMuted,
    backgroundColor: colors.primaryLight,
    marginTop: 4,
  },
  addBtnText: {
    fontSize: 14,
    fontFamily: fonts.semiBold,
    color: colors.primary,
  },
});
