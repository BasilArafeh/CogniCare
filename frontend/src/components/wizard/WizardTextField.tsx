import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  TouchableOpacity,
  StyleSheet,
  StyleProp,
  ViewStyle,
  KeyboardTypeOptions,
} from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { colors, fonts, withAlpha } from '../../theme/colors';

interface WizardTextFieldProps {
  label: string;
  hint?: string;
  value: string;
  onChangeText: (text: string) => void;
  keyboardType?: KeyboardTypeOptions;
  secureTextEntry?: boolean;
  multiline?: boolean;
  numberOfLines?: number;
  prefixIconName?: string;
  error?: string;
  style?: StyleProp<ViewStyle>;
}

export default function WizardTextField({
  label,
  hint,
  value,
  onChangeText,
  keyboardType = 'default',
  secureTextEntry = false,
  multiline = false,
  numberOfLines = 1,
  prefixIconName,
  error,
  style,
}: WizardTextFieldProps) {
  const [isFocused, setIsFocused] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  const isPassword = secureTextEntry;
  const actualSecure = isPassword && !showPassword;

  const borderColor = error
    ? colors.error
    : isFocused
    ? colors.primary
    : withAlpha(colors.textMuted, 0.4);

  const bgColor = error
    ? withAlpha(colors.error, 0.04)
    : isFocused
    ? colors.primaryLight
    : withAlpha(colors.textMuted, 0.06);

  return (
    <View style={[styles.wrapper, style]}>
      <Text style={[styles.label, error ? styles.labelError : isFocused ? styles.labelFocused : null]}>
        {label}
      </Text>
      <View
        style={[
          styles.inputContainer,
          { borderColor, backgroundColor: bgColor },
          multiline && { minHeight: 24 * (numberOfLines || 1) + 28 },
        ]}
      >
        {prefixIconName ? (
          <MaterialCommunityIcons
            name={prefixIconName as any}
            size={18}
            color={isFocused ? colors.primary : colors.textMuted}
            style={styles.prefixIcon}
          />
        ) : null}
        <TextInput
          value={value}
          onChangeText={onChangeText}
          placeholder={hint}
          placeholderTextColor={colors.textMuted}
          keyboardType={keyboardType}
          secureTextEntry={actualSecure}
          multiline={multiline}
          numberOfLines={numberOfLines}
          onFocus={() => setIsFocused(true)}
          onBlur={() => setIsFocused(false)}
          style={[
            styles.input,
            multiline && styles.inputMultiline,
          ]}
        />
        {isPassword ? (
          <TouchableOpacity
            onPress={() => setShowPassword((v) => !v)}
            style={styles.suffixButton}
          >
            <MaterialCommunityIcons
              name={showPassword ? 'eye-off' : 'eye'}
              size={18}
              color={colors.textMuted}
            />
          </TouchableOpacity>
        ) : null}
      </View>
      {error ? <Text style={styles.errorText}>{error}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: {
    marginBottom: 14,
  },
  label: {
    fontSize: 13,
    fontFamily: fonts.semiBold,
    color: colors.textSecondary,
    marginBottom: 6,
  },
  labelFocused: {
    color: colors.primary,
  },
  labelError: {
    color: colors.error,
  },
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1.5,
    borderRadius: 12,
    paddingHorizontal: 14,
    paddingVertical: 2,
    minHeight: 50,
  },
  prefixIcon: {
    marginRight: 8,
  },
  input: {
    flex: 1,
    fontSize: 15,
    fontFamily: fonts.regular,
    color: colors.textPrimary,
    paddingVertical: 10,
  },
  inputMultiline: {
    textAlignVertical: 'top',
    paddingTop: 10,
  },
  suffixButton: {
    padding: 4,
    marginLeft: 4,
  },
  errorText: {
    fontSize: 12,
    fontFamily: fonts.regular,
    color: colors.error,
    marginTop: 4,
    marginLeft: 4,
  },
});
