/**
 * ConnectionDiagnostics widget displaying host IP, API target, and latency test.
 */

import React, { useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { ENV } from '../config/env';
import { CONSTANTS } from '../config/constants';

export const ConnectionDiagnostics: React.FC = () => {
  const [latency, setLatency] = useState<number | null>(null);
  const [isTesting, setIsTesting] = useState<boolean>(false);
  const [statusText, setStatusText] = useState<string>('Not tested');

  const testConnection = async () => {
    setIsTesting(true);
    setStatusText('Pinging...');
    const start = Date.now();
    try {
      const resp = await fetch(ENV.API_BASE_URL.replace('/demo', '/health'), {
        method: 'GET',
      });
      const end = Date.now();
      if (resp.ok) {
        const ms = end - start;
        setLatency(ms);
        setStatusText(`Connected (${ms}ms)`);
      } else {
        setStatusText(`HTTP ${resp.status}`);
      }
    } catch (err: any) {
      setStatusText('Unreachable');
      setLatency(null);
    } finally {
      setIsTesting(false);
    }
  };

  return (
    <View style={styles.container}>
      <View style={styles.row}>
        <Text style={styles.label}>Target Host API:</Text>
        <Text style={styles.value} numberOfLines={1}>
          {ENV.API_BASE_URL}
        </Text>
      </View>
      <View style={styles.row}>
        <Text style={styles.label}>Link Status:</Text>
        <Text style={[styles.value, latency !== null && styles.textSuccess]}>
          {statusText}
        </Text>
      </View>
      <TouchableOpacity
        style={styles.btn}
        onPress={testConnection}
        disabled={isTesting}
      >
        <Text style={styles.btnText}>{isTesting ? 'Testing...' : 'Test Connection'}</Text>
      </TouchableOpacity>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: '#0c1322',
    borderRadius: 8,
    padding: 10,
    marginVertical: 6,
    borderWidth: 1,
    borderColor: '#1e293b',
  },
  row: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginVertical: 2,
  },
  label: {
    fontSize: 11,
    color: CONSTANTS.COLORS.textMuted,
  },
  value: {
    fontSize: 11,
    fontWeight: '600',
    color: CONSTANTS.COLORS.textMain,
    maxWidth: '65%',
  },
  textSuccess: {
    color: CONSTANTS.COLORS.success,
  },
  btn: {
    marginTop: 6,
    paddingVertical: 4,
    alignItems: 'center',
    backgroundColor: '#1e293b',
    borderRadius: 6,
  },
  btnText: {
    fontSize: 11,
    fontWeight: '600',
    color: CONSTANTS.COLORS.primary,
  },
});
