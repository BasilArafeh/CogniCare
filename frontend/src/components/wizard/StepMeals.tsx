import React, { useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { colors, fonts, withAlpha } from '../../theme/colors';
import TimePickerModal from '../TimePickerModal';

export interface MealItem {
  id: string;
  mealName: string;
  mealTime: string;
  notes: string;
}

const MEAL_TYPES = ['Breakfast', 'Lunch', 'Dinner', 'Snack'];

function makeId() {
  return Math.random().toString(36).slice(2, 9);
}

function emptyMeal(): MealItem {
  return { id: makeId(), mealName: '', mealTime: '', notes: '' };
}

export function initialMeals(): MealItem[] {
  return [emptyMeal()];
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
  meals: MealItem[];
  onMealsChange: (items: MealItem[]) => void;
}

function MealCard({
  item,
  index,
  canRemove,
  onUpdate,
  onRemove,
}: {
  item: MealItem;
  index: number;
  canRemove: boolean;
  onUpdate: (field: keyof MealItem, value: string) => void;
  onRemove: () => void;
}) {
  const [showTimePicker, setShowTimePicker] = useState(false);

  return (
    <View style={styles.card}>
      <View style={styles.cardHeader}>
        <View style={styles.iconCircle}>
          <MaterialCommunityIcons name="silverware-fork-knife" size={18} color={colors.primary} />
        </View>
        <Text style={styles.cardTitle}>
          {item.mealName || `Meal ${index + 1}`}
        </Text>
        {canRemove && (
          <TouchableOpacity onPress={onRemove} style={styles.removeBtn}>
            <MaterialCommunityIcons name="close-circle" size={20} color={colors.error} />
          </TouchableOpacity>
        )}
      </View>

      <Text style={styles.fieldLabel}>Meal Type *</Text>
      <View style={styles.pillRow}>
        {MEAL_TYPES.map((type) => {
          const selected = item.mealName === type;
          return (
            <TouchableOpacity
              key={type}
              onPress={() => onUpdate('mealName', type)}
              style={[styles.pill, selected && styles.pillSelected]}
            >
              <Text style={[styles.pillText, selected && styles.pillTextSelected]}>{type}</Text>
            </TouchableOpacity>
          );
        })}
      </View>

      <Text style={[styles.fieldLabel, { marginTop: 4 }]}>Meal Time</Text>
      <TouchableOpacity
        onPress={() => setShowTimePicker(true)}
        style={styles.pickerBtn}
      >
        <MaterialCommunityIcons
          name="clock-outline"
          size={18}
          color={item.mealTime ? colors.primary : colors.textMuted}
          style={styles.pickerIcon}
        />
        <Text style={[styles.pickerText, !item.mealTime && styles.pickerPlaceholder]}>
          {item.mealTime ? formatTime12h(item.mealTime) : 'Select time'}
        </Text>
        <MaterialCommunityIcons name="chevron-down" size={18} color={colors.textMuted} />
      </TouchableOpacity>

      <TimePickerModal
        visible={showTimePicker}
        initialTime={item.mealTime}
        title="Meal Time"
        onConfirm={(t) => { onUpdate('mealTime', t); setShowTimePicker(false); }}
        onCancel={() => setShowTimePicker(false)}
      />
    </View>
  );
}

export default function StepMeals({ meals, onMealsChange }: Props) {
  const handleUpdate = (id: string, field: keyof MealItem, value: string) => {
    onMealsChange(meals.map((m) => (m.id === id ? { ...m, [field]: value } : m)));
  };

  const handleRemove = (id: string) => {
    onMealsChange(meals.filter((m) => m.id !== id));
  };

  const handleAdd = () => {
    onMealsChange([...meals, emptyMeal()]);
  };

  return (
    <View>
      <Text style={styles.hint}>
        Add the patient's regular meals and schedule.
      </Text>
      {meals.map((meal, i) => (
        <MealCard
          key={meal.id}
          item={meal}
          index={i}
          canRemove={meals.length > 1}
          onUpdate={(f, v) => handleUpdate(meal.id, f, v)}
          onRemove={() => handleRemove(meal.id)}
        />
      ))}
      <TouchableOpacity onPress={handleAdd} style={styles.addBtn}>
        <MaterialCommunityIcons name="plus-circle" size={20} color={colors.primary} />
        <Text style={styles.addBtnText}>Add Another Meal</Text>
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
  iconCircle: {
    width: 34,
    height: 34,
    borderRadius: 17,
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
  fieldLabel: {
    fontSize: 13,
    fontFamily: fonts.semiBold,
    color: colors.textSecondary,
    marginBottom: 8,
  },
  pillRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 8,
    marginBottom: 8,
  },
  pill: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 20,
    borderWidth: 1.5,
    borderColor: withAlpha(colors.textMuted, 0.4),
    backgroundColor: withAlpha(colors.textMuted, 0.06),
  },
  pillSelected: {
    backgroundColor: colors.primary,
    borderColor: colors.primary,
  },
  pillText: {
    fontSize: 13,
    fontFamily: fonts.semiBold,
    color: colors.textSecondary,
  },
  pillTextSelected: {
    color: colors.white,
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
