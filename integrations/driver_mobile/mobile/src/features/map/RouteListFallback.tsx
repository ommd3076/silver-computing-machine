/**
 * List-first fallback view for stops, corridors, and road segments.
 */

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { StopInfo } from '../../api/types';
import { CONSTANTS } from '../../config/constants';

interface RouteListFallbackProps {
  stops: StopInfo[];
  routeName?: string;
  corridorId?: string;
}

export const RouteListFallback: React.FC<RouteListFallbackProps> = ({
  stops,
  routeName,
  corridorId,
}) => {
  return (
    <View style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>Route Corridor Stops</Text>
        {routeName && <Text style={styles.routeName}>{routeName}</Text>}
        {corridorId && <Text style={styles.corridorId}>Corridor: {corridorId}</Text>}
      </View>

      <View style={styles.list}>
        {stops.map((stop, idx) => {
          const isDone = stop.status === 'completed';
          const isNext = stop.status === 'next';
          return (
            <View key={`${stop.id}-${idx}`} style={styles.item}>
              <View style={[styles.badge, isDone && styles.badgeDone, isNext && styles.badgeNext]}>
                <Text style={styles.badgeText}>{idx + 1}</Text>
              </View>
              <View style={styles.info}>
                <Text style={[styles.name, isDone && styles.nameDone]}>{stop.name}</Text>
                <Text style={styles.coords}>
                  [{stop.coordinates[0].toFixed(4)}, {stop.coordinates[1].toFixed(4)}]
                </Text>
              </View>
              <View style={styles.statusBox}>
                <Text style={[styles.statusText, isDone && styles.statusDone, isNext && styles.statusNext]}>
                  {stop.status.toUpperCase()}
                </Text>
              </View>
            </View>
          );
        })}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    backgroundColor: CONSTANTS.COLORS.surface,
    borderRadius: 12,
    padding: 16,
    marginVertical: 8,
    borderWidth: 1,
    borderColor: CONSTANTS.COLORS.surfaceBorder,
  },
  header: {
    marginBottom: 12,
  },
  title: {
    fontSize: 16,
    fontWeight: '700',
    color: CONSTANTS.COLORS.textMain,
  },
  routeName: {
    fontSize: 14,
    color: CONSTANTS.COLORS.primary,
    marginTop: 2,
  },
  corridorId: {
    fontSize: 12,
    color: CONSTANTS.COLORS.textMuted,
    marginTop: 2,
  },
  list: {
    marginTop: 8,
  },
  item: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderBottomColor: CONSTANTS.COLORS.surfaceBorder,
  },
  badge: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: '#334155',
    alignItems: 'center',
    justifyContent: 'center',
    marginRight: 12,
  },
  badgeDone: {
    backgroundColor: CONSTANTS.COLORS.success,
  },
  badgeNext: {
    backgroundColor: CONSTANTS.COLORS.primary,
  },
  badgeText: {
    color: '#ffffff',
    fontSize: 13,
    fontWeight: '700',
  },
  info: {
    flex: 1,
  },
  name: {
    fontSize: 14,
    fontWeight: '600',
    color: CONSTANTS.COLORS.textMain,
  },
  nameDone: {
    color: CONSTANTS.COLORS.textMuted,
    textDecorationLine: 'line-through',
  },
  coords: {
    fontSize: 11,
    color: CONSTANTS.COLORS.textMuted,
    marginTop: 2,
  },
  statusBox: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
    backgroundColor: 'rgba(255,255,255,0.05)',
  },
  statusText: {
    fontSize: 11,
    fontWeight: '700',
    color: CONSTANTS.COLORS.textMuted,
  },
  statusDone: {
    color: CONSTANTS.COLORS.success,
  },
  statusNext: {
    color: CONSTANTS.COLORS.primary,
  },
});
