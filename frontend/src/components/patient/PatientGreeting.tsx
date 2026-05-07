import React, { useEffect, useRef } from 'react';
import { View, Text, Animated, StyleSheet } from 'react-native';
import { colors, fonts, withAlpha } from '../../theme/colors';

interface Props {
  greeting: string;
  patientName: string;
  isListening: boolean;
}

function BouncingDots() {
  const dot1 = useRef(new Animated.Value(1)).current;
  const dot2 = useRef(new Animated.Value(1)).current;
  const dot3 = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    const makeLoop = (val: Animated.Value, delay: number) =>
      Animated.loop(
        Animated.sequence([
          Animated.delay(delay),
          Animated.timing(val, { toValue: 1.4, duration: 300, useNativeDriver: true }),
          Animated.timing(val, { toValue: 0.5, duration: 300, useNativeDriver: true }),
          Animated.timing(val, { toValue: 1.0, duration: 300, useNativeDriver: true }),
        ]),
      );

    const a1 = makeLoop(dot1, 0);
    const a2 = makeLoop(dot2, 150);
    const a3 = makeLoop(dot3, 300);
    a1.start();
    a2.start();
    a3.start();
    return () => {
      a1.stop();
      a2.stop();
      a3.stop();
    };
  }, []);

  return (
    <View style={styles.dotsRow}>
      {[dot1, dot2, dot3].map((dot, i) => (
        <Animated.View
          key={i}
          style={[styles.dot, { transform: [{ scale: dot }] }]}
        />
      ))}
    </View>
  );
}

export default function PatientGreeting({ greeting, patientName, isListening }: Props) {
  const fadeAnim = useRef(new Animated.Value(0)).current;
  const slideAnim = useRef(new Animated.Value(16)).current;

  useEffect(() => {
    Animated.parallel([
      Animated.timing(fadeAnim, { toValue: 1, duration: 600, useNativeDriver: true }),
      Animated.timing(slideAnim, { toValue: 0, duration: 600, useNativeDriver: true }),
    ]).start();
  }, []);

  return (
    <Animated.View
      style={[
        styles.container,
        { opacity: fadeAnim, transform: [{ translateY: slideAnim }] },
      ]}
    >
      <Text style={styles.greeting}>{greeting},</Text>
      <Text style={styles.name}>{patientName}</Text>

      {/* Status pill */}
      {isListening ? (
        <View style={styles.listeningPill}>
          <BouncingDots />
          <Text style={styles.listeningText}>Listening</Text>
        </View>
      ) : (
        <View style={styles.idlePill}>
          <View style={styles.greenDot} />
          <Text style={styles.idleText}>I'm here for you</Text>
        </View>
      )}
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    marginBottom: 24,
  },
  greeting: {
    fontSize: 18,
    fontFamily: fonts.regular,
    color: colors.textSecondary,
    marginBottom: 2,
  },
  name: {
    fontSize: 32,
    fontFamily: fonts.extraBold,
    color: colors.textPrimary,
    marginBottom: 12,
  },
  idlePill: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: withAlpha(colors.secondary, 0.15),
    borderRadius: 20,
    paddingHorizontal: 14,
    paddingVertical: 7,
    gap: 7,
  },
  greenDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.secondaryDark,
  },
  idleText: {
    fontSize: 13,
    fontFamily: fonts.semiBold,
    color: colors.secondaryDark,
  },
  listeningPill: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: withAlpha(colors.primary, 0.15),
    borderRadius: 20,
    paddingHorizontal: 14,
    paddingVertical: 7,
    gap: 8,
  },
  dotsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
  },
  dot: {
    width: 7,
    height: 7,
    borderRadius: 3.5,
    backgroundColor: colors.primary,
  },
  listeningText: {
    fontSize: 13,
    fontFamily: fonts.semiBold,
    color: colors.primary,
  },
});
