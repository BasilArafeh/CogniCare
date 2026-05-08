import React, { useEffect, useRef } from 'react';
import {
  View,
  Text,
  Animated,
  StyleSheet,
  useWindowDimensions,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { colors, fonts, withAlpha } from '../../theme/colors';

interface WizardProgressProps {
  currentStep: number;
  totalSteps: number;
  stepTitles: string[];
  stepIcons: string[];
}

export default function WizardProgress({
  currentStep,
  totalSteps,
  stepTitles,
  stepIcons,
}: WizardProgressProps) {
  const { width } = useWindowDimensions();
  const barWidth = width - 48; // 24px padding each side
  const targetWidth = ((currentStep + 1) / totalSteps) * barWidth;

  const animatedWidth = useRef(new Animated.Value(targetWidth)).current;

  useEffect(() => {
    Animated.timing(animatedWidth, {
      toValue: targetWidth,
      duration: 400,
      useNativeDriver: false,
    }).start();
  }, [currentStep]);

  return (
    <View style={styles.container}>
      {/* Icon + Step info */}
      <View style={styles.row}>
        <LinearGradient
          colors={[colors.primary, colors.primaryMuted]}
          style={styles.stepIcon}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
        >
          <MaterialCommunityIcons
            name={stepIcons[currentStep] as any}
            size={20}
            color={colors.white}
          />
        </LinearGradient>
        <View style={styles.stepInfo}>
          <Text style={styles.stepTitle}>{stepTitles[currentStep]}</Text>
          <Text style={styles.stepCount}>
            Step {currentStep + 1} of {totalSteps}
          </Text>
        </View>
        <View style={styles.percentBadge}>
          <Text style={styles.percentText}>
            {Math.round(((currentStep + 1) / totalSteps) * 100)}%
          </Text>
        </View>
      </View>

      {/* Progress bar */}
      <View style={[styles.barTrack, { width: barWidth }]}>
        <Animated.View style={{ width: animatedWidth, borderRadius: 4, overflow: 'hidden', height: 8 }}>
          <LinearGradient
            colors={[colors.primary, colors.primaryMuted]}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 0 }}
            style={StyleSheet.absoluteFill}
          />
        </Animated.View>
      </View>

      {/* Step dots */}
      <View style={styles.dotsRow}>
        {Array.from({ length: totalSteps }).map((_, i) => {
          const isDone = i < currentStep;
          const isCurrent = i === currentStep;
          return (
            <View
              key={i}
              style={[
                styles.dot,
                isDone && styles.dotDone,
                isCurrent && styles.dotCurrent,
                !isDone && !isCurrent && styles.dotFuture,
              ]}
            />
          );
        })}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    paddingHorizontal: 24,
    paddingVertical: 12,
    backgroundColor: withAlpha(colors.white, 0.6),
    borderBottomWidth: 1,
    borderBottomColor: withAlpha(colors.primaryMuted, 0.2),
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 12,
  },
  stepIcon: {
    width: 40,
    height: 40,
    borderRadius: 20,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  stepInfo: {
    flex: 1,
  },
  stepTitle: {
    fontSize: 15,
    fontFamily: fonts.bold,
    color: colors.textPrimary,
  },
  stepCount: {
    fontSize: 12,
    fontFamily: fonts.regular,
    color: colors.textSecondary,
    marginTop: 2,
  },
  percentBadge: {
    backgroundColor: colors.primaryLight,
    borderRadius: 10,
    paddingHorizontal: 10,
    paddingVertical: 4,
  },
  percentText: {
    fontSize: 12,
    fontFamily: fonts.bold,
    color: colors.primary,
  },
  barTrack: {
    height: 8,
    backgroundColor: colors.primaryLight,
    borderRadius: 4,
    overflow: 'hidden',
    marginBottom: 12,
  },
  dotsRow: {
    flexDirection: 'row',
    gap: 6,
    justifyContent: 'center',
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  dotDone: {
    backgroundColor: colors.primary,
  },
  dotCurrent: {
    backgroundColor: colors.primaryMuted,
    width: 20,
    borderRadius: 4,
  },
  dotFuture: {
    backgroundColor: colors.primaryLight,
  },
});
