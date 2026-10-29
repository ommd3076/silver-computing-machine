/**
 * ProvenanceBadge displaying accurate data attribution.
 * Explicitly distinguishes synthetic simulation from trained inference models.
 */

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';

interface ProvenanceBadgeProps {
  provenance: string;
  simulationMode?: boolean;
}

export const ProvenanceBadge: React.FC<ProvenanceBadgeProps> = ({
  provenance,
  simulationMode = true,
}) => {
  const displayLabel = provenance === 'synthetic_delhivery_v1'
    ? 'SIMULATED CORRIDOR (DELHIVERY V1)'
    : provenance.toUpperCase();

  return (
    <View style={styles.container}>
      <View style={styles.indicator} />
      <Text style={styles.text}>
        {displayLabel} {simulationMode ? '• SYNTHETIC PROGRESSION' : ''}
      </Text>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: 'rgba(56, 189, 248, 0.08)',
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: 'rgba(56, 189, 248, 0.2)',
  },
  indicator: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: '#38bdf8',
    marginRight: 6,
  },
  text: {
    fontSize: 10,
    fontWeight: '700',
    color: '#38bdf8',
    letterSpacing: 0.5,
  },
});
