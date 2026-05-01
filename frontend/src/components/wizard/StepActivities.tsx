import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { colors, fonts, withAlpha } from '../../theme/colors';
import WizardTextField from './WizardTextField';

export interface ActivityItem {
  id: string;
  name: string;
  startTime: string;
  endTime: string;
  description: string;
}

function makeId() {
  return Math.random().toString(36).slice(2, 9);
}

function emptyActivity(): ActivityItem {
  return { id: makeId(), name: '', startTime: '', endTime: '', description: '' };
}

export function initialActivities(): ActivityItem[] {
  return [emptyActivity()];
}

interface Props {
  activities: ActivityItem[];
  onActivitiesChange: (items: ActivityItem[]) => void;
}

function ActivityCard({
  item,
  index,
  canRemove,
  onUpdate,
  onRemove,
}: {
  item: ActivityItem;
  index: number;
  canRemove: boolean;
  onUpdate: (field: keyof ActivityItem, value: string) => void;
  onRemove: () => void;
}) {
  return (
    <View style={styles.card}>
      <View style={styles.cardHeader}>
        <View style={styles.indexBadge}>
          <MaterialCommunityIcons name="run-fast" size={16} color={colors.primary} />
        </View>
        <Text style={styles.cardTitle}>
          {item.name.trim() || `Activity ${index + 1}`}
        </Text>
        {canRemove && (
          <TouchableOpacity onPress={onRemove} style={styles.removeBtn}>
            <MaterialCommunityIcons name="close-circle" size={20} color={colors.error} />
          </TouchableOpacity>
        )}
      </View>
      <WizardTextField
        label="Activity Name *"
        hint="e.g. Morning Walk"
        value={item.name}
        onChangeText={(v) => onUpdate('name', v)}
        prefixIconName="shoe-sneaker"
      />
      <View style={styles.row}>
        <View style={{ flex: 1, marginRight: 8 }}>
          <WizardTextField
            label="Start Time"
            hint="e.g. 9:00 AM"
            value={item.startTime}
            onChangeText={(v) => onUpdate('startTime', v)}
            prefixIconName="clock-start"
          />
        </View>
        <View style={{ flex: 1 }}>
          <WizardTextField
            label="End Time"
            hint="e.g. 9:30 AM"
            value={item.endTime}
            onChangeText={(v) => onUpdate('endTime', v)}
            prefixIconName="clock-end"
          />
        </View>
      </View>
      <WizardTextField
        label="Description"
        hint="Brief description of the activity..."
        value={item.description}
        onChangeText={(v) => onUpdate('description', v)}
        prefixIconName="text"
        multiline
        numberOfLines={2}
        style={{ marginBottom: 0 }}
      />
    </View>
  );
}

export default function StepActivities({ activities, onActivitiesChange }: Props) {
  const handleUpdate = (id: string, field: keyof ActivityItem, value: string) => {
    onActivitiesChange(
      activities.map((a) => (a.id === id ? { ...a, [field]: value } : a)),
    );
  };

  const handleRemove = (id: string) => {
    onActivitiesChange(activities.filter((a) => a.id !== id));
  };

  const handleAdd = () => {
    onActivitiesChange([...activities, emptyActivity()]);
  };

  return (
    <View>
      <Text style={styles.hint}>
        Schedule daily activities to support a structured routine.
      </Text>
      {activities.map((act, i) => (
        <ActivityCard
          key={act.id}
          item={act}
          index={i}
          canRemove={activities.length > 1}
          onUpdate={(f, v) => handleUpdate(act.id, f, v)}
          onRemove={() => handleRemove(act.id)}
        />
      ))}
      <TouchableOpacity onPress={handleAdd} style={styles.addBtn}>
        <MaterialCommunityIcons name="plus-circle" size={20} color={colors.primary} />
        <Text style={styles.addBtnText}>Add Another Activity</Text>
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
  indexBadge: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: colors.primaryLight,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 10,
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
