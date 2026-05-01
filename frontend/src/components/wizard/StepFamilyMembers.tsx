import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { colors, fonts, withAlpha } from '../../theme/colors';
import WizardTextField from './WizardTextField';

export interface FamilyMemberItem {
  id: string;
  firstName: string;
  lastName: string;
  relationship: string;
  contactNo: string;
}

function makeId() {
  return Math.random().toString(36).slice(2, 9);
}

function emptyMember(): FamilyMemberItem {
  return { id: makeId(), firstName: '', lastName: '', relationship: '', contactNo: '' };
}

export function initialFamilyMembers(): FamilyMemberItem[] {
  return [emptyMember()];
}

const AVATAR_ICONS = [
  'account-circle',
  'account-cowboy-hat',
  'account-tie',
  'account-heart',
  'account-star',
];

interface Props {
  familyMembers: FamilyMemberItem[];
  onFamilyMembersChange: (items: FamilyMemberItem[]) => void;
}

function MemberCard({
  item,
  index,
  canRemove,
  onUpdate,
  onRemove,
}: {
  item: FamilyMemberItem;
  index: number;
  canRemove: boolean;
  onUpdate: (field: keyof FamilyMemberItem, value: string) => void;
  onRemove: () => void;
}) {
  const avatarIcon = AVATAR_ICONS[index % AVATAR_ICONS.length];
  const displayName = [item.firstName, item.lastName].filter(Boolean).join(' ');

  return (
    <View style={styles.card}>
      <View style={styles.cardHeader}>
        <View style={styles.avatar}>
          <MaterialCommunityIcons name={avatarIcon as any} size={22} color={colors.primary} />
        </View>
        <Text style={styles.cardTitle}>
          {displayName.trim() || `Family Member ${index + 1}`}
        </Text>
        {canRemove && (
          <TouchableOpacity onPress={onRemove} style={styles.removeBtn}>
            <MaterialCommunityIcons name="close-circle" size={20} color={colors.error} />
          </TouchableOpacity>
        )}
      </View>
      <View style={styles.row}>
        <View style={{ flex: 1, marginRight: 8 }}>
          <WizardTextField
            label="First Name *"
            hint="First name"
            value={item.firstName}
            onChangeText={(v) => onUpdate('firstName', v)}
            prefixIconName="account"
          />
        </View>
        <View style={{ flex: 1 }}>
          <WizardTextField
            label="Last Name"
            hint="Last name"
            value={item.lastName}
            onChangeText={(v) => onUpdate('lastName', v)}
            prefixIconName="account-outline"
          />
        </View>
      </View>
      <WizardTextField
        label="Relationship"
        hint="e.g. Son, Daughter, Spouse"
        value={item.relationship}
        onChangeText={(v) => onUpdate('relationship', v)}
        prefixIconName="family-tree"
      />
      <WizardTextField
        label="Contact Number"
        hint="+1 (555) 000-0000"
        value={item.contactNo}
        onChangeText={(v) => onUpdate('contactNo', v)}
        keyboardType="phone-pad"
        prefixIconName="phone"
        style={{ marginBottom: 0 }}
      />
    </View>
  );
}

export default function StepFamilyMembers({ familyMembers, onFamilyMembersChange }: Props) {
  const handleUpdate = (id: string, field: keyof FamilyMemberItem, value: string) => {
    onFamilyMembersChange(
      familyMembers.map((m) => (m.id === id ? { ...m, [field]: value } : m)),
    );
  };

  const handleRemove = (id: string) => {
    onFamilyMembersChange(familyMembers.filter((m) => m.id !== id));
  };

  const handleAdd = () => {
    onFamilyMembersChange([...familyMembers, emptyMember()]);
  };

  return (
    <View>
      <Text style={styles.hint}>
        Add family members who will be involved in the patient's care.
      </Text>
      {familyMembers.map((member, i) => (
        <MemberCard
          key={member.id}
          item={member}
          index={i}
          canRemove={familyMembers.length > 1}
          onUpdate={(f, v) => handleUpdate(member.id, f, v)}
          onRemove={() => handleRemove(member.id)}
        />
      ))}
      <TouchableOpacity onPress={handleAdd} style={styles.addBtn}>
        <MaterialCommunityIcons name="account-plus" size={20} color={colors.primary} />
        <Text style={styles.addBtnText}>Add Family Member</Text>
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
  avatar: {
    width: 38,
    height: 38,
    borderRadius: 19,
    backgroundColor: colors.primaryLight,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  cardTitle: {
    flex: 1,
    fontSize: 14,
    fontFamily: fonts.semiBold,
    color: colors.textPrimary,
  },
  removeBtn: { padding: 4 },
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
  },
  addBtnText: {
    fontSize: 14,
    fontFamily: fonts.semiBold,
    color: colors.primary,
  },
});
