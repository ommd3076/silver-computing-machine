/**
 * Driver Pairing Screen: code entry and device registration.
 */

import React, { useState } from 'react';
import {
  View,
  Text,
  TextInput,
  StyleSheet,
  SafeAreaView,
  KeyboardAvoidingView,
  Platform,
  TouchableOpacity,
} from 'react-native';
import { useSession } from '../auth/SessionContext';
import { PrimaryButton } from '../components/PrimaryButton';
import { ConnectionDiagnostics } from '../components/ConnectionDiagnostics';
import { CONSTANTS } from '../config/constants';

export const PairingScreen: React.FC = () => {
  const { login, isLoading, error, clearError } = useSession();
  const [code, setCode] = useState<string>('');

  const handlePair = async () => {
    if (!code.trim()) return;
    try {
      await login(code.trim());
    } catch {
      // Error handled via session context
    }
  };

  const handleQuickFill = (demoCode: string) => {
    clearError();
    setCode(demoCode);
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
        style={styles.container}
      >
        <View style={styles.content}>
          <View style={styles.header}>
            <Text style={styles.logo}>DEBUGLEAF</Text>
            <Text style={styles.subLogo}>Mobile Driver Cockpit</Text>
            <Text style={styles.instructions}>
              Enter your assigned 6-character one-time pairing code to synchronize with dispatch.
            </Text>
          </View>

          <View style={styles.inputContainer}>
            <TextInput
              style={styles.input}
              placeholder="e.g. PAIR01"
              placeholderTextColor="#64748b"
              value={code}
              onChangeText={(t) => {
                clearError();
                setCode(t.toUpperCase());
              }}
              autoCapitalize="characters"
              autoCorrect={false}
              maxLength={12}
            />

            {error && (
              <View style={styles.errorBox}>
                <Text style={styles.errorText}>{error}</Text>
              </View>
            )}

            <PrimaryButton
              title="Pair & Start Route"
              onPress={handlePair}
              isLoading={isLoading}
              disabled={!code.trim()}
            />

            <View style={styles.quickFillSection}>
              <Text style={styles.quickFillLabel}>Quick Demo Presets:</Text>
              <View style={styles.quickFillRow}>
                <TouchableOpacity
                  style={styles.presetButton}
                  onPress={() => handleQuickFill('PAIR01')}
                >
                  <Text style={styles.presetText}>Driver 1 (PAIR01)</Text>
                </TouchableOpacity>
                <TouchableOpacity
                  style={styles.presetButton}
                  onPress={() => handleQuickFill('PAIR02')}
                >
                  <Text style={styles.presetText}>Driver 2 (PAIR02)</Text>
                </TouchableOpacity>
              </View>
            </View>
          </View>

          <View style={styles.footer}>
            <ConnectionDiagnostics />
          </View>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: CONSTANTS.COLORS.background,
  },
  container: {
    flex: 1,
  },
  content: {
    flex: 1,
    padding: 24,
    justifyContent: 'space-between',
  },
  header: {
    marginTop: 40,
    alignItems: 'center',
  },
  logo: {
    fontSize: 28,
    fontWeight: '900',
    color: CONSTANTS.COLORS.textMain,
    letterSpacing: 2,
  },
  subLogo: {
    fontSize: 14,
    color: CONSTANTS.COLORS.primary,
    fontWeight: '700',
    marginTop: 4,
    textTransform: 'uppercase',
  },
  instructions: {
    fontSize: 13,
    color: CONSTANTS.COLORS.textMuted,
    textAlign: 'center',
    marginTop: 16,
    lineHeight: 20,
    paddingHorizontal: 20,
  },
  inputContainer: {
    marginVertical: 20,
  },
  input: {
    height: 60,
    backgroundColor: CONSTANTS.COLORS.surface,
    borderWidth: 2,
    borderColor: CONSTANTS.COLORS.surfaceBorder,
    borderRadius: 14,
    fontSize: 22,
    fontWeight: '800',
    color: CONSTANTS.COLORS.textMain,
    textAlign: 'center',
    letterSpacing: 4,
    marginBottom: 12,
  },
  errorBox: {
    backgroundColor: 'rgba(239, 68, 68, 0.15)',
    borderWidth: 1,
    borderColor: 'rgba(239, 68, 68, 0.3)',
    borderRadius: 8,
    padding: 10,
    marginBottom: 12,
  },
  errorText: {
    color: CONSTANTS.COLORS.danger,
    fontSize: 12,
    fontWeight: '600',
    textAlign: 'center',
  },
  quickFillSection: {
    marginTop: 20,
    alignItems: 'center',
  },
  quickFillLabel: {
    fontSize: 12,
    color: CONSTANTS.COLORS.textMuted,
    marginBottom: 8,
  },
  quickFillRow: {
    flexDirection: 'row',
    justifyContent: 'center',
    gap: 10,
  },
  presetButton: {
    paddingHorizontal: 14,
    paddingVertical: 8,
    backgroundColor: '#1e293b',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#334155',
  },
  presetText: {
    color: CONSTANTS.COLORS.primary,
    fontSize: 12,
    fontWeight: '700',
  },
  footer: {
    marginBottom: 10,
  },
});
