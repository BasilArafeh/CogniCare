import React, { useEffect, useState, useCallback } from 'react';
import {
  View, Text, ScrollView, StyleSheet, TouchableOpacity,
  ActivityIndicator, RefreshControl,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useNavigation } from '@react-navigation/native';
import type { StackNavigationProp } from '@react-navigation/stack';
import type { RootStackParamList } from '../../navigation/AppNavigator';
import { colors, fonts, withAlpha } from '../../theme/colors';
import apiService, { type WeeklyReportDisplay } from '../../services/apiService';

type Nav = StackNavigationProp<RootStackParamList, 'CaregiverDashboard'>;

interface Props {
  patientId: number;
  caregiverId: number;
  patientName: string;
}

function formatDate(dateStr: string): string {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

export default function DashboardReportsTab({ patientId, caregiverId, patientName }: Props) {
  const navigation = useNavigation<Nav>();
  const [reports, setReports] = useState<WeeklyReportDisplay[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const fetchReports = useCallback(async () => {
    const data = await apiService.getWeeklyReports(caregiverId, patientId);
    setReports(data);
  }, [caregiverId, patientId]);

  useEffect(() => {
    setLoading(true);
    fetchReports().finally(() => setLoading(false));
  }, [fetchReports]);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    fetchReports().finally(() => setRefreshing(false));
  }, [fetchReports]);

  const handleOpen = (report: WeeklyReportDisplay) => {
    navigation.navigate('ReportViewer', {
      title: report.title,
      period: report.period,
      reportDate: report.reportDate,
      pdfUrl: report.pdfUrl,
    });
  };

  return (
    <ScrollView
      style={styles.scroll}
      contentContainerStyle={styles.content}
      showsVerticalScrollIndicator={false}
      refreshControl={
        <RefreshControl refreshing={refreshing} onRefresh={onRefresh} tintColor={colors.primary} />
      }
    >
      {/* Header */}
      <LinearGradient
        colors={['#4A2D9A', '#7C5CBF']}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 1 }}
        style={styles.header}
      >
        <View style={styles.headerIcon}>
          <MaterialCommunityIcons name="file-chart" size={28} color={colors.white} />
        </View>
        <View style={styles.headerText}>
          <Text style={styles.headerTitle}>Care Reports</Text>
          <Text style={styles.headerSub}>{patientName}'s health progress reports</Text>
        </View>
      </LinearGradient>

      {/* Info banner */}
      <View style={styles.infoBanner}>
        <MaterialCommunityIcons name="information-outline" size={16} color={colors.primary} />
        <Text style={styles.infoText}>
          Tap any report to view and download the full PDF. Pull down to refresh.
        </Text>
      </View>

      {loading ? (
        <View style={styles.loadingWrap}>
          <ActivityIndicator color={colors.primary} size="large" />
          <Text style={styles.loadingText}>Loading reports…</Text>
        </View>
      ) : reports.length === 0 ? (
        <EmptyReports />
      ) : (
        <View style={styles.list}>
          <Text style={styles.listLabel}>
            {reports.length} report{reports.length !== 1 ? 's' : ''} available
          </Text>
          {reports.map((report, index) => (
            <ReportCard
              key={report.reportId}
              report={report}
              index={index}
              onOpen={() => handleOpen(report)}
            />
          ))}
        </View>
      )}
    </ScrollView>
  );
}

function ReportCard({ report, index, onOpen }: {
  report: WeeklyReportDisplay;
  index: number;
  onOpen: () => void;
}) {
  const isLatest = index === 0;

  return (
    <TouchableOpacity
      style={[styles.card, isLatest && styles.cardLatest]}
      onPress={onOpen}
      activeOpacity={0.85}
    >
      {isLatest && (
        <View style={styles.latestBadge}>
          <Text style={styles.latestBadgeText}>Latest</Text>
        </View>
      )}

      <View style={styles.cardTop}>
        <View style={[styles.cardIconWrap, isLatest && styles.cardIconWrapLatest]}>
          <MaterialCommunityIcons
            name="file-pdf-box"
            size={26}
            color={isLatest ? colors.white : colors.primary}
          />
        </View>

        <View style={styles.cardInfo}>
          <Text style={styles.cardTitle} numberOfLines={2}>{report.title}</Text>
          {report.period ? (
            <View style={styles.dateRow}>
              <MaterialCommunityIcons name="calendar-range" size={13} color={colors.textSecondary} />
              <Text style={styles.dateText}>{report.period}</Text>
            </View>
          ) : null}
          <View style={styles.dateRow}>
            <MaterialCommunityIcons name="clock-outline" size={12} color={colors.textMuted} />
            <Text style={styles.createdText}>Generated {formatDate(report.reportDate)}</Text>
          </View>
        </View>

        <MaterialCommunityIcons name="chevron-right" size={20} color={colors.textMuted} />
      </View>
    </TouchableOpacity>
  );
}

function EmptyReports() {
  return (
    <View style={styles.emptyWrap}>
      <View style={styles.emptyIconWrap}>
        <MaterialCommunityIcons name="file-clock-outline" size={48} color={withAlpha(colors.primary, 0.35)} />
      </View>
      <Text style={styles.emptyTitle}>No Reports Yet</Text>
      <Text style={styles.emptySub}>
        Reports will appear here once they have been generated. Pull down to refresh.
      </Text>
      <View style={styles.emptyHint}>
        <MaterialCommunityIcons name="refresh" size={14} color={colors.primary} />
        <Text style={styles.emptyHintText}>Pull down to refresh</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  scroll: { flex: 1 },
  content: { paddingBottom: 32 },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
    margin: 20,
    marginBottom: 12,
    padding: 20,
    borderRadius: 20,
  },
  headerIcon: {
    width: 52,
    height: 52,
    borderRadius: 16,
    backgroundColor: 'rgba(255,255,255,0.2)',
    alignItems: 'center',
    justifyContent: 'center',
  },
  headerText: { flex: 1 },
  headerTitle: {
    fontSize: 20,
    fontFamily: fonts.extraBold,
    color: colors.white,
    marginBottom: 2,
  },
  headerSub: {
    fontSize: 13,
    fontFamily: fonts.regular,
    color: 'rgba(255,255,255,0.75)',
  },
  infoBanner: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 8,
    marginHorizontal: 20,
    marginBottom: 20,
    backgroundColor: withAlpha(colors.primary, 0.07),
    borderRadius: 12,
    padding: 12,
    borderWidth: 1,
    borderColor: withAlpha(colors.primary, 0.15),
  },
  infoText: {
    flex: 1,
    fontSize: 12,
    fontFamily: fonts.regular,
    color: colors.textSecondary,
    lineHeight: 18,
  },
  loadingWrap: {
    paddingTop: 80,
    alignItems: 'center',
    gap: 12,
  },
  loadingText: {
    fontSize: 14,
    fontFamily: fonts.regular,
    color: colors.textSecondary,
  },
  list: {
    paddingHorizontal: 20,
    gap: 12,
  },
  listLabel: {
    fontSize: 13,
    fontFamily: fonts.semiBold,
    color: colors.textSecondary,
    marginBottom: 4,
  },
  card: {
    backgroundColor: colors.white,
    borderRadius: 18,
    padding: 16,
    borderWidth: 1,
    borderColor: withAlpha(colors.primary, 0.1),
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.07,
    shadowRadius: 10,
    elevation: 3,
  },
  cardLatest: {
    borderColor: withAlpha(colors.primary, 0.35),
    borderWidth: 1.5,
  },
  latestBadge: {
    alignSelf: 'flex-start',
    backgroundColor: withAlpha(colors.primary, 0.1),
    paddingHorizontal: 10,
    paddingVertical: 3,
    borderRadius: 8,
    marginBottom: 10,
  },
  latestBadgeText: {
    fontSize: 11,
    fontFamily: fonts.bold,
    color: colors.primary,
  },
  cardTop: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 14,
  },
  cardIconWrap: {
    width: 50,
    height: 50,
    borderRadius: 14,
    backgroundColor: withAlpha(colors.primary, 0.1),
    alignItems: 'center',
    justifyContent: 'center',
  },
  cardIconWrapLatest: {
    backgroundColor: colors.primary,
  },
  cardInfo: { flex: 1, gap: 3 },
  cardTitle: {
    fontSize: 15,
    fontFamily: fonts.bold,
    color: colors.textPrimary,
  },
  dateRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  dateText: {
    fontSize: 13,
    fontFamily: fonts.semiBold,
    color: colors.textSecondary,
  },
  createdText: {
    fontSize: 12,
    fontFamily: fonts.regular,
    color: colors.textMuted,
  },
  emptyWrap: {
    alignItems: 'center',
    paddingHorizontal: 36,
    paddingTop: 60,
    gap: 12,
  },
  emptyIconWrap: {
    width: 96,
    height: 96,
    borderRadius: 48,
    backgroundColor: withAlpha(colors.primary, 0.07),
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 8,
  },
  emptyTitle: {
    fontSize: 18,
    fontFamily: fonts.bold,
    color: colors.textPrimary,
  },
  emptySub: {
    fontSize: 13,
    fontFamily: fonts.regular,
    color: colors.textSecondary,
    textAlign: 'center',
    lineHeight: 20,
  },
  emptyHint: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    marginTop: 8,
  },
  emptyHintText: {
    fontSize: 13,
    fontFamily: fonts.semiBold,
    color: colors.primary,
  },
});
