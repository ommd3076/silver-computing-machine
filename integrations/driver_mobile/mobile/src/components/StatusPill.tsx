/**
 * StatusPill component with operational color codes.
 */

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { CONSTANTS } from '../config/constants';

interface StatusPillProps {
  status: string;
}

export const StatusPill: React.FC<StatusPillProps> = ({ status }) => {
  const norm = status.toLowerCase();
  let bg = 'rgba(148, 163, 184, 0.15)';
  let color = CONSTANTS.COLORS.textMuted;

  if (norm === 'en_route' || norm === 'assigned') {
    bg = 'rgba(56, 189, 248, 0.15)';
    color = CONSTANTS.COLORS.primary;
  } else if (norm === 'completed' || norm === 'synced') {
    bg = 'rgba(16, 185, 129, 0.15)';
    color = CONSTANTS.COLORS.success;
  } else if (norm === 'delayed') {
    bg = 'rgba(239, 68, 68, 0.15)';
    color = CONSTANTS.COLORS.danger;
  }

  return (
    <View style={[styles.pill, { backgroundColor: bg }]}>
      <Text style={[styles.text, { color }]}>{status.toUpperCase()}</Text>
    </View>
  );
};

const styles = StyleSheet.create({
  pill: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
    alignSelf: 'flex-start',
  },
  text: {
    fontSize: 11,
    fontWeight: '800',
    letterSpacing: 0.5,
  },
});
