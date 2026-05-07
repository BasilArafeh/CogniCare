import React, { useState, useRef, useEffect } from 'react';
import {
  View,
  Text,
  Modal,
  FlatList,
  TextInput,
  TouchableOpacity,
  KeyboardAvoidingView,
  Animated,
  Platform,
  StyleSheet,
  Dimensions,
  Keyboard,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { colors, fonts, withAlpha } from '../../theme/colors';
import apiService from '../../services/apiService';

interface ChatMessage {
  id: string;
  text: string;
  isUser: boolean;
  timestamp: Date;
}

interface Props {
  visible: boolean;
  onClose: () => void;
  patientName: string;
  patientId: number;
}

const { height: SCREEN_HEIGHT } = Dimensions.get('window');

function makeGreeting(name: string): ChatMessage {
  const firstName = name.split(' ')[0] || name;
  return {
    id: '0',
    text: `Hello ${firstName}! How are you feeling today? 😊 You can ask me about your medications, meals, activities, or anything else.`,
    isUser: false,
    timestamp: new Date(),
  };
}

function TypingIndicator() {
  const dot1 = useRef(new Animated.Value(0)).current;
  const dot2 = useRef(new Animated.Value(0)).current;
  const dot3 = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    const loop = (val: Animated.Value, delay: number) =>
      Animated.loop(
        Animated.sequence([
          Animated.delay(delay),
          Animated.timing(val, { toValue: -6, duration: 300, useNativeDriver: true }),
          Animated.timing(val, { toValue: 0, duration: 300, useNativeDriver: true }),
        ]),
      );
    const a1 = loop(dot1, 0);
    const a2 = loop(dot2, 150);
    const a3 = loop(dot3, 300);
    a1.start(); a2.start(); a3.start();
    return () => { a1.stop(); a2.stop(); a3.stop(); };
  }, []);

  return (
    <View style={styles.typingBubble}>
      {[dot1, dot2, dot3].map((d, i) => (
        <Animated.View
          key={i}
          style={[styles.typingDot, { transform: [{ translateY: d }] }]}
        />
      ))}
    </View>
  );
}

export default function PatientChatSheet({ visible, onClose, patientName, patientId }: Props) {
  const insets = useSafeAreaInsets();
  const [messages, setMessages] = useState<ChatMessage[]>(() => [makeGreeting(patientName)]);
  const [inputText, setInputText] = useState('');
  const [isSending, setIsSending] = useState(false);
  const flatListRef = useRef<FlatList>(null);

  const scrollToBottom = () => {
    setTimeout(() => flatListRef.current?.scrollToEnd({ animated: true }), 100);
  };

  useEffect(() => {
    if (visible) scrollToBottom();
  }, [visible]);

  const handleSend = async () => {
    const text = inputText.trim();
    if (!text || isSending) return;

    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      text,
      isUser: true,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setInputText('');
    setIsSending(true);
    Keyboard.dismiss();
    scrollToBottom();

    try {
      const reply = await apiService.sendChatMessage(patientId, text);
      setMessages((prev) => [
        ...prev,
        { id: (Date.now() + 1).toString(), text: reply, isUser: false, timestamp: new Date() },
      ]);
    } catch {
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          text: "Sorry, I couldn't connect right now. Please try again.",
          isUser: false,
          timestamp: new Date(),
        },
      ]);
    } finally {
      setIsSending(false);
      scrollToBottom();
    }
  };

  const renderMessage = ({ item }: { item: ChatMessage }) => {
    if (item.isUser) {
      return (
        <View style={styles.userMsgRow}>
          <LinearGradient
            colors={[colors.primary, colors.primaryMuted]}
            style={styles.userBubble}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 1 }}
          >
            <Text style={styles.userMsgText}>{item.text}</Text>
          </LinearGradient>
        </View>
      );
    }
    return (
      <View style={styles.aiMsgRow}>
        <View style={styles.aiAvatar}>
          <MaterialCommunityIcons name="brain" size={16} color={colors.primary} />
        </View>
        <View style={styles.aiBubble}>
          <Text style={styles.aiMsgText}>{item.text}</Text>
        </View>
      </View>
    );
  };

  return (
    <Modal
      visible={visible}
      animationType="slide"
      transparent
      onRequestClose={onClose}
    >
      <View style={styles.overlay}>
        <TouchableOpacity style={styles.dismissArea} onPress={onClose} activeOpacity={1} />
        <KeyboardAvoidingView
          behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
          style={[styles.sheet, { height: SCREEN_HEIGHT * 0.82 }]}
        >
          {/* Header */}
          <View style={styles.header}>
            <View style={styles.dragHandle} />
            <View style={styles.headerRow}>
              <LinearGradient
                colors={[colors.primary, colors.primaryMuted]}
                style={styles.headerAvatar}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 1 }}
              >
                <MaterialCommunityIcons name="brain" size={20} color={colors.white} />
              </LinearGradient>
              <View style={styles.headerInfo}>
                <Text style={styles.headerName}>CogniCare</Text>
                <Text style={styles.headerSub}>Always here for you</Text>
              </View>
              <TouchableOpacity onPress={onClose} style={styles.closeBtn}>
                <MaterialCommunityIcons name="close" size={20} color={colors.textSecondary} />
              </TouchableOpacity>
            </View>
          </View>

          <View style={styles.divider} />

          {/* Messages */}
          <FlatList
            ref={flatListRef}
            data={messages}
            keyExtractor={(item) => item.id}
            renderItem={renderMessage}
            contentContainerStyle={styles.messagesList}
            onContentSizeChange={scrollToBottom}
            showsVerticalScrollIndicator={false}
            ListFooterComponent={isSending ? <TypingIndicator /> : null}
          />

          {/* Input bar */}
          <View style={[styles.inputBar, { paddingBottom: Math.max(insets.bottom, 12) }]}>
            <TextInput
              value={inputText}
              onChangeText={setInputText}
              placeholder={`Message CogniCare...`}
              placeholderTextColor={colors.textMuted}
              style={styles.textInput}
              multiline
              onSubmitEditing={handleSend}
              blurOnSubmit
            />
            <TouchableOpacity onPress={handleSend} disabled={!inputText.trim() || isSending}>
              <LinearGradient
                colors={
                  inputText.trim()
                    ? [colors.primary, colors.primaryMuted]
                    : [colors.textMuted, colors.textMuted]
                }
                style={styles.sendBtn}
                start={{ x: 0, y: 0 }}
                end={{ x: 1, y: 1 }}
              >
                <MaterialCommunityIcons name="send" size={18} color={colors.white} />
              </LinearGradient>
            </TouchableOpacity>
          </View>
        </KeyboardAvoidingView>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    justifyContent: 'flex-end',
    backgroundColor: withAlpha('#000000', 0.4),
  },
  dismissArea: {
    flex: 1,
  },
  sheet: {
    backgroundColor: colors.white,
    borderTopLeftRadius: 28,
    borderTopRightRadius: 28,
    overflow: 'hidden',
  },
  header: {
    paddingTop: 12,
    paddingHorizontal: 20,
    paddingBottom: 12,
  },
  dragHandle: {
    width: 36,
    height: 4,
    borderRadius: 2,
    backgroundColor: withAlpha(colors.textMuted, 0.3),
    alignSelf: 'center',
    marginBottom: 12,
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  headerAvatar: {
    width: 44,
    height: 44,
    borderRadius: 22,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  headerInfo: {
    flex: 1,
  },
  headerName: {
    fontSize: 16,
    fontFamily: fonts.bold,
    color: colors.textPrimary,
  },
  headerSub: {
    fontSize: 12,
    fontFamily: fonts.regular,
    color: colors.textSecondary,
  },
  closeBtn: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: withAlpha(colors.textMuted, 0.1),
    alignItems: 'center',
    justifyContent: 'center',
  },
  divider: {
    height: 1,
    backgroundColor: withAlpha(colors.primaryMuted, 0.15),
  },
  messagesList: {
    padding: 16,
    paddingBottom: 8,
  },
  userMsgRow: {
    alignItems: 'flex-end',
    marginBottom: 12,
  },
  userBubble: {
    maxWidth: '75%',
    borderRadius: 20,
    borderBottomRightRadius: 4,
    paddingHorizontal: 16,
    paddingVertical: 10,
  },
  userMsgText: {
    fontSize: 15,
    fontFamily: fonts.regular,
    color: colors.white,
    lineHeight: 22,
  },
  aiMsgRow: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    marginBottom: 12,
    gap: 8,
  },
  aiAvatar: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: colors.primaryLight,
    alignItems: 'center',
    justifyContent: 'center',
  },
  aiBubble: {
    maxWidth: '75%',
    backgroundColor: colors.background,
    borderRadius: 20,
    borderBottomLeftRadius: 4,
    paddingHorizontal: 16,
    paddingVertical: 10,
    borderWidth: 1,
    borderColor: withAlpha(colors.primaryMuted, 0.2),
  },
  aiMsgText: {
    fontSize: 15,
    fontFamily: fonts.regular,
    color: colors.textPrimary,
    lineHeight: 22,
  },
  typingBubble: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.background,
    borderRadius: 20,
    padding: 14,
    alignSelf: 'flex-start',
    marginBottom: 8,
    marginLeft: 40,
    gap: 5,
  },
  typingDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.primaryMuted,
  },
  inputBar: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    paddingHorizontal: 16,
    paddingTop: 10,
    borderTopWidth: 1,
    borderTopColor: withAlpha(colors.primaryMuted, 0.15),
    gap: 10,
  },
  textInput: {
    flex: 1,
    minHeight: 44,
    maxHeight: 100,
    backgroundColor: colors.background,
    borderRadius: 22,
    paddingHorizontal: 16,
    paddingVertical: 10,
    fontSize: 15,
    fontFamily: fonts.regular,
    color: colors.textPrimary,
    borderWidth: 1,
    borderColor: withAlpha(colors.primaryMuted, 0.2),
  },
  sendBtn: {
    width: 44,
    height: 44,
    borderRadius: 22,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
