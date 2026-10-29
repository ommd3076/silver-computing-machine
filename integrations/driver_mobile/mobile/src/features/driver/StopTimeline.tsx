/**
 * StopTimeline component rendering delivery progression cards.
 */

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { StopInfo } from '../../api/types';
import { CONSTANTS } from '../../config/constants';

interface StopTimelineProps {
  stops: StopInfo[];
}

export const StopTimeline: React.FC<StopTimelineProps> = ({ stops }) => {
  if (!stops || stops.length === 0) {
    return null;
  }

  return (
    <View style={styles.container}>
      <Text style={styles.heading}>Delivery Stops Progression</Text>
      {stops.map((stop, idx) => {
        const isDone = stop.status === 'completed';
        const isNext = stop.status === 'next';
        const isLast = idx === stops.length - 1;

        return (
          <View key={`timeline-${stop.id}-${idx}`} style={styles.row}>
            <View style={styles.indicatorCol}>
              <View
                style={[
                  styles.node,
                  isDone && styles.nodeDone,
                  isNext && styles.nodeNext,
                ]}
              >
                <Text style={styles.nodeText}>{isDone ? '✓' : idx + 1}</Text>
              </View>
              {!isLast && <View style={[styles.line, isDone && styles.lineDone]} />}
            </View>

            <View style={[styles.card, isNext && styles.cardActive]}>
              <View style={styles.cardHeader}>
                <Text style={[styles.stopName, isDone && styles.stopNameDone]}>
                  {stop.name}
                </Text>
                <View
                  style={[
                    styles.statusPill,
                    isDone && styles.statusPillDone,
                    isNext && styles.statusPillNext,
                  ]}
                >
                  <Text
                    style={[
                      styles.statusText,
                      isDone && styles.statusTextDone,
                      isNext && styles.statusTextNext,
                    ]}
                  >
                    {isNext ? 'CURRENT TARGET' : stop.status.toUpperCase()}
                  </Text>
                </View>
              </View>
              <Text style={styles.stopCoords}>
                WGS84: {stop.coordinates[0].toFixed(4)}°E, {stop.coordinates[1].toFixed(4)}°N
              </Text>
            </View>
          </View>
        );
      })}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    marginVertical: 10,
  },
  heading: {
    fontSize: 16,
    fontWeight: '700',
    color: CONSTANTS.COLORS.textMain,
    marginBottom: 12,
  },
  row: {
    flexDirection: 'row',
  },
  indicatorCol: {
    alignItems: 'center',
    width: 32,
  },
  node: {
    width: 24,
    height: 24,
    borderRadius: 12,
    backgroundColor: '#334155',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1,
  },
  nodeDone: {
    backgroundColor: CONSTANTS.COLORS.success,
  },
  nodeNext: {
    backgroundColor: CONSTANTS.COLORS.primary,
  },
  nodeText: {
    color: '#ffffff',
    fontSize: 11,
    fontWeight: '700',
  },
  line: {
    width: 2,
    flex: 1,
    backgroundColor: '#334155',
    marginVertical: 2,
  },
  lineDone: {
    backgroundColor: CONSTANTS.COLORS.success,
  },
  card: {
    flex: 1,
    backgroundColor: CONSTANTS.COLORS.surface,
    borderRadius: 10,
    padding: 12,
    marginLeft: 10,
    marginBottom: 10,
    borderWidth: 1,
    borderColor: CONSTANTS.COLORS.surfaceBorder,
  },
  cardActive: {
    borderColor: CONSTANTS.COLORS.primary,
    backgroundColor: '#11223b',
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  stopName: {
    fontSize: 14,
    fontWeight: '600',
    color: CONSTANTS.COLORS.textMain,
    flex: 1,
  },
  stopNameDone: {
    color: CONSTANTS.COLORS.textMuted,
    textDecorationLine: 'line-through',
  },
  stopCoords: {
    fontSize: 11,
    color: CONSTANTS.COLORS.textMuted,
    marginTop: 4,
    fontFamily: 'monospace',
  },
  statusPill: {
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 4,
    backgroundColor: 'rgba(255,255,255,0.06)',
  },
  statusPillDone: {
    backgroundColor: 'rgba(16, 185, 129, 0.15)',
  },
  statusPillNext: {
    backgroundColor: 'rgba(56, 189, 248, 0.2)',
  },
  statusText: {
    fontSize: 10,
    fontWeight: '700',
    color: CONSTANTS.COLORS.textMuted,
  },
  statusTextDone: {
    color: CONSTANTS.COLORS.success,
  },
  statusTextNext: {
    color: CONSTANTS.COLORS.primary,
  },
});
