import React, { useState, useRef, useEffect } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  Animated,
  StyleSheet,
  TextInput,
  KeyboardAvoidingView,
  Platform,
  ActivityIndicator,
  ScrollView,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { useNavigation } from '@react-navigation/native';
import type { StackNavigationProp } from '@react-navigation/stack';
import { colors, fonts, withAlpha } from '../theme/colors';
import type { RootStackParamList } from '../navigation/AppNavigator';
import apiService from '../services/apiService';

type PatientLoginNavProp = StackNavigationProp<RootStackParamList, 'PatientLogin'>;

export default function PatientLoginScreen() {
  const navigation = useNavigation<PatientLoginNavProp>();
  const insets = useSafeAreaInsets();

  const [username, setUsername] = useState('');
  const [pin, setPin] = useState('');
  const [showPin, setShowPin] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const heroAnim = useRef(new Animated.Value(0)).current;
  const cardAnim = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    Animated.sequence([
      Animated.timing(heroAnim, { toValue: 1, duration: 600, useNativeDriver: true }),
      Animated.timing(cardAnim, { toValue: 1, duration: 450, useNativeDriver: true }),
    ]).start();
  }, []);

  const heroTranslateY = heroAnim.interpolate({ inputRange: [0, 1], outputRange: [30, 0] });
  const cardTranslateY = cardAnim.interpolate({ inputRange: [0, 1], outputRange: [32, 0] });

  const handleLogin = async () => {
    if (!username.trim()) {
      setError('Please enter your username.');
      return;
    }
    if (pin.length !== 4) {
      setError('Please enter your 4-digit PIN.');
      return;
    }
    setError('');
    setLoading(true);
    try {
      const result = await apiService.signInPatient(username.trim(), pin);
      if (!result) {
        setError('Incorrect username or PIN. Please try again.');
        return;
      }
      navigation.replace('PatientHome', {
        patientId: result.patientId,
        patientName: result.patientName,
      });
    } catch {
      setError('Something went wrong. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <LinearGradient
      colors={['#2E1760', '#4A2D9A', '#7C5CBF']}
      locations={[0, 0.5, 1]}
      style={[styles.container, { paddingTop: insets.top }]}
    >
      <View style={styles.blob1} />
      <View style={styles.blob2} />
      <View style={styles.blob3} />

      <TouchableOpacity
        onPress={() => navigation.goBack()}
        style={[styles.backBtn, { top: insets.top + 14 }]}
        activeOpacity={0.7}
      >
        <View style={styles.backBtnInner}>
          <MaterialCommunityIcons name="arrow-left" size={20} color="rgba(255,255,255,0.9)" />
        </View>
      </TouchableOpacity>

      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={{ flex: 1 }}
      >
        <ScrollView
          contentContainerStyle={[styles.scroll, { paddingBottom: insets.bottom + 32 }]}
          showsVerticalScrollIndicator={false}
          keyboardShouldPersistTaps="handled"
          bounces={false}
        >
          <Animated.View
            style={[
              styles.hero,
              { opacity: heroAnim, transform: [{ translateY: heroTranslateY }] },
            ]}
          >
            <View style={styles.logoRing}>
              <LinearGradient
                colors={['rgba(255,255,255,0.28)', 'rgba(255,255,255,0.07)']}
                style={styles.logoRingGradient}
              >
                <View style={styles.logoCircle}>
                  <MaterialCommunityIcons name="account-heart" size={42} color={colors.primary} />
                </View>
              </LinearGradient>
            </View>
            <Text style={styles.appName}>CogniCare</Text>
            <Text style={styles.heroSub}>Patient login</Text>
          </Animated.View>

          <Animated.View
            style={[
              styles.card,
              { opacity: cardAnim, transform: [{ translateY: cardTranslateY }] },
            ]}
          >
            <View style={styles.cardHeader}>
              <View style={styles.cardIconWrap}>
                <MaterialCommunityIcons name="account-circle" size={28} color={colors.primary} />
              </View>
              <View>
                <Text style={styles.cardTitle}>Patient Sign In</Text>
                <Text style={styles.cardSubtitle}>Use the credentials your caregiver set up</Text>
              </View>
            </View>

            <View style={styles.dividerLine} />

            <View style={styles.fieldGroup}>
              <Text style={styles.fieldLabel}>Username</Text>
              <View style={[styles.inputWrap, username.length > 0 && styles.inputWrapActive]}>
                <MaterialCommunityIcons
                  name="at"
                  size={19}
                  color={username.length > 0 ? colors.primary : colors.textMuted}
                  style={styles.inputIcon}
                />
                <TextInput
                  style={styles.input}
                  placeholder="Enter username"
                  placeholderTextColor={colors.textMuted}
                  value={username}
                  onChangeText={(v) => { setUsername(v); setError(''); }}
                  autoCapitalize="none"
                  autoCorrect={false}
                  returnKeyType="next"
                />
              </View>
            </View>

            <View style={styles.fieldGroup}>
              <Text style={styles.fieldLabel}>4-Digit PIN</Text>
              <View style={[styles.inputWrap, pin.length > 0 && styles.inputWrapActive]}>
                <MaterialCommunityIcons
                  name="lock-outline"
                  size={19}
                  color={pin.length > 0 ? colors.primary : colors.textMuted}
                  style={styles.inputIcon}
                />
                <TextInput
                  style={[styles.input, { flex: 1 }]}
                  placeholder="Enter 4-digit PIN"
                  placeholderTextColor={colors.textMuted}
                  value={pin}
                  onChangeText={(v) => { setPin(v.replace(/\D/g, '').slice(0, 4)); setError(''); }}
                  keyboardType="numeric"
                  secureTextEntry={!showPin}
                  returnKeyType="done"
                  onSubmitEditing={handleLogin}
                />
                <TouchableOpacity
                  onPress={() => setShowPin((p) => !p)}
                  style={styles.eyeBtn}
                  activeOpacity={0.6}
                >
                  <MaterialCommunityIcons
                    name={showPin ? 'eye-off-outline' : 'eye-outline'}
                    size={19}
                    color={colors.textMuted}
                  />
                </TouchableOpacity>
              </View>
            </View>

            {!!error && (
              <View style={styles.errorRow}>
                <MaterialCommunityIcons name="alert-circle-outline" size={15} color={colors.error} />
                <Text style={styles.errorText}>{error}</Text>
              </View>
            )}

            <TouchableOpacity
              onPress={handleLogin}
              activeOpacity={0.87}
              style={styles.primaryWrapper}
              disabled={loading}
            >
              <LinearGradient
                colors={loading ? ['#A088CC', '#A088CC'] : ['#6B43B5', '#9B7EDB']}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 0 }}
                style={styles.primaryBtn}
              >
                {loading ? (
                  <ActivityIndicator color={colors.white} size="small" />
                ) : (
                  <>
                    <MaterialCommunityIcons name="login" size={20} color={colors.white} />
                    <Text style={styles.primaryBtnText}>Sign In</Text>
                  </>
                )}
              </LinearGradient>
            </TouchableOpacity>
          </Animated.View>

          <Animated.View style={[styles.footerRow, { opacity: cardAnim }]}>
            <MaterialCommunityIcons name="shield-check-outline" size={12} color="rgba(255,255,255,0.35)" />
            <Text style={styles.footerText}>  Your data is secure and private</Text>
          </Animated.View>
        </ScrollView>
      </KeyboardAvoidingView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1 },
  blob1: {
    position: 'absolute', width: 280, height: 280, borderRadius: 140,
    backgroundColor: 'rgba(255,255,255,0.05)', top: -90, right: -70,
  },
  blob2: {
    position: 'absolute', width: 180, height: 180, borderRadius: 90,
    backgroundColor: 'rgba(255,255,255,0.04)', top: 180, left: -70,
  },
  blob3: {
    position: 'absolute', width: 140, height: 140, borderRadius: 70,
    backgroundColor: 'rgba(255,255,255,0.03)', bottom: 260, right: -30,
  },
  backBtn: { position: 'absolute', left: 18, zIndex: 10 },
  backBtnInner: {
    width: 40, height: 40, borderRadius: 20,
    backgroundColor: 'rgba(255,255,255,0.15)',
    borderWidth: 1, borderColor: 'rgba(255,255,255,0.2)',
    alignItems: 'center', justifyContent: 'center',
  },
  scroll: { flexGrow: 1, paddingHorizontal: 22, alignItems: 'center', paddingTop: 72 },
  hero: { alignItems: 'center', marginBottom: 28 },
  logoRing: { marginBottom: 14 },
  logoRingGradient: {
    width: 96, height: 96, borderRadius: 48,
    alignItems: 'center', justifyContent: 'center',
    borderWidth: 1.5, borderColor: 'rgba(255,255,255,0.18)',
  },
  logoCircle: {
    width: 72, height: 72, borderRadius: 36,
    backgroundColor: colors.white, alignItems: 'center', justifyContent: 'center',
    shadowColor: '#000', shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.3, shadowRadius: 14, elevation: 10,
  },
  appName: {
    fontSize: 32, fontFamily: fonts.extraBold,
    color: colors.white, letterSpacing: 0.5, marginBottom: 4,
  },
  heroSub: {
    fontSize: 14, fontFamily: fonts.semiBold,
    color: 'rgba(255,255,255,0.65)', letterSpacing: 0.2,
  },
  card: {
    width: '100%', backgroundColor: colors.white, borderRadius: 28,
    padding: 24, shadowColor: '#000', shadowOffset: { width: 0, height: 14 },
    shadowOpacity: 0.22, shadowRadius: 26, elevation: 14, marginBottom: 22,
  },
  cardHeader: { flexDirection: 'row', alignItems: 'center', gap: 12, marginBottom: 18 },
  cardIconWrap: {
    width: 48, height: 48, borderRadius: 14,
    backgroundColor: withAlpha(colors.primary, 0.1),
    alignItems: 'center', justifyContent: 'center',
  },
  cardTitle: {
    fontSize: 20, fontFamily: fonts.extraBold,
    color: colors.textPrimary, marginBottom: 2,
  },
  cardSubtitle: { fontSize: 12, fontFamily: fonts.regular, color: colors.textSecondary },
  dividerLine: {
    height: 1, backgroundColor: withAlpha(colors.textMuted, 0.2), marginBottom: 22,
  },
  fieldGroup: { marginBottom: 16 },
  fieldLabel: {
    fontSize: 13, fontFamily: fonts.semiBold,
    color: colors.textSecondary, marginBottom: 8, marginLeft: 2,
  },
  inputWrap: {
    flexDirection: 'row', alignItems: 'center',
    borderWidth: 1.5, borderColor: withAlpha(colors.textMuted, 0.35),
    borderRadius: 14, backgroundColor: colors.background,
    paddingHorizontal: 14, height: 52,
  },
  inputWrapActive: {
    borderColor: withAlpha(colors.primary, 0.6),
    backgroundColor: withAlpha(colors.primary, 0.03),
  },
  inputIcon: { marginRight: 10 },
  input: { flex: 1, fontSize: 15, fontFamily: fonts.regular, color: colors.textPrimary },
  eyeBtn: { padding: 4, marginLeft: 6 },
  errorRow: {
    flexDirection: 'row', alignItems: 'center', gap: 6,
    backgroundColor: withAlpha(colors.error, 0.08),
    borderRadius: 10, paddingHorizontal: 12, paddingVertical: 9,
    marginBottom: 14, borderWidth: 1, borderColor: withAlpha(colors.error, 0.2),
  },
  errorText: { fontSize: 13, fontFamily: fonts.regular, color: colors.error, flex: 1 },
  primaryWrapper: {
    borderRadius: 16, overflow: 'hidden',
    shadowColor: colors.primary, shadowOffset: { width: 0, height: 5 },
    shadowOpacity: 0.35, shadowRadius: 12, elevation: 7,
    marginTop: 4, marginBottom: 4,
  },
  primaryBtn: {
    height: 56, flexDirection: 'row', alignItems: 'center',
    justifyContent: 'center', gap: 10, borderRadius: 16,
  },
  primaryBtnText: {
    fontSize: 16, fontFamily: fonts.bold, color: colors.white, letterSpacing: 0.2,
  },
  footerRow: { flexDirection: 'row', alignItems: 'center' },
  footerText: { fontSize: 12, fontFamily: fonts.regular, color: 'rgba(255,255,255,0.4)' },
});
