import React, { useEffect, useState } from 'react';
import { View, Text, StyleSheet, ActivityIndicator } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { colors, fonts, withAlpha } from '../../theme/colors';
import apiService from '../../services/apiService';
import { formatTime } from '../../utils/time';

interface Props {
  patientId: number;
}

interface SummaryItem {
  key: string;
  icon: string;
  iconColor: string;
  title: string;
  detail: string;
  time: string;
  hour: number;
}

function hourFromTime(t: string): number {
  if (!t) return 0;
  return parseInt(t.split(':')[0], 10);
}

function formatDate(d: Date): string {
  return d.toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
  });
}

export default function DailySummary({ patientId }: Props) {
  const [items, setItems] = useState<SummaryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const now = new Date();
  const currentHour = now.getHours();

  useEffect(() => {
    let cancelled = false;
    async function load() {
      console.log('[DailySummary] loading for patientId =', patientId);
      setLoading(true);
      const [meds, meals, activities] = await Promise.all([
        apiService.getPatientMedications(patientId),
        apiService.getPatientMeals(patientId),
        apiService.getPatientActivities(patientId),
      ]);
      console.log('[DailySummary] loaded | meds =', meds.length, '| meals =', meals.length, '| activities =', activities.length);

      if (cancelled) return;

      const summaryItems: SummaryItem[] = [
        ...meds.map((m) => ({
          key: `med-${m.patientMedicationId}`,
          icon: 'pill',
          iconColor: colors.primary,
          title: 'Medication',
          detail: m.dosage ? `${m.name} ${m.dosage}` : m.name,
          time: formatTime(m.time),
          hour: hourFromTime(m.time),
        })),
        ...meals.map((m) => ({
          key: `meal-${m.patientMealId}`,
          icon: 'silverware-fork-knife',
          iconColor: colors.secondary,
          title: 'Meal',
          detail: m.mealType,
          time: formatTime(m.mealTime),
          hour: hourFromTime(m.mealTime),
        })),
        ...activities.map((a) => ({
          key: `act-${a.patientActivityId}`,
          icon: 'shoe-sneaker',
          iconColor: '#F59E0B',
          title: 'Activity',
          detail: a.description ? `${a.name} — ${a.description}` : a.name,
          time: formatTime(a.startTime),
          hour: hourFromTime(a.startTime),
        })),
      ].sort((a, b) => a.hour - b.hour);

      setItems(summaryItems);
      setLoading(false);
    }
    load();
    return () => { cancelled = true; };
  }, [patientId]);

  return (
    <View style={styles.card}>
      {/* Header */}
      <View style={styles.header}>
        <View style={styles.headerLeft}>
          <View style={styles.sunCircle}>
            <MaterialCommunityIcons name="weather-sunny" size={20} color="#F59E0B" />
          </View>
          <View>
            <Text style={styles.headerTitle}>Today's Plan</Text>
            <Text style={styles.headerDate}>{formatDate(now)}</Text>
          </View>
        </View>
      </View>

      <View style={styles.divider} />

      {loading ? (
        <View style={styles.loadingRow}>
          <ActivityIndicator size="small" color={colors.primary} />
        </View>
      ) : items.length === 0 ? (
        <View style={styles.emptyRow}>
          <Text style={styles.emptyText}>No schedule for today</Text>
        </View>
      ) : (
        items.map((item) => {
          const isDone = item.hour < currentHour;
          return (
            <View key={item.key} style={styles.row}>
              <View
                style={[
                  styles.iconCircle,
                  { backgroundColor: withAlpha(item.iconColor, 0.12) },
                ]}
              >
                <MaterialCommunityIcons
                  name={item.icon as any}
                  size={18}
                  color={isDone ? colors.textMuted : item.iconColor}
                />
              </View>
              <View style={styles.rowContent}>
                <Text
                  style={[
                    styles.rowTitle,
                    isDone && styles.textStrike,
                  ]}
                >
                  {item.detail}
                </Text>
                <Text style={styles.rowMeta}>
                  {item.title} · {item.time}
                </Text>
              </View>
              {isDone ? (
                <View style={styles.doneBadge}>
                  <Text style={styles.doneText}>Done</Text>
                </View>
              ) : (
                <Text style={[styles.timeLabel, { color: item.iconColor }]}>
                  {item.time}
                </Text>
              )}
            </View>
          );
        })
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: colors.white,
    borderRadius: 20,
    marginHorizontal: 16,
    shadowColor: colors.primary,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.1,
    shadowRadius: 14,
    elevation: 4,
    overflow: 'hidden',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 16,
    paddingBottom: 12,
  },
  headerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  sunCircle: {
    width: 38,
    height: 38,
    borderRadius: 19,
    backgroundColor: withAlpha('#F59E0B', 0.12),
    alignItems: 'center',
    justifyContent: 'center',
  },
  headerTitle: {
    fontSize: 15,
    fontFamily: fonts.bold,
    color: colors.textPrimary,
  },
  headerDate: {
    fontSize: 12,
    fontFamily: fonts.regular,
    color: colors.textSecondary,
    marginTop: 2,
  },
  divider: {
    height: 1,
    backgroundColor: withAlpha(colors.primaryMuted, 0.15),
    marginHorizontal: 16,
  },
  loadingRow: {
    paddingVertical: 24,
    alignItems: 'center',
  },
  emptyRow: {
    paddingVertical: 24,
    alignItems: 'center',
  },
  emptyText: {
    fontSize: 14,
    fontFamily: fonts.regular,
    color: colors.textMuted,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: withAlpha(colors.primaryMuted, 0.08),
  },
  iconCircle: {
    width: 36,
    height: 36,
    borderRadius: 18,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  rowContent: {
    flex: 1,
  },
  rowTitle: {
    fontSize: 14,
    fontFamily: fonts.semiBold,
    color: colors.textPrimary,
  },
  textStrike: {
    textDecorationLine: 'line-through',
    color: colors.textMuted,
  },
  rowMeta: {
    fontSize: 12,
    fontFamily: fonts.regular,
    color: colors.textSecondary,
    marginTop: 2,
  },
  doneBadge: {
    backgroundColor: withAlpha(colors.success, 0.12),
    borderRadius: 8,
    paddingHorizontal: 8,
    paddingVertical: 4,
  },
  doneText: {
    fontSize: 11,
    fontFamily: fonts.semiBold,
    color: colors.success,
  },
  timeLabel: {
    fontSize: 12,
    fontFamily: fonts.semiBold,
  },
});
