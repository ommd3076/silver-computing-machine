/**
 * RouteUpdatedAlert modal dialog appearing when server synchronizes a new route revision.
 */

import React from 'react';
import { View, Text, StyleSheet, Modal } from 'react-native';
import { PrimaryButton } from '../components/PrimaryButton';
import { CONSTANTS } from '../config/constants';

interface RouteUpdatedAlertProps {
  visible: boolean;
  oldVersion: number;
  newVersion: number;
  oldRouteName?: string;
  newRouteName?: string;
  onAcknowledge: () => void;
}

export const RouteUpdatedAlert: React.FC<RouteUpdatedAlertProps> = ({
  visible,
  oldVersion,
  newVersion,
  oldRouteName,
  newRouteName,
  onAcknowledge,
}) => {
  return (
    <Modal visible={visible} transparent animationType="fade">
      <View style={styles.overlay}>
        <View style={styles.card}>
          <View style={styles.header}>
            <View style={styles.iconCircle}>
              <Text style={styles.icon}>⚡</Text>
            </View>
            <Text style={styles.title}>New Route Published</Text>
            <Text style={styles.subtitle}>
              Server re-evaluated corridor conditions and published an updated delivery route.
            </Text>
          </View>

          <View style={styles.versionRow}>
            <View style={styles.vBox}>
              <Text style={styles.vLabel}>PREVIOUS</Text>
              <Text style={styles.vNum}>v{oldVersion}</Text>
              <Text style={styles.vName} numberOfLines={1}>
                {oldRouteName || 'Previous Route'}
              </Text>
            </View>

            <Text style={styles.arrow}>➔</Text>

            <View style={[styles.vBox, styles.vBoxNew]}>
              <Text style={[styles.vLabel, styles.vLabelNew]}>NEW ROUTE</Text>
              <Text style={[styles.vNum, styles.vNumNew]}>v{newVersion}</Text>
              <Text style={[styles.vName, styles.vNameNew]} numberOfLines={1}>
                {newRouteName || 'Updated Corridor'}
              </Text>
            </View>
          </View>

          <PrimaryButton
            title="Acknowledge & View New Route"
            onPress={onAcknowledge}
          />
        </View>
      </View>
    </Modal>
  );
};

const styles = StyleSheet.create({
  overlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.75)',
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  card: {
    backgroundColor: CONSTANTS.COLORS.surface,
    borderRadius: 18,
    padding: 24,
    width: '100%',
    maxWidth: 400,
    borderWidth: 2,
    borderColor: CONSTANTS.COLORS.primary,
  },
  header: {
    alignItems: 'center',
    marginBottom: 16,
  },
  iconCircle: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: 'rgba(56, 189, 248, 0.15)',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 10,
  },
  icon: {
    fontSize: 24,
  },
  title: {
    fontSize: 20,
    fontWeight: '800',
    color: CONSTANTS.COLORS.textMain,
    textAlign: 'center',
  },
  subtitle: {
    fontSize: 12,
    color: CONSTANTS.COLORS.textMuted,
    textAlign: 'center',
    marginTop: 6,
    lineHeight: 18,
  },
  versionRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    backgroundColor: '#0c1322',
    borderRadius: 12,
    padding: 14,
    marginVertical: 16,
    borderWidth: 1,
    borderColor: '#1e293b',
  },
  vBox: {
    flex: 1,
    alignItems: 'center',
  },
  vBoxNew: {
    backgroundColor: 'rgba(56, 189, 248, 0.08)',
    borderRadius: 8,
    paddingVertical: 6,
  },
  arrow: {
    fontSize: 18,
    color: CONSTANTS.COLORS.primary,
    paddingHorizontal: 8,
  },
  vLabel: {
    fontSize: 10,
    fontWeight: '700',
    color: CONSTANTS.COLORS.textMuted,
  },
  vLabelNew: {
    color: CONSTANTS.COLORS.primary,
  },
  vNum: {
    fontSize: 18,
    fontWeight: '900',
    color: CONSTANTS.COLORS.textMain,
    marginVertical: 2,
  },
  vNumNew: {
    color: CONSTANTS.COLORS.primary,
  },
  vName: {
    fontSize: 11,
    color: CONSTANTS.COLORS.textMuted,
  },
  vNameNew: {
    color: '#e2e8f0',
    fontWeight: '600',
  },
});
