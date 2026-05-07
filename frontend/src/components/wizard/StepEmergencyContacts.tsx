import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { colors, fonts, withAlpha } from '../../theme/colors';
import WizardTextField from './WizardTextField';

export interface EmergencyContactItem {
  id: string;
  name: string;
  phone: string;
  relationship: string;
  priority: string;
}

function makeId() {
  return Math.random().toString(36).slice(2, 9);
}

function emptyContact(): EmergencyContactItem {
  return { id: makeId(), name: '', phone: '', relationship: '', priority: 'Primary' };
}

export function initialEmergencyContacts(): EmergencyContactItem[] {
  return [emptyContact()];
}

const PRIORITIES = [
  { label: 'Primary', color: colors.error },
  { label: 'Secondary', color: colors.warning },
  { label: 'Backup', color: colors.textMuted },
];

interface Props {
  contacts: EmergencyContactItem[];
  onContactsChange: (items: EmergencyContactItem[]) => void;
}

function ContactCard({
  item,
  index,
  canRemove,
  onUpdate,
  onRemove,
}: {
  item: EmergencyContactItem;
  index: number;
  canRemove: boolean;
  onUpdate: (field: keyof EmergencyContactItem, value: string) => void;
  onRemove: () => void;
}) {
  const priorityMeta = PRIORITIES.find((p) => p.label === item.priority) ?? PRIORITIES[0];

  return (
    <View style={[styles.card, { borderLeftColor: priorityMeta.color, borderLeftWidth: 4 }]}>
      <View style={styles.cardHeader}>
        <View style={[styles.iconCircle, { backgroundColor: withAlpha(priorityMeta.color, 0.12) }]}>
          <MaterialCommunityIcons name="phone-alert" size={18} color={priorityMeta.color} />
        </View>
        <View style={{ flex: 1 }}>
          <Text style={styles.cardTitle}>
            {item.name.trim() || `Emergency Contact ${index + 1}`}
          </Text>
          <Text style={[styles.priorityBadge, { color: priorityMeta.color }]}>
            {item.priority}
          </Text>
        </View>
        {canRemove && (
          <TouchableOpacity onPress={onRemove} style={styles.removeBtn}>
            <MaterialCommunityIcons name="close-circle" size={20} color={colors.error} />
          </TouchableOpacity>
        )}
      </View>

      <WizardTextField
        label="Full Name *"
        hint="Emergency contact's name"
        value={item.name}
        onChangeText={(v) => onUpdate('name', v)}
        prefixIconName="account"
      />
      <WizardTextField
        label="Phone Number *"
        hint="+1 (555) 000-0000"
        value={item.phone}
        onChangeText={(v) => onUpdate('phone', v)}
        keyboardType="phone-pad"
        prefixIconName="phone"
      />
      <WizardTextField
        label="Relationship"
        hint="e.g. Doctor, Neighbor, Sibling"
        value={item.relationship}
        onChangeText={(v) => onUpdate('relationship', v)}
        prefixIconName="account-question"
      />

      <Text style={styles.priorityLabel}>Priority Level</Text>
      <View style={styles.priorityRow}>
        {PRIORITIES.map((p) => {
          const selected = item.priority === p.label;
          return (
            <TouchableOpacity
              key={p.label}
              onPress={() => onUpdate('priority', p.label)}
              style={[
                styles.priorityPill,
                { borderColor: selected ? p.color : withAlpha(colors.textMuted, 0.3) },
                selected && { backgroundColor: withAlpha(p.color, 0.1) },
              ]}
            >
              <View style={[styles.priorityDot, { backgroundColor: p.color }]} />
              <Text style={[styles.priorityText, { color: selected ? p.color : colors.textSecondary }]}>
                {p.label}
              </Text>
            </TouchableOpacity>
          );
        })}
      </View>
    </View>
  );
}

export default function StepEmergencyContacts({ contacts, onContactsChange }: Props) {
  const handleUpdate = (id: string, field: keyof EmergencyContactItem, value: string) => {
    onContactsChange(
      contacts.map((c) => (c.id === id ? { ...c, [field]: value } : c)),
    );
  };

  const handleRemove = (id: string) => {
    onContactsChange(contacts.filter((c) => c.id !== id));
  };

  const handleAdd = () => {
    onContactsChange([...contacts, emptyContact()]);
  };

  return (
    <View>
      <Text style={styles.hint}>
        Add emergency contacts who should be notified in case of an emergency.
      </Text>
      {contacts.map((contact, i) => (
        <ContactCard
          key={contact.id}
          item={contact}
          index={i}
          canRemove={contacts.length > 1}
          onUpdate={(f, v) => handleUpdate(contact.id, f, v)}
          onRemove={() => handleRemove(contact.id)}
        />
      ))}
      <TouchableOpacity onPress={handleAdd} style={styles.addBtn}>
        <MaterialCommunityIcons name="phone-plus" size={20} color={colors.error} />
        <Text style={[styles.addBtnText, { color: colors.error }]}>Add Emergency Contact</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  hint: {
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
    borderColor: withAlpha(colors.error, 0.15),
    padding: 16,
    marginBottom: 14,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.06,
    shadowRadius: 8,
    elevation: 2,
    overflow: 'hidden',
  },
  cardHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  iconCircle: {
    width: 38,
    height: 38,
    borderRadius: 19,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  cardTitle: {
    fontSize: 14,
    fontFamily: fonts.semiBold,
    color: colors.textPrimary,
  },
  priorityBadge: {
    fontSize: 11,
    fontFamily: fonts.semiBold,
    marginTop: 2,
  },
  removeBtn: { padding: 4 },
  priorityLabel: {
    fontSize: 13,
    fontFamily: fonts.semiBold,
    color: colors.textSecondary,
    marginBottom: 8,
  },
  priorityRow: {
    flexDirection: 'row',
    gap: 8,
  },
  priorityPill: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 9,
    borderRadius: 10,
    borderWidth: 1.5,
    gap: 5,
  },
  priorityDot: {
    width: 7,
    height: 7,
    borderRadius: 3.5,
  },
  priorityText: {
    fontSize: 12,
    fontFamily: fonts.semiBold,
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
    borderColor: withAlpha(colors.error, 0.4),
    backgroundColor: withAlpha(colors.error, 0.04),
  },
  addBtnText: {
    fontSize: 14,
    fontFamily: fonts.semiBold,
  },
});
