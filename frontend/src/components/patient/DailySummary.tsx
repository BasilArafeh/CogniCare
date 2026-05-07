import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { colors, fonts, withAlpha } from '../../theme/colors';

interface Props {
  patientName: string;
}

interface SummaryItem {
  icon: string;
  iconColor: string;
  title: string;
  detail: string;
  time: string;
  hour: number; // 0-23 for comparison
}

const ITEMS: SummaryItem[] = [
  {
    icon: 'pill',
    iconColor: colors.primary,
    title: 'Medication',
    detail: 'Donepezil 10mg',
    time: '8:00 PM',
    hour: 20,
  },
  {
    icon: 'silverware-fork-knife',
    iconColor: colors.secondary,
    title: 'Meal',
    detail: 'Lunch',
    time: '12:30 PM',
    hour: 12,
  },
  {
    icon: 'shoe-sneaker',
    iconColor: '#F59E0B',
    title: 'Activity',
    detail: 'Morning Walk',
    time: '9:00 AM',
    hour: 9,
  },
  {
    icon: 'phone',
    iconColor: colors.primaryDark,
    title: 'Family Call',
    detail: 'Sarah',
    time: '3:00 PM',
    hour: 15,
  },
];

function formatDate(d: Date): string {
  return d.toLocaleDateString('en-US', {
    weekday: 'long',
    month: 'long',
    day: 'numeric',
  });
}

export default function DailySummary({ patientName }: Props) {
  const now = new Date();
  const currentHour = now.getHours();

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

      {/* Items */}
      {ITEMS.map((item) => {
        const isDone = item.hour < currentHour;
        return (
          <View key={item.title} style={styles.row}>
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
      })}
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
