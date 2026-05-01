import React, { useEffect, useRef } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  Animated,
  StyleSheet,
  ScrollView,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useNavigation } from '@react-navigation/native';
import type { StackNavigationProp } from '@react-navigation/stack';
import { colors, fonts, withAlpha } from '../theme/colors';
import type { RootStackParamList } from '../navigation/AppNavigator';

type WelcomeNavProp = StackNavigationProp<RootStackParamList, 'Welcome'>;

const FEATURES = [
  { icon: 'pill', label: 'Medications' },
  { icon: 'silverware-fork-knife', label: 'Meal Plans' },
  { icon: 'run-fast', label: 'Activities' },
  { icon: 'account-group', label: 'Family' },
  { icon: 'phone-alert', label: 'Emergency' },
  { icon: 'brain', label: 'Cognitive Care' },
];

export default function WelcomeScreen() {
  const navigation = useNavigation<WelcomeNavProp>();
  const insets = useSafeAreaInsets();

  const heroAnim = useRef(new Animated.Value(0)).current;
  const featuresAnim = useRef(new Animated.Value(0)).current;
  const cardAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.sequence([
      Animated.timing(heroAnim, { toValue: 1, duration: 700, useNativeDriver: true }),
      Animated.timing(featuresAnim, { toValue: 1, duration: 500, useNativeDriver: true }),
      Animated.timing(cardAnim, { toValue: 1, duration: 400, useNativeDriver: true }),
    ]).start();
  }, []);

  const heroTranslateY = heroAnim.interpolate({ inputRange: [0, 1], outputRange: [50, 0] });
  const featuresTranslateY = featuresAnim.interpolate({ inputRange: [0, 1], outputRange: [30, 0] });
  const cardTranslateY = cardAnim.interpolate({ inputRange: [0, 1], outputRange: [24, 0] });

  return (
    <LinearGradient
      colors={['#2E1760', '#4A2D9A', '#7C5CBF']}
      locations={[0, 0.5, 1]}
      style={[styles.container, { paddingTop: insets.top }]}
    >
      {/* Decorative blobs */}
      <View style={styles.blob1} />
      <View style={styles.blob2} />
      <View style={styles.blob3} />

      <ScrollView
        contentContainerStyle={[styles.scroll, { paddingBottom: insets.bottom + 28 }]}
        showsVerticalScrollIndicator={false}
        bounces={false}
      >
        {/* Hero */}
        <Animated.View
          style={[
            styles.hero,
            { opacity: heroAnim, transform: [{ translateY: heroTranslateY }] },
          ]}
        >
          <View style={styles.logoRing}>
            <LinearGradient
              colors={['rgba(255,255,255,0.3)', 'rgba(255,255,255,0.08)']}
              style={styles.logoRingGradient}
            >
              <View style={styles.logoCircle}>
                <MaterialCommunityIcons name="heart-pulse" size={46} color={colors.primary} />
              </View>
            </LinearGradient>
          </View>

          <Text style={styles.appName}>CogniCare</Text>
          <Text style={styles.tagline}>Alzheimer's Care, Simplified</Text>
          <Text style={styles.description}>
            Empowering caregivers with intelligent tools{'\n'}for compassionate daily care management.
          </Text>
        </Animated.View>

        {/* Feature chips */}
        <Animated.View
          style={[
            styles.featuresWrap,
            { opacity: featuresAnim, transform: [{ translateY: featuresTranslateY }] },
          ]}
        >
          {FEATURES.map((f) => (
            <View key={f.label} style={styles.chip}>
              <MaterialCommunityIcons name={f.icon as any} size={14} color="rgba(255,255,255,0.9)" />
              <Text style={styles.chipLabel}>{f.label}</Text>
            </View>
          ))}
        </Animated.View>

        {/* Action card */}
        <Animated.View
          style={[
            styles.card,
            { opacity: cardAnim, transform: [{ translateY: cardTranslateY }] },
          ]}
        >
          <Text style={styles.cardTitle}>Get Started</Text>
          <Text style={styles.cardSubtitle}>Choose how you'd like to continue</Text>

          {/* Sign Up as Caregiver */}
          <TouchableOpacity
            onPress={() => navigation.navigate('CaregiverOnboarding')}
            activeOpacity={0.87}
            style={styles.primaryWrapper}
          >
            <LinearGradient
              colors={['#6B43B5', '#9B7EDB']}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 0 }}
              style={styles.primaryBtn}
            >
              <MaterialCommunityIcons name="account-plus" size={20} color={colors.white} />
              <Text style={styles.primaryBtnText}>Sign Up as Caregiver</Text>
            </LinearGradient>
          </TouchableOpacity>

          <View style={styles.divider}>
            <View style={styles.dividerLine} />
            <Text style={styles.dividerText}>or</Text>
            <View style={styles.dividerLine} />
          </View>

          {/* Sign In */}
          <TouchableOpacity
            onPress={() => {}}
            activeOpacity={0.87}
            style={[styles.outlineBtn, { marginBottom: 12 }]}
          >
            <MaterialCommunityIcons name="login" size={20} color={colors.primary} />
            <Text style={styles.outlineBtnText}>Sign In</Text>
          </TouchableOpacity>

          {/* Patient Login */}
          <TouchableOpacity
            onPress={() => navigation.navigate('PatientHome')}
            activeOpacity={0.87}
            style={styles.ghostBtn}
          >
            <MaterialCommunityIcons name="account-circle" size={18} color={colors.textSecondary} />
            <Text style={styles.ghostBtnText}>Login as Patient</Text>
          </TouchableOpacity>
        </Animated.View>

        {/* Footer */}
        <Animated.View style={[styles.footerRow, { opacity: cardAnim }]}>
          <MaterialCommunityIcons name="heart" size={12} color="rgba(255,255,255,0.4)" />
          <Text style={styles.footerText}>  Designed with care for every family</Text>
        </Animated.View>
      </ScrollView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  blob1: {
    position: 'absolute',
    width: 300,
    height: 300,
    borderRadius: 150,
    backgroundColor: 'rgba(255,255,255,0.05)',
    top: -100,
    right: -80,
  },
  blob2: {
    position: 'absolute',
    width: 200,
    height: 200,
    borderRadius: 100,
    backgroundColor: 'rgba(255,255,255,0.04)',
    top: 160,
    left: -80,
  },
  blob3: {
    position: 'absolute',
    width: 160,
    height: 160,
    borderRadius: 80,
    backgroundColor: 'rgba(255,255,255,0.03)',
    bottom: 300,
    right: -40,
  },
  scroll: {
    flexGrow: 1,
    paddingHorizontal: 22,
    alignItems: 'center',
  },
  hero: {
    alignItems: 'center',
    paddingTop: 36,
    marginBottom: 24,
  },
  logoRing: {
    marginBottom: 18,
  },
  logoRingGradient: {
    width: 108,
    height: 108,
    borderRadius: 54,
    alignItems: 'center',
    justifyContent: 'center',
    borderWidth: 1.5,
    borderColor: 'rgba(255,255,255,0.18)',
  },
  logoCircle: {
    width: 82,
    height: 82,
    borderRadius: 41,
    backgroundColor: colors.white,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.35,
    shadowRadius: 16,
    elevation: 12,
  },
  appName: {
    fontSize: 38,
    fontFamily: fonts.extraBold,
    color: colors.white,
    letterSpacing: 0.6,
    marginBottom: 6,
  },
  tagline: {
    fontSize: 15,
    fontFamily: fonts.semiBold,
    color: 'rgba(255,255,255,0.8)',
    marginBottom: 12,
    letterSpacing: 0.2,
  },
  description: {
    fontSize: 13,
    fontFamily: fonts.regular,
    color: 'rgba(255,255,255,0.6)',
    textAlign: 'center',
    lineHeight: 20,
  },
  featuresWrap: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    justifyContent: 'center',
    gap: 8,
    marginBottom: 24,
  },
  chip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    paddingHorizontal: 12,
    paddingVertical: 7,
    borderRadius: 20,
    backgroundColor: 'rgba(255,255,255,0.12)',
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.18)',
  },
  chipLabel: {
    fontSize: 12,
    fontFamily: fonts.semiBold,
    color: 'rgba(255,255,255,0.9)',
  },
  card: {
    width: '100%',
    backgroundColor: colors.white,
    borderRadius: 28,
    padding: 24,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 12 },
    shadowOpacity: 0.25,
    shadowRadius: 24,
    elevation: 14,
    marginBottom: 20,
  },
  cardTitle: {
    fontSize: 22,
    fontFamily: fonts.extraBold,
    color: colors.textPrimary,
    marginBottom: 4,
  },
  cardSubtitle: {
    fontSize: 13,
    fontFamily: fonts.regular,
    color: colors.textSecondary,
    marginBottom: 22,
  },
  primaryWrapper: {
    borderRadius: 16,
    overflow: 'hidden',
    shadowColor: colors.primary,
    shadowOffset: { width: 0, height: 5 },
    shadowOpacity: 0.35,
    shadowRadius: 12,
    elevation: 7,
  },
  primaryBtn: {
    height: 58,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 10,
    borderRadius: 16,
  },
  primaryBtnText: {
    fontSize: 16,
    fontFamily: fonts.bold,
    color: colors.white,
    letterSpacing: 0.2,
  },
  divider: {
    flexDirection: 'row',
    alignItems: 'center',
    marginVertical: 16,
    gap: 12,
  },
  dividerLine: {
    flex: 1,
    height: 1,
    backgroundColor: withAlpha(colors.textMuted, 0.25),
  },
  dividerText: {
    fontSize: 12,
    fontFamily: fonts.regular,
    color: colors.textMuted,
  },
  outlineBtn: {
    height: 54,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    borderRadius: 16,
    borderWidth: 1.5,
    borderColor: colors.primary,
    backgroundColor: withAlpha(colors.primary, 0.05),
  },
  outlineBtnText: {
    fontSize: 15,
    fontFamily: fonts.bold,
    color: colors.primary,
  },
  ghostBtn: {
    height: 46,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 8,
    borderRadius: 14,
    backgroundColor: withAlpha(colors.textMuted, 0.1),
  },
  ghostBtnText: {
    fontSize: 14,
    fontFamily: fonts.semiBold,
    color: colors.textSecondary,
  },
  footerRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  footerText: {
    fontSize: 12,
    fontFamily: fonts.regular,
    color: 'rgba(255,255,255,0.45)',
  },
});
