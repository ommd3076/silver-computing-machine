/**
 * DebugLeaf Driver Mobile Application Root Entrypoint.
 */

import React from 'react';
import { View, Text, StyleSheet, ActivityIndicator } from 'react-native';
import { StatusBar } from 'expo-status-bar';
import { SessionProvider, useSession } from './src/auth/SessionContext';
import { PairingScreen } from './src/screens/PairingScreen';
import { DriverHomeScreen } from './src/screens/DriverHomeScreen';
import { CONSTANTS } from './src/config/constants';

const MainNavigator: React.FC = () => {
  const { isAuthenticated, isLoading } = useSession();

  if (isLoading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color={CONSTANTS.COLORS.primary} />
        <Text style={styles.loadingText}>Initializing DebugLeaf Driver Edge...</Text>
      </View>
    );
  }

  return isAuthenticated ? <DriverHomeScreen /> : <PairingScreen />;
};

export default function App() {
  return (
    <SessionProvider>
      <StatusBar style="light" />
      <MainNavigator />
    </SessionProvider>
  );
}

const styles = StyleSheet.create({
  loadingContainer: {
    flex: 1,
    backgroundColor: CONSTANTS.COLORS.background,
    alignItems: 'center',
    justifyContent: 'center',
  },
  loadingText: {
    color: CONSTANTS.COLORS.textMuted,
    fontSize: 14,
    marginTop: 12,
  },
});
