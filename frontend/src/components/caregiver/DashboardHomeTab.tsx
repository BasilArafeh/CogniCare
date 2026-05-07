import React, { useEffect, useState, useCallback } from 'react';
import {
  View, Text, ScrollView, TouchableOpacity,
  StyleSheet, ActivityIndicator, RefreshControl,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { colors, fonts, withAlpha } from '../../theme/colors';
import apiService, {
  type MedDisplay, type MealDisplay,
  type ActivityDisplay, type FamilyDisplay, type PatientRow,
} from '../../services/apiService';

interface Props {
  patientId: number;
  caregiverId: number;
  caregiverName: string;
  patientName: string;
  onGoToPatient: () => void;
}

function getGreeting() {
  const h = new Date().getHours();
  if (h < 12) return 'Good morning';
  if (h < 17) return 'Good afternoon';
  return 'Good evening';
}

function formatTime(t: string): string {
  if (!t) return '';
  const [h, m] = t.split(':').map(Number);
  const period = h >= 12 ? 'PM' : 'AM';
  return `${h % 12 || 12}:${String(m).padStart(2, '0')} ${period}`;
}

function todayLabel() {
  return new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' });
}

interface ScheduleItem {
  key: string;
  time: string;
  sortMin: number;
  icon: string;
  iconColor: string;
  label: string;
  sub: string;
}

export default function DashboardHomeTab({ patientId, caregiverName, patientName, onGoToPatient }: Props) {
  const [patient, setPatient] = useState<PatientRow | null>(null);
  const [meds, setMeds] = useState<MedDisplay[]>([]);
  const [meals, setMeals] = useState<MealDisplay[]>([]);
  const [activities, setActivities] = useState<ActivityDisplay[]>([]);
  const [family, setFamily] = useState<FamilyDisplay[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchAll = useCallback(async () => {
    const [p, m, ml, ac, fm] = await Promise.all([
      apiService.getPatient(patientId),
      apiService.getPatientMedications(patientId),
      apiService.getPatientMeals(patientId),
      apiService.getPatientActivities(patientId),
      apiService.getFamilyMembers(patientId),
    ]);
    setPatient(p);
    setMeds(m);
    setMeals(ml);
    setActivities(ac);
    setFamily(fm);
  }, [patientId]);

  useEffect(() => {
    setLoading(true);
    fetchAll().finally(() => setLoading(false));
  }, [fetchAll]);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchAll().finally(() => setRefreshing(false));
  }, [fetchAll]);

  const scheduleItems: ScheduleItem[] = [
    ...meds.map((m) => {
      const [h, min] = m.time.split(':').map(Number);
      return {
        key: `med-${m.patientMedicationId}`,
        time: formatTime(m.time),
        sortMin: h * 60 + (min || 0),
        icon: 'pill',
        iconColor: colors.primary,
        label: m.name,
        sub: m.dosage ? `${m.dosage}mg` : 'Medication',
      };
    }),
    ...meals.map((m) => {
      const [h, min] = m.mealTime.split(':').map(Number);
      return {
        key: `meal-${m.patientMealId}`,
        time: formatTime(m.mealTime),
        sortMin: h * 60 + (min || 0),
        icon: 'silverware-fork-knife',
        iconColor: colors.secondary,
        label: m.mealType,
        sub: 'Meal',
      };
    }),
    ...activities.map((a) => {
      const [h, min] = a.startTime.split(':').map(Number);
      return {
        key: `act-${a.patientActivityId}`,
        time: formatTime(a.startTime),
        sortMin: h * 60 + (min || 0),
        icon: 'run-fast',
        iconColor: '#F59E0B',
        label: a.name,
        sub: a.endTime ? `Until ${formatTime(a.endTime)}` : 'Activity',
      };
    }),
  ].sort((a, b) => a.sortMin - b.sortMin);

  const firstName = caregiverName.split(' ')[0] || caregiverName;

  return (
    <ScrollView
      style={styles.scroll}
      contentContainerStyle={styles.scrollContent}
      showsVerticalScrollIndicator={false}
      refreshControl={<RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.primary} />}
    >
      {/* Header */}
      <View style={styles.header}>
        <View>
          <Text style={styles.greeting}>{getGreeting()}, {firstName} !</Text>
          <Text style={styles.dateLabel}>{todayLabel()}</Text>
        </View>
      </View>
      

      {loading ? (
        <View style={styles.loadingWrap}>
          <ActivityIndicator color={colors.primary} size="large" />
        </View>
      ) : (
        <>
          {/* Patient Card */}
          <LinearGradient
            colors={[colors.primary, colors.primaryDark]}
            start={{ x: 0, y: 0 }} end={{ x: 1, y: 1 }}
            style={styles.patientCard}
          >
            <View style={styles.patientCardIcon}>
              <MaterialCommunityIcons name="account-heart" size={32} color={colors.white} />
            </View>
            <View style={styles.patientCardInfo}>
              <Text style={styles.patientCardName}>{patientName}</Text>
              <Text style={styles.patientCardSub}>
                {patient?.diagnosis_stage
                  ? `${patient.diagnosis_stage} · Memory Care`
                  : 'Memory Care Patient'}
              </Text>
              {patient?.dob ? (
                <Text style={styles.patientCardDetail}>
                  DOB: {new Date(patient.dob).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' })}
                </Text>
              ) : null}
            </View>
            <View style={styles.patientCardBadge}>
              <MaterialCommunityIcons name="shield-check" size={14} color={withAlpha(colors.white, 0.9)} />
              <Text style={styles.patientCardBadgeText}>Active</Text>
            </View>
          </LinearGradient>

          {/* Stats Row */}
          <Text style={styles.sectionTitle}>Today's Overview</Text>
          <View style={styles.statsRow}>
            {[
              { icon: 'pill',                  label: 'Medications', count: meds.length,       bg: withAlpha(colors.primary, 0.1),   color: colors.primary },
              { icon: 'silverware-fork-knife', label: 'Meals',       count: meals.length,      bg: withAlpha(colors.secondary, 0.1), color: colors.secondary },
              { icon: 'run-fast',              label: 'Activities',  count: activities.length, bg: withAlpha('#F59E0B', 0.1),        color: '#F59E0B' },
              { icon: 'account-group',         label: 'Family',      count: family.length,     bg: withAlpha(colors.primaryDark, 0.1), color: colors.primaryDark },
            ].map((s) => (
              <View key={s.label} style={[styles.statCard, { backgroundColor: s.bg }]}>
                <MaterialCommunityIcons name={s.icon as any} size={20} color={s.color} />
                <Text style={[styles.statCount, { color: s.color }]}>{s.count}</Text>
                <Text style={styles.statLabel}>{s.label}</Text>
              </View>
            ))}
          </View>

          {/* Today's Schedule */}
          <Text style={styles.sectionTitle}>Today's Schedule</Text>
          <View style={styles.card}>
            {scheduleItems.length === 0 ? (
              <View style={styles.emptyRow}>
                <MaterialCommunityIcons name="calendar-blank" size={28} color={colors.textMuted} />
                <Text style={styles.emptyText}>No schedule configured yet</Text>
              </View>
            ) : (
              scheduleItems.map((item, idx) => (
                <View key={item.key} style={[styles.scheduleRow, idx < scheduleItems.length - 1 && styles.scheduleRowBorder]}>
                  <View style={[styles.scheduleIconCircle, { backgroundColor: withAlpha(item.iconColor, 0.12) }]}>
                    <MaterialCommunityIcons name={item.icon as any} size={16} color={item.iconColor} />
                  </View>
                  <View style={styles.scheduleInfo}>
                    <Text style={styles.scheduleLabel}>{item.label}</Text>
                    <Text style={styles.scheduleSub}>{item.sub}</Text>
                  </View>
                  <Text style={styles.scheduleTime}>{item.time}</Text>
                </View>
              ))
            )}
          </View>

          {/* Family Contacts */}
          {family.length > 0 && (
            <>
              <Text style={styles.sectionTitle}>Family Members</Text>
              <View style={styles.card}>
                {family.map((f, idx) => (
                  <View key={f.familyMemberId} style={[styles.familyRow, idx < family.length - 1 && styles.scheduleRowBorder]}>
                    <View style={styles.familyAvatar}>
                      <Text style={styles.familyAvatarText}>
                        {(f.firstName[0] ?? '?').toUpperCase()}
                      </Text>
                    </View>
                    <View style={styles.scheduleInfo}>
                      <Text style={styles.scheduleLabel}>{f.firstName} {f.lastName}</Text>
                      <Text style={styles.scheduleSub}>{f.relationship ?? 'Family'}</Text>
                    </View>
                    {f.contactNo ? (
                      <View style={styles.contactBadge}>
                        <MaterialCommunityIcons name="phone" size={12} color={colors.secondary} />
                        <Text style={styles.contactBadgeText} numberOfLines={1}>{f.contactNo}</Text>
                      </View>
                    ) : null}
                  </View>
                ))}
              </View>
            </>
          )}
        </>
      )}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  scroll: { flex: 1 },
  scrollContent: { padding: 20, paddingBottom: 16 },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: 20,
  },
  greeting: {
    fontSize: 20,
    fontFamily: fonts.extraBold,
    color: colors.textPrimary,
  },
  dateLabel: {
    fontSize: 12,
    fontFamily: fonts.regular,
    color: colors.textSecondary,
    marginTop: 2,
  },
  patientViewBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: withAlpha(colors.primary, 0.1),
    paddingHorizontal: 14,
    paddingVertical: 8,
    borderRadius: 20,
    borderWidth: 1,
    borderColor: withAlpha(colors.primary, 0.2),
  },
  patientViewText: {
    fontSize: 13,
    fontFamily: fonts.semiBold,
    color: colors.primary,
  },
  loadingWrap: {
    flex: 1,
    paddingTop: 80,
    alignItems: 'center',
  },
  // Patient Card
  patientCard: {
    flexDirection: 'row',
    alignItems: 'center',
    borderRadius: 20,
    padding: 18,
    marginBottom: 24,
    gap: 14,
    shadowColor: colors.primary,
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.25,
    shadowRadius: 14,
    elevation: 6,
  },
  patientCardIcon: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: withAlpha('#fff', 0.2),
    alignItems: 'center',
    justifyContent: 'center',
  },
  patientCardInfo: { flex: 1 },
  patientCardName: {
    fontSize: 18,
    fontFamily: fonts.extraBold,
    color: colors.white,
  },
  patientCardSub: {
    fontSize: 12,
    fontFamily: fonts.regular,
    color: withAlpha(colors.white, 0.85),
    marginTop: 2,
  },
  patientCardDetail: {
    fontSize: 11,
    fontFamily: fonts.regular,
    color: withAlpha(colors.white, 0.7),
    marginTop: 4,
  },
  patientCardBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: withAlpha('#fff', 0.15),
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 12,
    alignSelf: 'flex-start',
  },
  patientCardBadgeText: {
    fontSize: 11,
    fontFamily: fonts.semiBold,
    color: colors.white,
  },
  // Section
  sectionTitle: {
    fontSize: 15,
    fontFamily: fonts.bold,
    color: colors.textPrimary,
    marginBottom: 12,
  },
  // Stats
  statsRow: {
    flexDirection: 'row',
    gap: 10,
    marginBottom: 24,
  },
  statCard: {
    flex: 1,
    alignItems: 'center',
    borderRadius: 14,
    paddingVertical: 14,
    gap: 4,
  },
  statCount: {
    fontSize: 20,
    fontFamily: fonts.extraBold,
  },
  statLabel: {
    fontSize: 10,
    fontFamily: fonts.regular,
    color: colors.textSecondary,
    textAlign: 'center',
  },
  // Card
  card: {
    backgroundColor: colors.white,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: withAlpha(colors.primary, 0.1),
    marginBottom: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.06,
    shadowRadius: 8,
    elevation: 2,
    overflow: 'hidden',
  },
  emptyRow: {
    alignItems: 'center',
    paddingVertical: 28,
    gap: 8,
  },
  emptyText: {
    fontSize: 13,
    fontFamily: fonts.regular,
    color: colors.textMuted,
  },
  // Schedule
  scheduleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    gap: 12,
  },
  scheduleRowBorder: {
    borderBottomWidth: 1,
    borderBottomColor: withAlpha(colors.textMuted, 0.12),
  },
  scheduleIconCircle: {
    width: 34,
    height: 34,
    borderRadius: 17,
    alignItems: 'center',
    justifyContent: 'center',
  },
  scheduleInfo: { flex: 1 },
  scheduleLabel: {
    fontSize: 14,
    fontFamily: fonts.semiBold,
    color: colors.textPrimary,
  },
  scheduleSub: {
    fontSize: 12,
    fontFamily: fonts.regular,
    color: colors.textSecondary,
    marginTop: 1,
  },
  scheduleTime: {
    fontSize: 13,
    fontFamily: fonts.bold,
    color: colors.primary,
  },
  // Family
  familyRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    gap: 12,
  },
  familyAvatar: {
    width: 34,
    height: 34,
    borderRadius: 17,
    backgroundColor: colors.primaryLight,
    alignItems: 'center',
    justifyContent: 'center',
  },
  familyAvatarText: {
    fontSize: 14,
    fontFamily: fonts.bold,
    color: colors.primary,
  },
  contactBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: withAlpha(colors.secondary, 0.1),
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 10,
    maxWidth: 120,
  },
  contactBadgeText: {
    fontSize: 10,
    fontFamily: fonts.regular,
    color: colors.secondaryDark,
  },
});
