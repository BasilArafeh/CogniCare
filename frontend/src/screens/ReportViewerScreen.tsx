import React, { useState } from 'react';
import {
  View, Text, TouchableOpacity, StyleSheet,
  Alert, ActivityIndicator, ScrollView,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import * as FileSystem from 'expo-file-system/legacy';
import type { RouteProp } from '@react-navigation/native';
import type { StackNavigationProp } from '@react-navigation/stack';
import type { RootStackParamList } from '../navigation/AppNavigator';
import { colors, fonts, withAlpha } from '../theme/colors';

type Props = {
  route: RouteProp<RootStackParamList, 'ReportViewer'>;
  navigation: StackNavigationProp<RootStackParamList, 'ReportViewer'>;
};

function formatDate(dateStr: string): string {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });
}

export default function ReportViewerScreen({ route, navigation }: Props) {
  const { title, period, reportDate, pdfUrl } = route.params;
  const insets = useSafeAreaInsets();
  const [saving, setSaving] = useState(false);

  const handleViewPdf = () => {
    if (!pdfUrl) {
      Alert.alert('Not Available', 'This report does not have a PDF attached.');
      return;
    }
    navigation.navigate('PdfViewer', { title, pdfUrl });
  };

  const handleDownload = async () => {
    if (!pdfUrl) return;
    setSaving(true);
    try {
      const fileName = pdfUrl.split('/').pop() ?? 'report.pdf';
      const destUri = `${FileSystem.documentDirectory}${fileName}`;
      await FileSystem.downloadAsync(pdfUrl, destUri);
      Alert.alert('Downloaded', 'Report saved to your device successfully.');
    } catch {
      Alert.alert('Error', 'Could not download the report. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <LinearGradient
      colors={['#F0EAFF', '#F5F3FF']}
      style={[styles.container, { paddingTop: insets.top }]}
    >
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity
          onPress={() => navigation.goBack()}
          style={styles.backBtn}
          activeOpacity={0.7}
        >
          <MaterialCommunityIcons name="arrow-left" size={22} color={colors.primary} />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Care Report</Text>
        <View style={styles.headerSpacer} />
      </View>

      <ScrollView
        contentContainerStyle={styles.scroll}
        showsVerticalScrollIndicator={false}
      >
        {/* Report info card */}
        <View style={styles.card}>
          <View style={styles.iconWrap}>
            <MaterialCommunityIcons name="file-pdf-box" size={48} color={colors.primary} />
          </View>

          <Text style={styles.cardTitle}>{title}</Text>

          {period ? (
            <View style={styles.metaRow}>
              <MaterialCommunityIcons name="calendar-range" size={15} color={colors.textSecondary} />
              <Text style={styles.metaText}>{period}</Text>
            </View>
          ) : null}

          <View style={styles.metaRow}>
            <MaterialCommunityIcons name="clock-outline" size={15} color={colors.textSecondary} />
            <Text style={styles.metaText}>Generated {formatDate(reportDate)}</Text>
          </View>
        </View>

        {/* Action buttons */}
        <View style={styles.actions}>
          <TouchableOpacity
            style={[styles.btn, styles.btnPrimary, !pdfUrl && styles.btnDisabled]}
            onPress={handleViewPdf}
            activeOpacity={0.8}
            disabled={!pdfUrl}
          >
            <MaterialCommunityIcons name="eye-outline" size={20} color={colors.white} />
            <Text style={styles.btnTextPrimary}>View PDF</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.btn, styles.btnSecondary, (!pdfUrl || saving) && styles.btnSecondaryDisabled]}
            onPress={handleDownload}
            activeOpacity={0.8}
            disabled={!pdfUrl || saving}
          >
            {saving ? (
              <ActivityIndicator color={colors.primary} size="small" />
            ) : (
              <MaterialCommunityIcons name="download-outline" size={20} color={colors.primary} />
            )}
            <Text style={styles.btnTextSecondary}>{saving ? 'Saving…' : 'Download PDF'}</Text>
          </TouchableOpacity>
        </View>

        {!pdfUrl && (
          <View style={styles.noPdfBanner}>
            <MaterialCommunityIcons name="alert-circle-outline" size={16} color="#B45309" />
            <Text style={styles.noPdfText}>PDF is not yet available for this report.</Text>
          </View>
        )}
      </ScrollView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: withAlpha(colors.primary, 0.1),
    backgroundColor: 'rgba(255,255,255,0.6)',
  },
  backBtn: {
    width: 40,
    height: 40,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 12,
    backgroundColor: withAlpha(colors.primary, 0.08),
  },
  headerTitle: {
    flex: 1,
    textAlign: 'center',
    fontSize: 17,
    fontFamily: fonts.bold,
    color: colors.textPrimary,
  },
  headerSpacer: { width: 40 },
  scroll: {
    padding: 20,
    gap: 16,
  },
  card: {
    backgroundColor: colors.white,
    borderRadius: 20,
    padding: 24,
    alignItems: 'center',
    gap: 10,
    borderWidth: 1,
    borderColor: withAlpha(colors.primary, 0.12),
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.08,
    shadowRadius: 12,
    elevation: 4,
  },
  iconWrap: {
    width: 80,
    height: 80,
    borderRadius: 24,
    backgroundColor: withAlpha(colors.primary, 0.08),
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 4,
  },
  cardTitle: {
    fontSize: 17,
    fontFamily: fonts.bold,
    color: colors.textPrimary,
    textAlign: 'center',
  },
  metaRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  metaText: {
    fontSize: 14,
    fontFamily: fonts.regular,
    color: colors.textSecondary,
  },
  actions: {
    gap: 12,
  },
  btn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
    borderRadius: 14,
    paddingVertical: 15,
  },
  btnPrimary: {
    backgroundColor: colors.primary,
  },
  btnSecondary: {
    backgroundColor: colors.white,
    borderWidth: 1.5,
    borderColor: colors.primary,
  },
  btnDisabled: {
    backgroundColor: withAlpha(colors.textMuted, 0.15),
    borderWidth: 0,
  },
  btnSecondaryDisabled: {
    borderColor: withAlpha(colors.textMuted, 0.3),
  },
  btnTextPrimary: {
    fontSize: 15,
    fontFamily: fonts.bold,
    color: colors.white,
  },
  btnTextSecondary: {
    fontSize: 15,
    fontFamily: fonts.bold,
    color: colors.primary,
  },
  noPdfBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: '#FFFBEB',
    borderRadius: 12,
    padding: 12,
    borderWidth: 1,
    borderColor: '#FDE68A',
  },
  noPdfText: {
    flex: 1,
    fontSize: 13,
    fontFamily: fonts.regular,
    color: '#B45309',
  },
});
