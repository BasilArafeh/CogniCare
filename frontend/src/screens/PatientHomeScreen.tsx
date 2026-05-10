import React, { useState, useRef, useEffect } from 'react';
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
import { useRoute } from '@react-navigation/native';
import type { RouteProp } from '@react-navigation/native';
import { Audio } from 'expo-av';
import { colors, fonts, withAlpha } from '../theme/colors';
import apiService from '../services/apiService';
import type { RootStackParamList } from '../navigation/AppNavigator';
import VoiceOrb from '../components/patient/VoiceOrb';
import PatientGreeting from '../components/patient/PatientGreeting';
import DailySummary from '../components/patient/DailySummary';
import ChatBottomBar from '../components/patient/ChatBottomBar';
import PatientChatSheet from '../components/patient/PatientChatSheet';
import ReminderModal from '../components/patient/ReminderModal';
import { getAiAgentBaseUrl } from '../services/backendUrls';
import * as Notifications from 'expo-notifications';
import * as Device from 'expo-device';
import Constants from 'expo-constants';
import { supabase } from '../services/supabaseClient';

// WAV / Linear PCM recording options.
// Raw numeric/string values used to avoid enum import issues across expo-av versions.
// iOS outputFormat 'lpcm' = IOSOutputFormat.LINEARPCM, audioQuality 96 = IOSAudioQuality.HIGH
// Android outputFormat 0 = AndroidOutputFormat.DEFAULT, audioEncoder 0 = AndroidAudioEncoder.DEFAULT
const WAV_RECORDING_OPTIONS = {
  android: {
    extension: '.wav',
    outputFormat: 0,
    audioEncoder: 0,
    sampleRate: 16000,
    numberOfChannels: 1,
    bitRate: 256000,
  },
  ios: {
    extension: '.wav',
    outputFormat: 'lpcm',
    audioQuality: 96,
    sampleRate: 16000,
    numberOfChannels: 1,
    bitRate: 256000,
    linearPCMBitDepth: 16,
    linearPCMIsBigEndian: false,
    linearPCMIsFloat: false,
  },
  web: {
    mimeType: 'audio/wav',
    bitsPerSecond: 256000,
  },
// eslint-disable-next-line @typescript-eslint/no-explicit-any
} as any;

function getGreeting(): string {
  const h = new Date().getHours();
  if (h < 12) return 'Good morning';
  if (h < 17) return 'Good afternoon';
  return 'Good evening';
}

export default function PatientHomeScreen() {
  const insets = useSafeAreaInsets();
  const route = useRoute<RouteProp<RootStackParamList, 'PatientHome'>>();
  const { patientId, patientName: PATIENT_NAME } = route.params;

  const [isListening, setIsListening] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isPlaying, setIsPlaying] = useState(false);
  const [voiceError, setVoiceError] = useState('');
  const [responseText, setResponseText] = useState('');
  const [responseAudioUri, setResponseAudioUri] = useState('');
  const [showDailySummary, setShowDailySummary] = useState(false);
  const [showChat, setShowChat] = useState(false);
  const [reminder, setReminder] = useState<{ message: string; reminderId: string | null } | null>(null);

  const recordingRef = useRef<Audio.Recording | null>(null);
  const soundRef = useRef<Audio.Sound | null>(null);
  const summaryAnim = useRef(new Animated.Value(0)).current;

  // Unload sound when screen unmounts
  React.useEffect(() => {
    return () => { soundRef.current?.unloadAsync(); };
  }, []);

  const handleReminderReply = async (confirmed: boolean) => {
    setReminder(null);
    await fetch(`${getAiAgentBaseUrl()}/agent/reminder-reply`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ patient_id: patientId, confirmed }),
    });
  };

  // Listen for push notifications
  useEffect(() => {
    // Register push token in background (non-blocking)
    if (Device.isDevice) {
      Notifications.requestPermissionsAsync().then(({ status }) => {
        console.log('[PushToken] permission status:', status);
        if (status === 'granted') {
          const projectId = Constants.expoConfig?.extra?.eas?.projectId;
          console.log('[PushToken] projectId:', projectId);
          Notifications.getExpoPushTokenAsync({ projectId }).then(tokenData => {
            console.log('[PushToken] token:', tokenData.data);
            supabase.from('patients').update({ push_token: tokenData.data }).eq('patient_id', patientId)
              .then(({ error }) => console.log('[PushToken] saved to db, error:', error));
          }).catch(err => console.log('[PushToken] getExpoPushTokenAsync error:', err));
        }
      }).catch(err => console.log('[PushToken] requestPermissions error:', err));
    } else {
      console.log('[PushToken] not a physical device, skipping');
    }

    // App is open — notification arrives
    const foreground = Notifications.addNotificationReceivedListener(notification => {
      const message = notification.request.content.body;
      if (message) setReminder({ message, reminderId: null });
    });

    // App is background — user taps notification
    const tap = Notifications.addNotificationResponseReceivedListener(response => {
      const message = response.notification.request.content.body;
      if (message) setReminder({ message, reminderId: null });
    });

    // App was killed — user tapped notification to open app
    Notifications.getLastNotificationResponseAsync().then(response => {
      if (response) {
        const message = response.notification.request.content.body;
        if (message) setReminder({ message, reminderId: null });
      }
    });

    return () => {
      foreground.remove();
      tap.remove();
    };
  }, []);

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
      const { recording } = await Audio.Recording.createAsync(WAV_RECORDING_OPTIONS);
      recordingRef.current = recording;
      setIsListening(true);
    } catch (err) {
      setVoiceError('Could not start recording. Please try again.');
      console.warn('startRecording error:', err);
    }
  };

  const playResponse = async (uri: string) => {
    try {
      if (soundRef.current) {
        await soundRef.current.unloadAsync();
        soundRef.current = null;
      }
      setIsPlaying(true);
      await Audio.setAudioModeAsync({ allowsRecordingIOS: false, playsInSilentModeIOS: true });
      const { sound } = await Audio.Sound.createAsync({ uri });
      soundRef.current = sound;
      sound.setOnPlaybackStatusUpdate((status) => {
        if (status.isLoaded && status.didJustFinish) setIsPlaying(false);
      });
      await sound.playAsync();
    } catch (err) {
      setIsPlaying(false);
      console.warn('playResponse error:', err);
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

      if (!uri) return;

      const result = await apiService.sendVoiceRecording(patientId, uri);
      setResponseText(result.replyText);
      setResponseAudioUri(result.audioUri);
      console.log('responseAudioUri', result);
      await playResponse(result.audioUri);
    } catch (err) {
      setVoiceError('Voice message failed. Please try again.');
      console.warn('stopAndSend error:', err);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleOrbTap = () => {
    if (isProcessing || isPlaying) return;
    if (isListening) {
      stopAndSend();
    } else {
      startRecording();
    }
  };

  const orbLabel = isProcessing
    ? 'Processing...'
    : isPlaying
    ? 'Playing response...'
    : isListening
    ? 'Tap to stop'
    : 'Tap to speak';

  return (
    <LinearGradient
      colors={['#F5F0FF', '#FFFFFF', '#EDE8F8']}
      style={[styles.container, { paddingTop: insets.top }]}
    >
      {reminder && (
        <ReminderModal
          message={reminder.message}
          onYes={() => handleReminderReply(true)}
          onNo={() => handleReminderReply(false)}
        />
      )}
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

        {/* Voice response note */}
        {responseText ? (
          <View style={styles.voiceNote}>
            <TouchableOpacity
              onPress={() => responseAudioUri && playResponse(responseAudioUri)}
              style={styles.voiceNotePlayBtn}
              disabled={isPlaying}
            >
              <MaterialCommunityIcons
                name={isPlaying ? 'pause-circle' : 'play-circle'}
                size={30}
                color={colors.primary}
              />
            </TouchableOpacity>
            <Text style={styles.voiceNoteText}>{responseText}</Text>
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
              alignSelf: 'stretch',
            }}
          >
            <DailySummary patientId={patientId} />
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
        patientId={patientId}
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
  voiceNote: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 10,
    backgroundColor: withAlpha(colors.primary, 0.06),
    borderWidth: 1,
    borderColor: withAlpha(colors.primary, 0.15),
    borderRadius: 16,
    paddingHorizontal: 14,
    paddingVertical: 12,
    marginHorizontal: 20,
    marginBottom: 16,
  },
  voiceNotePlayBtn: {
    marginTop: 2,
  },
  voiceNoteText: {
    flex: 1,
    fontSize: 14,
    fontFamily: fonts.regular,
    color: colors.textPrimary,
    lineHeight: 20,
  },
});
