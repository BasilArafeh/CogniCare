import React from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
} from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { colors, fonts, withAlpha } from '../../theme/colors';
import WizardTextField from './WizardTextField';

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
            hint="e.g. 10mg"
            value={item.dosage}
            onChangeText={(v) => onUpdate('dosage', v)}
            prefixIconName="weight"
          />
        </View>
        <View style={{ flex: 1 }}>
          <WizardTextField
            label="Time"
            hint="e.g. 8:00 PM"
            value={item.time}
            onChangeText={(v) => onUpdate('time', v)}
            prefixIconName="clock-outline"
          />
        </View>
      </View>
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
