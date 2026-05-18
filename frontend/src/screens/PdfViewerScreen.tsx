import React, { useState } from 'react';
import { View, Text, TouchableOpacity, StyleSheet, ActivityIndicator } from 'react-native';
import { WebView } from 'react-native-webview';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import type { RouteProp } from '@react-navigation/native';
import type { StackNavigationProp } from '@react-navigation/stack';
import type { RootStackParamList } from '../navigation/AppNavigator';
import { colors, fonts, withAlpha } from '../theme/colors';

type Props = {
  route: RouteProp<RootStackParamList, 'PdfViewer'>;
  navigation: StackNavigationProp<RootStackParamList, 'PdfViewer'>;
};

export default function PdfViewerScreen({ route, navigation }: Props) {
  const { title, pdfUrl } = route.params;
  const insets = useSafeAreaInsets();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  return (
    <View style={[styles.container, { paddingTop: insets.top }]}>
      <View style={styles.header}>
        <TouchableOpacity
          onPress={() => navigation.goBack()}
          style={styles.backBtn}
          activeOpacity={0.7}
        >
          <MaterialCommunityIcons name="arrow-left" size={22} color={colors.primary} />
        </TouchableOpacity>
        <Text style={styles.headerTitle} numberOfLines={1}>{title}</Text>
        <View style={styles.headerSpacer} />
      </View>

      {error ? (
        <View style={styles.errorWrap}>
          <MaterialCommunityIcons name="file-alert-outline" size={48} color={withAlpha(colors.primary, 0.4)} />
          <Text style={styles.errorTitle}>Could not load PDF</Text>
          <Text style={styles.errorSub}>Make sure the backend server is running and accessible from your device.</Text>
        </View>
      ) : (
        <>
          {loading && (
            <View style={styles.loadingWrap}>
              <ActivityIndicator color={colors.primary} size="large" />
              <Text style={styles.loadingText}>Loading PDF…</Text>
            </View>
          )}
          <WebView
            source={{ uri: pdfUrl }}
            style={[styles.webview, loading && styles.hidden]}
            originWhitelist={['*']}
            onLoad={() => setLoading(false)}
            onError={(e) => {
              console.error('[PdfViewer] render error:', e.nativeEvent);
              setLoading(false);
              setError(true);
            }}
            onHttpError={(e) => {
              console.error('[PdfViewer] HTTP error:', e.nativeEvent.statusCode);
              setLoading(false);
              setError(true);
            }}
          />
        </>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#F0EAFF' },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: withAlpha(colors.primary, 0.1),
    backgroundColor: 'rgba(255,255,255,0.9)',
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
    fontSize: 16,
    fontFamily: fonts.bold,
    color: colors.textPrimary,
    marginHorizontal: 8,
  },
  headerSpacer: { width: 40 },
  webview: { flex: 1, backgroundColor: '#fff' },
  hidden: { opacity: 0, height: 0 },
  loadingWrap: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 12,
  },
  loadingText: {
    fontSize: 14,
    fontFamily: fonts.regular,
    color: colors.textSecondary,
  },
  errorWrap: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 36,
    gap: 12,
  },
  errorTitle: {
    fontSize: 18,
    fontFamily: fonts.bold,
    color: colors.textPrimary,
  },
  errorSub: {
    fontSize: 13,
    fontFamily: fonts.regular,
    color: colors.textSecondary,
    textAlign: 'center',
    lineHeight: 20,
  },
});
