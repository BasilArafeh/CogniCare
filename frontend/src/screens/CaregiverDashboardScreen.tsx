import React, { useState } from 'react';
import { View, TouchableOpacity, Text, StyleSheet } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import type { RouteProp } from '@react-navigation/native';
import type { StackNavigationProp } from '@react-navigation/stack';
import type { RootStackParamList } from '../navigation/AppNavigator';
import { colors, fonts, withAlpha } from '../theme/colors';
import DashboardHomeTab from '../components/caregiver/DashboardHomeTab';
import DashboardReportsTab from '../components/caregiver/DashboardReportsTab';
import DashboardSettingsTab from '../components/caregiver/DashboardSettingsTab';

type Tab = 'home' | 'reports' | 'settings';

type Props = {
  route: RouteProp<RootStackParamList, 'CaregiverDashboard'>;
  navigation: StackNavigationProp<RootStackParamList, 'CaregiverDashboard'>;
};

const TABS: { key: Tab; icon: string; label: string }[] = [
  { key: 'home',     icon: 'view-dashboard',   label: 'Dashboard' },
  { key: 'reports',  icon: 'chart-bar',         label: 'Reports'   },
  { key: 'settings', icon: 'cog',               label: 'Settings'  },
];

export default function CaregiverDashboardScreen({ route, navigation }: Props) {
  const { patientId, caregiverId, caregiverName, patientName } = route.params;
  const [activeTab, setActiveTab] = useState<Tab>('home');
  const insets = useSafeAreaInsets();

  const renderContent = () => {
    switch (activeTab) {
      case 'home':
        return (
          <DashboardHomeTab
            patientId={patientId}
            caregiverId={caregiverId}
            caregiverName={caregiverName}
            patientName={patientName}
            onGoToPatient={() => navigation.navigate('PatientHome', { patientId, patientName })}
          />
        );
      case 'reports':
        return (
          <DashboardReportsTab
            patientId={patientId}
            patientName={patientName}
          />
        );
      case 'settings':
        return (
          <DashboardSettingsTab
            patientId={patientId}
            caregiverId={caregiverId}
          />
        );
    }
  };

  return (
    <LinearGradient
      colors={['#F0EAFF', '#F5F3FF']}
      style={[styles.container, { paddingTop: insets.top }]}
    >
      <View style={styles.content}>
        {renderContent()}
      </View>

      {/* Custom bottom tab bar */}
      <View style={[styles.tabBar, { paddingBottom: Math.max(insets.bottom, 12) }]}>
        {TABS.map((tab) => {
          const active = activeTab === tab.key;
          return (
            <TouchableOpacity
              key={tab.key}
              onPress={() => setActiveTab(tab.key)}
              style={styles.tabItem}
              activeOpacity={0.7}
            >
              {active && <View style={styles.tabActiveIndicator} />}
              <View style={[styles.tabIconWrap, active && styles.tabIconWrapActive]}>
                <MaterialCommunityIcons
                  name={tab.icon as any}
                  size={22}
                  color={active ? colors.primary : colors.textMuted}
                />
              </View>
              <Text style={[styles.tabLabel, active && styles.tabLabelActive]}>
                {tab.label}
              </Text>
            </TouchableOpacity>
          );
        })}
      </View>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  content: {
    flex: 1,
  },
  tabBar: {
    flexDirection: 'row',
    backgroundColor: colors.white,
    borderTopWidth: 1,
    borderTopColor: withAlpha(colors.primaryMuted, 0.25),
    paddingTop: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: -2 },
    shadowOpacity: 0.06,
    shadowRadius: 8,
    elevation: 10,
  },
  tabItem: {
    flex: 1,
    alignItems: 'center',
    gap: 4,
  },
  tabActiveIndicator: {
    position: 'absolute',
    top: -8,
    width: 32,
    height: 3,
    borderRadius: 2,
    backgroundColor: colors.primary,
  },
  tabIconWrap: {
    width: 40,
    height: 36,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 12,
  },
  tabIconWrapActive: {
    backgroundColor: withAlpha(colors.primary, 0.1),
  },
  tabLabel: {
    fontSize: 11,
    fontFamily: fonts.semiBold,
    color: colors.textMuted,
  },
  tabLabelActive: {
    color: colors.primary,
  },
});
