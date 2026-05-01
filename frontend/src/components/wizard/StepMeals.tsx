import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { colors, fonts, withAlpha } from '../../theme/colors';
import WizardTextField from './WizardTextField';

export interface MealItem {
  id: string;
  mealName: string;
  mealTime: string;
  notes: string;
}

function makeId() {
  return Math.random().toString(36).slice(2, 9);
}

function emptyMeal(): MealItem {
  return { id: makeId(), mealName: '', mealTime: '', notes: '' };
}

export function initialMeals(): MealItem[] {
  return [emptyMeal()];
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
  return (
    <View style={styles.card}>
      <View style={styles.cardHeader}>
        <View style={styles.iconCircle}>
          <MaterialCommunityIcons name="silverware-fork-knife" size={18} color={colors.primary} />
        </View>
        <Text style={styles.cardTitle}>
          {item.mealName.trim() || `Meal ${index + 1}`}
        </Text>
        {canRemove && (
          <TouchableOpacity onPress={onRemove} style={styles.removeBtn}>
            <MaterialCommunityIcons name="close-circle" size={20} color={colors.error} />
          </TouchableOpacity>
        )}
      </View>
      <WizardTextField
        label="Meal Name *"
        hint="e.g. Breakfast, Lunch, Dinner"
        value={item.mealName}
        onChangeText={(v) => onUpdate('mealName', v)}
        prefixIconName="silverware-fork-knife"
      />
      <WizardTextField
        label="Meal Time"
        hint="e.g. 8:00 AM"
        value={item.mealTime}
        onChangeText={(v) => onUpdate('mealTime', v)}
        prefixIconName="clock-outline"
      />
      <WizardTextField
        label="Notes"
        hint="Any additional notes..."
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
