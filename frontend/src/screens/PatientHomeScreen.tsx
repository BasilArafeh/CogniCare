import React, { useState, useRef } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  Animated,
  ScrollView,
  StyleSheet,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Audio } from 'expo-av';
import { colors, fonts, withAlpha } from '../theme/colors';
import apiService from '../services/apiService';
import VoiceOrb from '../components/patient/VoiceOrb';
import PatientGreeting from '../components/patient/PatientGreeting';
import DailySummary from '../components/patient/DailySummary';
import ChatBottomBar from '../components/patient/ChatBottomBar';
import PatientChatSheet from '../components/patient/PatientChatSheet';

const PATIENT_ID = 'patient_1';
const PATIENT_NAME = 'Eleanor';

function getGreeting(): string {
  const h = new Date().getHours();
  if (h < 12) return 'Good morning';
  if (h < 17) return 'Good afternoon';
  return 'Good evening';
}

export default function PatientHomeScreen() {
  const insets = useSafeAreaInsets();

  const [isListening, setIsListening] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [voiceError, setVoiceError] = useState('');
  const [showDailySummary, setShowDailySummary] = useState(false);
  const [showChat, setShowChat] = useState(false);

  const recordingRef = useRef<Audio.Recording | null>(null);
  const summaryAnim = useRef(new Animated.Value(0)).current;

  const greeting = getGreeting();

  // ─── Toggle summary ─────────────────────────────────────────────────────────
  const toggleSummary = () => {
    if (showDailySummary) {
      Animated.timing(summaryAnim, {
        toValue: 0,
        duration: 300,
        useNativeDriver: true,
      }).start(() => setShowDailySummary(false));
    } else {
      setShowDailySummary(true);
      Animated.timing(summaryAnim, {
        toValue: 1,
        duration: 300,
        useNativeDriver: true,
      }).start();
    }
  };

  // ─── Voice flow ──────────────────────────────────────────────────────────────
  const startRecording = async () => {
    try {
      setVoiceError('');
      const { status } = await Audio.requestPermissionsAsync();
      if (status !== 'granted') {
        setVoiceError('Microphone permission denied.');
        return;
      }
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
      });
      const { recording } = await Audio.Recording.createAsync(
        Audio.RecordingOptionsPresets.HIGH_QUALITY,
      );
      recordingRef.current = recording;
      setIsListening(true);
    } catch (err) {
      setVoiceError('Could not start recording. Please try again.');
      console.warn('startRecording error:', err);
    }
  };

  const stopAndSend = async () => {
    if (!recordingRef.current) return;
    setIsListening(false);
    setIsProcessing(true);

    try {
      await recordingRef.current.stopAndUnloadAsync();
      const uri = recordingRef.current.getURI();
      recordingRef.current = null;

      if (!uri) {
        setIsProcessing(false);
        return;
      }

      const responseUri = await apiService.postVoice(PATIENT_ID, uri);

      // Play response audio
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: false,
        playsInSilentModeIOS: true,
      });
      const { sound } = await Audio.Sound.createAsync({ uri: responseUri });
      await sound.playAsync();
      sound.setOnPlaybackStatusUpdate((status) => {
        if (status.isLoaded && status.didJustFinish) {
          sound.unloadAsync();
        }
      });
    } catch (err) {
      setVoiceError('Voice message failed. Please try again.');
      console.warn('stopAndSend error:', err);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleOrbTap = () => {
    if (isProcessing) return;
    if (isListening) {
      stopAndSend();
    } else {
      startRecording();
    }
  };

  const orbLabel = isProcessing
    ? 'Processing...'
    : isListening
    ? 'Tap to stop'
    : 'Tap to speak';

  return (
    <LinearGradient
      colors={['#F5F0FF', '#FFFFFF', '#EDE8F8']}
      style={[styles.container, { paddingTop: insets.top }]}
    >
      {/* ── Top Bar ── */}
      <View style={styles.topBar}>
        {/* CogniCare pill */}
        <LinearGradient
          colors={[colors.primary, colors.primaryMuted]}
          style={styles.logoPill}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
        >
          <MaterialCommunityIcons name="brain" size={16} color={colors.white} />
        </LinearGradient>
        <Text style={styles.logoText}>CogniCare</Text>

        <View style={{ flex: 1 }} />

        {/* Settings button */}
        <TouchableOpacity style={styles.settingsBtn}>
          <MaterialCommunityIcons name="cog-outline" size={20} color={colors.textSecondary} />
        </TouchableOpacity>
      </View>

      {/* ── Main content ── */}
      <ScrollView
        style={{ flex: 1 }}
        contentContainerStyle={styles.scrollContent}
        showsVerticalScrollIndicator={false}
      >
        {/* Greeting */}
        <PatientGreeting
          greeting={greeting}
          patientName={PATIENT_NAME}
          isListening={isListening}
        />

        {/* Voice Orb */}
        <View style={styles.orbContainer}>
          <VoiceOrb
            isListening={isListening}
            isProcessing={isProcessing}
            onTap={handleOrbTap}
            size={190}
          />
          <Text style={styles.orbLabel}>{orbLabel}</Text>
        </View>

        {/* Error banner */}
        {voiceError ? (
          <View style={styles.errorBanner}>
            <MaterialCommunityIcons name="alert-circle" size={18} color={colors.error} />
            <Text style={styles.errorText}>{voiceError}</Text>
            <TouchableOpacity onPress={() => setVoiceError('')}>
              <MaterialCommunityIcons name="close" size={18} color={colors.error} />
            </TouchableOpacity>
          </View>
        ) : null}

        {/* Summary toggle */}
        <TouchableOpacity onPress={toggleSummary} style={styles.summaryToggle}>
          <MaterialCommunityIcons
            name={showDailySummary ? 'chevron-up' : 'chevron-down'}
            size={18}
            color={colors.primary}
          />
          <Text style={styles.summaryToggleText}>
            {showDailySummary ? "Hide daily summary" : "View daily summary"}
          </Text>
        </TouchableOpacity>

        {/* Daily Summary */}
        {showDailySummary && (
          <Animated.View
            style={{
              opacity: summaryAnim,
              transform: [
                {
                  translateY: summaryAnim.interpolate({
                    inputRange: [0, 1],
                    outputRange: [12, 0],
                  }),
                },
              ],
              marginBottom: 24,
            }}
          >
            <DailySummary patientName={PATIENT_NAME} />
          </Animated.View>
        )}
      </ScrollView>

      {/* ── Chat Bottom Bar ── */}
      <View style={[styles.bottomBar, { paddingBottom: Math.max(insets.bottom, 16) }]}>
        <ChatBottomBar onChatTap={() => setShowChat(true)} />
      </View>

      {/* Chat Modal */}
      <PatientChatSheet
        visible={showChat}
        onClose={() => setShowChat(false)}
        patientName={PATIENT_NAME}
      />
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  topBar: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 12,
  },
  logoPill: {
    width: 34,
    height: 34,
    borderRadius: 17,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 8,
  },
  logoText: {
    fontSize: 16,
    fontFamily: fonts.bold,
    color: colors.textPrimary,
  },
  settingsBtn: {
    width: 38,
    height: 38,
    borderRadius: 19,
    backgroundColor: withAlpha(colors.textMuted, 0.12),
    alignItems: 'center',
    justifyContent: 'center',
  },
  scrollContent: {
    alignItems: 'center',
    paddingTop: 24,
    paddingBottom: 24,
  },
  orbContainer: {
    alignItems: 'center',
    marginBottom: 24,
  },
  orbLabel: {
    marginTop: 18,
    fontSize: 14,
    fontFamily: fonts.semiBold,
    color: colors.textSecondary,
  },
  errorBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    backgroundColor: withAlpha(colors.error, 0.08),
    borderWidth: 1,
    borderColor: withAlpha(colors.error, 0.2),
    borderRadius: 14,
    paddingHorizontal: 14,
    paddingVertical: 10,
    marginHorizontal: 20,
    marginBottom: 16,
  },
  errorText: {
    flex: 1,
    fontSize: 13,
    fontFamily: fonts.regular,
    color: colors.error,
  },
  summaryToggle: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderRadius: 20,
    backgroundColor: withAlpha(colors.primary, 0.08),
    marginBottom: 16,
  },
  summaryToggleText: {
    fontSize: 14,
    fontFamily: fonts.semiBold,
    color: colors.primary,
  },
  bottomBar: {
    paddingTop: 10,
  },
});
