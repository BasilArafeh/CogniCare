import React, { useEffect, useRef } from 'react';
import {
  View,
  TouchableOpacity,
  Animated,
  ActivityIndicator,
  StyleSheet,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { colors, withAlpha } from '../../theme/colors';

interface Props {
  isListening: boolean;
  isProcessing: boolean;
  onTap: () => void;
  size?: number;
}

export default function VoiceOrb({
  isListening,
  isProcessing,
  onTap,
  size = 190,
}: Props) {
  const pulse1 = useRef(new Animated.Value(1)).current;
  const pulse2 = useRef(new Animated.Value(1)).current;
  const innerPulse = useRef(new Animated.Value(1)).current;
  const ripple = useRef(new Animated.Value(1)).current;
  const rippleOpacity = useRef(new Animated.Value(0)).current;
  const rotateAnim = useRef(new Animated.Value(0)).current;

  // Pulse loops
  useEffect(() => {
    const p1 = Animated.loop(
      Animated.sequence([
        Animated.timing(pulse1, { toValue: 1.08, duration: 2000, useNativeDriver: true }),
        Animated.timing(pulse1, { toValue: 1.0, duration: 2000, useNativeDriver: true }),
      ]),
    );
    const p2 = Animated.loop(
      Animated.sequence([
        Animated.delay(400),
        Animated.timing(pulse2, { toValue: 1.14, duration: 2000, useNativeDriver: true }),
        Animated.timing(pulse2, { toValue: 1.0, duration: 2000, useNativeDriver: true }),
      ]),
    );
    const ip = Animated.loop(
      Animated.sequence([
        Animated.timing(innerPulse, { toValue: 1.05, duration: 1600, useNativeDriver: true }),
        Animated.timing(innerPulse, { toValue: 0.95, duration: 1600, useNativeDriver: true }),
      ]),
    );
    const rot = Animated.loop(
      Animated.timing(rotateAnim, {
        toValue: 1,
        duration: 8000,
        useNativeDriver: true,
      }),
    );
    p1.start();
    p2.start();
    ip.start();
    rot.start();
    return () => { p1.stop(); p2.stop(); ip.stop(); rot.stop(); };
  }, []);

  // Ripple when listening
  useEffect(() => {
    if (!isListening) {
      ripple.setValue(1);
      rippleOpacity.setValue(0);
      return;
    }
    rippleOpacity.setValue(0.6);
    const rippleLoop = Animated.loop(
      Animated.sequence([
        Animated.timing(ripple, { toValue: 1.6, duration: 900, useNativeDriver: true }),
        Animated.timing(ripple, { toValue: 1.0, duration: 0, useNativeDriver: true }),
      ]),
    );
    rippleLoop.start();
    return () => rippleLoop.stop();
  }, [isListening]);

  const rotate = rotateAnim.interpolate({
    inputRange: [0, 1],
    outputRange: ['0deg', '360deg'],
  });

  const outerGlowSize = size * 1.36;
  const outerRingSize = size * 1.08;
  const mainOrbSize = size;
  const innerFrostSize = size * 0.68;
  const iconSize = size * 0.22;

  return (
    <TouchableOpacity
      onPress={onTap}
      activeOpacity={0.9}
      style={[styles.touchable, { width: outerGlowSize, height: outerGlowSize }]}
    >
      {/* Ambient glow */}
      <Animated.View
        style={[
          styles.centered,
          {
            width: outerGlowSize,
            height: outerGlowSize,
            borderRadius: outerGlowSize / 2,
            backgroundColor: withAlpha(colors.primary, 0.07),
            transform: [{ scale: pulse2 }],
          },
        ]}
      />

      {/* Ripple ring when listening */}
      {isListening && (
        <Animated.View
          style={[
            styles.centered,
            styles.ring,
            {
              width: mainOrbSize * 1.2,
              height: mainOrbSize * 1.2,
              borderRadius: (mainOrbSize * 1.2) / 2,
              borderColor: withAlpha(colors.primary, 0.35),
              transform: [{ scale: ripple }],
              opacity: rippleOpacity,
            },
          ]}
        />
      )}

      {/* Outer ring */}
      <Animated.View
        style={[
          styles.centered,
          styles.ring,
          {
            width: outerRingSize,
            height: outerRingSize,
            borderRadius: outerRingSize / 2,
            borderColor: withAlpha(colors.primaryMuted, 0.3),
            transform: [{ scale: pulse1 }],
          },
        ]}
      />

      {/* Main orb with gradient + rotation */}
      <Animated.View
        style={[
          styles.centered,
          {
            width: mainOrbSize,
            height: mainOrbSize,
            borderRadius: mainOrbSize / 2,
            transform: [{ rotate }, { scale: innerPulse }],
            overflow: 'hidden',
          },
        ]}
      >
        <LinearGradient
          colors={
            isListening
              ? [colors.primary, '#9B7EDB', colors.primaryMuted]
              : ['#FFFFFF', colors.primaryLight, withAlpha(colors.primary, 0.25)]
          }
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
          style={[StyleSheet.absoluteFill, { borderRadius: mainOrbSize / 2 }]}
        />
      </Animated.View>

      {/* Inner frosted circle */}
      <View
        style={[
          styles.centered,
          {
            width: innerFrostSize,
            height: innerFrostSize,
            borderRadius: innerFrostSize / 2,
            backgroundColor: isListening
              ? withAlpha(colors.primary, 0.2)
              : withAlpha(colors.white, 0.85),
            shadowColor: colors.primary,
            shadowOffset: { width: 0, height: 4 },
            shadowOpacity: 0.18,
            shadowRadius: 12,
            elevation: 6,
          },
        ]}
      >
        {isProcessing ? (
          <ActivityIndicator color={colors.primary} size="large" />
        ) : isListening ? (
          <MaterialCommunityIcons
            name="stop-circle-outline"
            size={iconSize}
            color={colors.white}
          />
        ) : (
          <MaterialCommunityIcons
            name="microphone"
            size={iconSize}
            color={colors.primary}
          />
        )}
      </View>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  touchable: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  centered: {
    position: 'absolute',
    alignSelf: 'center',
    alignItems: 'center',
    justifyContent: 'center',
  },
  ring: {
    borderWidth: 1.5,
    backgroundColor: 'transparent',
  },
});
