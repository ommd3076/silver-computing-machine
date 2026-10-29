/**
 * RouteSummaryCard component showing trip metrics, version, and provenance.
 */

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { DriverStateResponse } from '../../api/types';
import { CONSTANTS } from '../../config/constants';
import { ProvenanceBadge } from '../../components/ProvenanceBadge';

interface RouteSummaryCardProps {
  state: DriverStateResponse;
}

export const RouteSummaryCard: React.FC<RouteSummaryCardProps> = ({ state }) => {
  const durationMin = Math.round(state.estimated_duration_seconds / 60);
  const distanceKm = (state.estimated_distance_metres / 1000).toFixed(1);
  const isSynced = state.last_ack_version >= state.route_version;

  return (
    <View style={styles.card}>
      <View style={styles.statsRow}>
        <View style={styles.statBox}>
          <Text style={styles.statValue}>{durationMin} min</Text>
          <Text style={styles.statLabel}>Est. Duration</Text>
        </View>

        <View style={styles.statDivider} />

        <View style={styles.statBox}>
          <Text style={styles.statValue}>{distanceKm} km</Text>
          <Text style={styles.statLabel}>Total Distance</Text>
        </View>

        <View style={styles.statDivider} />

        <View style={styles.statBox}>
          <Text style={styles.statValue}>Rev {state.route_version}</Text>
          <Text style={styles.statLabel}>
            {isSynced ? 'Synced' : `Acking v${state.last_ack_version}`}
          </Text>
        </View>
      </View>

      <View style={styles.badgeRow}>
        <ProvenanceBadge provenance={state.data_provenance} simulationMode={state.simulation_mode} />
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: CONSTANTS.COLORS.surface,
    borderRadius: 14,
    padding: 16,
    marginVertical: 8,
    borderWidth: 1,
    borderColor: CONSTANTS.COLORS.surfaceBorder,
  },
  statsRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  statBox: {
    flex: 1,
    alignItems: 'center',
  },
  statValue: {
    fontSize: 18,
    fontWeight: '800',
    color: CONSTANTS.COLORS.textMain,
  },
  statLabel: {
    fontSize: 11,
    color: CONSTANTS.COLORS.textMuted,
    marginTop: 2,
  },
  statDivider: {
    width: 1,
    height: 28,
    backgroundColor: CONSTANTS.COLORS.surfaceBorder,
  },
  badgeRow: {
    marginTop: 12,
    paddingTop: 10,
    borderTopWidth: 1,
    borderTopColor: CONSTANTS.COLORS.surfaceBorder,
    alignItems: 'center',
  },
});
