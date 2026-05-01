import React, { useEffect, useRef } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  Animated,
  ActivityIndicator,
  StyleSheet,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { colors, fonts, withAlpha } from '../../theme/colors';

interface Props {
  caregiverName: string;
  patientName: string;
  medicationCount: number;
  mealCount: number;
  activityCount: number;
  familyCount: number;
  emergencyCount: number;
  isSubmitting: boolean;
  submitError?: string;
  onComplete: () => void;
}

interface SummaryTile {
  icon: string;
  label: string;
  count: number;
  color: string;
}

export default function StepReviewComplete({
  caregiverName,
  patientName,
  medicationCount,
  mealCount,
  activityCount,
  familyCount,
  emergencyCount,
  isSubmitting,
  submitError,
  onComplete,
}: Props) {
  const scaleAnim = useRef(new Animated.Value(0)).current;
  const pulseAnim = useRef(new Animated.Value(1)).current;
  const fadeAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.sequence([
      Animated.spring(scaleAnim, {
        toValue: 1,
        tension: 60,
        friction: 8,
        useNativeDriver: true,
      }),
      Animated.timing(fadeAnim, {
        toValue: 1,
        duration: 400,
        useNativeDriver: true,
      }),
    ]).start(() => {
      Animated.loop(
        Animated.sequence([
          Animated.timing(pulseAnim, { toValue: 1.06, duration: 900, useNativeDriver: true }),
          Animated.timing(pulseAnim, { toValue: 1.0, duration: 900, useNativeDriver: true }),
        ]),
      ).start();
    });
  }, []);

  const tiles: SummaryTile[] = [
    { icon: 'pill', label: 'Medications', count: medicationCount, color: colors.primary },
    { icon: 'silverware-fork-knife', label: 'Meals', count: mealCount, color: colors.secondary },
    { icon: 'run-fast', label: 'Activities', count: activityCount, color: '#F59E0B' },
    { icon: 'account-group', label: 'Family', count: familyCount, color: colors.primaryDark },
    { icon: 'phone-alert', label: 'Emergency', count: emergencyCount, color: colors.error },
  ];

  return (
    <View style={styles.container}>
      {/* Check Orb */}
      <Animated.View
        style={[
          styles.orbWrapper,
          { transform: [{ scale: Animated.multiply(scaleAnim, pulseAnim) }] },
        ]}
      >
        <LinearGradient
          colors={[colors.primary, colors.primaryMuted]}
          style={styles.orb}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
        >
          <MaterialCommunityIcons name="check-bold" size={52} color={colors.white} />
        </LinearGradient>
      </Animated.View>

      <Animated.View style={{ opacity: fadeAnim }}>
        <Text style={styles.readyTitle}>CogniCare is Ready!</Text>
        <Text style={styles.readySubtitle}>
          {caregiverName || 'Caregiver'}'s setup is complete.{'\n'}
          {patientName || 'Your patient'}'s profile has been configured.
        </Text>

        {/* Summary Grid */}
        <View style={styles.grid}>
          {tiles.map((tile) => (
            <View key={tile.label} style={styles.tile}>
              <View style={[styles.tileIcon, { backgroundColor: withAlpha(tile.color, 0.12) }]}>
                <MaterialCommunityIcons name={tile.icon as any} size={20} color={tile.color} />
              </View>
              <Text style={styles.tileCount}>{tile.count}</Text>
              <Text style={styles.tileLabel}>{tile.label}</Text>
            </View>
          ))}
        </View>

        {/* Error Banner */}
        {submitError ? (
          <View style={styles.errorBanner}>
            <MaterialCommunityIcons name="alert-circle" size={18} color={colors.error} />
            <Text style={styles.errorText}>{submitError}</Text>
          </View>
        ) : null}

        {/* Submit Button */}
        <TouchableOpacity
          onPress={onComplete}
          disabled={isSubmitting}
          activeOpacity={0.85}
          style={styles.submitWrapper}
        >
          <LinearGradient
            colors={[colors.primary, colors.primaryMuted]}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 0 }}
            style={styles.submitBtn}
          >
            {isSubmitting ? (
              <ActivityIndicator color={colors.white} size="small" />
            ) : (
              <>
                <MaterialCommunityIcons name="rocket-launch" size={20} color={colors.white} />
                <Text style={styles.submitText}>Launch CogniCare</Text>
              </>
            )}
          </LinearGradient>
        </TouchableOpacity>

        <Text style={styles.footer}>
          You can update this information anytime from the settings.
        </Text>
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    paddingTop: 12,
  },
  orbWrapper: {
    marginBottom: 24,
    shadowColor: colors.primary,
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.3,
    shadowRadius: 20,
    elevation: 10,
  },
  orb: {
    width: 110,
    height: 110,
    borderRadius: 55,
    alignItems: 'center',
    justifyContent: 'center',
  },
  readyTitle: {
    fontSize: 26,
    fontFamily: fonts.extraBold,
    color: colors.textPrimary,
    textAlign: 'center',
    marginBottom: 10,
  },
  readySubtitle: {
    fontSize: 14,
    fontFamily: fonts.regular,
    color: colors.textSecondary,
    textAlign: 'center',
    lineHeight: 22,
    marginBottom: 24,
  },
  grid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 12,
    justifyContent: 'center',
    marginBottom: 24,
  },
  tile: {
    width: 90,
    alignItems: 'center',
    backgroundColor: colors.white,
    borderRadius: 14,
    padding: 14,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.07,
    shadowRadius: 6,
    elevation: 2,
  },
  tileIcon: {
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 8,
  },
  tileCount: {
    fontSize: 20,
    fontFamily: fonts.extraBold,
    color: colors.textPrimary,
  },
  tileLabel: {
    fontSize: 11,
    fontFamily: fonts.regular,
    color: colors.textSecondary,
    textAlign: 'center',
    marginTop: 2,
  },
  errorBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: withAlpha(colors.error, 0.08),
    borderWidth: 1,
    borderColor: withAlpha(colors.error, 0.2),
    borderRadius: 12,
    padding: 12,
    marginBottom: 16,
    width: '100%',
  },
  errorText: {
    flex: 1,
    fontSize: 13,
    fontFamily: fonts.regular,
    color: colors.error,
  },
  submitWrapper: {
    width: '100%',
    borderRadius: 18,
    overflow: 'hidden',
    marginBottom: 16,
    shadowColor: colors.primary,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.25,
    shadowRadius: 12,
    elevation: 6,
  },
  submitBtn: {
    height: 60,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
    borderRadius: 18,
  },
  submitText: {
    fontSize: 17,
    fontFamily: fonts.bold,
    color: colors.white,
    letterSpacing: 0.3,
  },
  footer: {
    fontSize: 12,
    fontFamily: fonts.regular,
    color: colors.textMuted,
    textAlign: 'center',
  },
});
