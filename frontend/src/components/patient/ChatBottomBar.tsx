import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet, Platform } from 'react-native';
import { BlurView } from 'expo-blur';
import { LinearGradient } from 'expo-linear-gradient';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { colors, fonts, withAlpha } from '../../theme/colors';

interface Props {
  onChatTap: () => void;
}

export default function ChatBottomBar({ onChatTap }: Props) {
  return (
    <TouchableOpacity
      onPress={onChatTap}
      activeOpacity={0.85}
      style={styles.wrapper}
    >
      <BlurView intensity={20} tint="light" style={styles.blurContainer}>
        {/* Gradient orb */}
        <LinearGradient
          colors={[colors.primary, colors.primaryMuted]}
          style={styles.orbIcon}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
        >
          <MaterialCommunityIcons name="chat-processing" size={18} color={colors.white} />
        </LinearGradient>

        {/* Placeholder text */}
        <Text style={styles.placeholder}>Ask me anything...</Text>

        {/* Mic button */}
        <View style={styles.micBtn}>
          <MaterialCommunityIcons name="microphone" size={18} color={colors.primary} />
        </View>
      </BlurView>
    </TouchableOpacity>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    marginHorizontal: 16,
    borderRadius: 28,
    overflow: 'hidden',
    shadowColor: colors.primary,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.12,
    shadowRadius: 14,
    elevation: 6,
  },
  blurContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 14,
    paddingVertical: 10,
    backgroundColor: Platform.OS === 'android' ? withAlpha(colors.white, 0.92) : 'transparent',
    borderRadius: 28,
    borderWidth: 1,
    borderColor: withAlpha(colors.primaryMuted, 0.25),
  },
  orbIcon: {
    width: 38,
    height: 38,
    borderRadius: 19,
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 10,
  },
  placeholder: {
    flex: 1,
    fontSize: 15,
    fontFamily: fonts.regular,
    color: colors.textMuted,
  },
  micBtn: {
    width: 38,
    height: 38,
    borderRadius: 19,
    backgroundColor: colors.primaryLight,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
