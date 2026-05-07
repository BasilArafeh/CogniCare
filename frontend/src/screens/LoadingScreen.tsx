import React, { useEffect } from 'react';
import { ActivityIndicator, StyleSheet } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { useNavigation } from '@react-navigation/native';
import type { StackNavigationProp } from '@react-navigation/stack';
import type { RootStackParamList } from '../navigation/AppNavigator';
import { colors } from '../theme/colors';

type NavProp = StackNavigationProp<RootStackParamList, 'Loading'>;

export default function LoadingScreen() {
  const navigation = useNavigation<NavProp>();

  useEffect(() => {
    navigation.replace('Welcome');
  }, [navigation]);

  return (
    <LinearGradient colors={['#F0EAFF', '#F5F3FF']} style={styles.container}>
      <ActivityIndicator color={colors.primary} size="large" />
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
});
