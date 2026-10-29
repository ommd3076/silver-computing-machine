/**
 * RouteMap component displaying polyline geometry, waypoints, and incident indicators.
 */

import React, { useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { GeoJsonFeature, StopInfo } from '../../api/types';
import { CONSTANTS } from '../../config/constants';
import { RouteListFallback } from './RouteListFallback';

interface RouteMapProps {
  geojson?: GeoJsonFeature | null;
  stops: StopInfo[];
  activeOverlays?: Record<string, number>;
}

export const RouteMap: React.FC<RouteMapProps> = ({
  geojson,
  stops,
  activeOverlays = {},
}) => {
  const [showList, setShowList] = useState(false);

  const coordinates = geojson?.geometry?.coordinates || [];
  const routeName = geojson?.properties?.name || 'Assigned Route';
  const corridorId = geojson?.properties?.corridor_id || 'unknown';
  const hasIncident = Object.keys(activeOverlays).length > 0;

  return (
    <View style={styles.card}>
      <View style={styles.topRow}>
        <View style={styles.titleGroup}>
          <Text style={styles.title}>{routeName}</Text>
          <Text style={styles.subTitle}>{corridorId}</Text>
        </View>
        <TouchableOpacity
          style={styles.toggleButton}
          onPress={() => setShowList(!showList)}
        >
          <Text style={styles.toggleText}>{showList ? 'Map View' : 'Stops List'}</Text>
        </TouchableOpacity>
      </View>

      {hasIncident && (
        <View style={styles.incidentBanner}>
          <Text style={styles.incidentText}>
            ACTIVE CONGESTION OVERLAY APPLIED (+{Math.max(...Object.values(activeOverlays))}s)
          </Text>
        </View>
      )}

      {showList ? (
        <RouteListFallback stops={stops} routeName={routeName} corridorId={corridorId} />
      ) : (
        <View style={styles.mapCanvas}>
          {/* Visual Route Vector Representation */}
          <View style={styles.polylineTrack}>
            {coordinates.slice(0, 5).map((pt, i) => (
              <View key={`node-${i}`} style={styles.waypointRow}>
                <View style={[styles.waypointDot, i === 0 && styles.depotDot]} />
                <Text style={styles.waypointCoord}>
                  Waypoint {i + 1}: {pt[0].toFixed(4)}°E, {pt[1].toFixed(4)}°N
                </Text>
              </View>
            ))}
            {coordinates.length > 5 && (
              <Text style={styles.moreWaypoints}>
                + {coordinates.length - 5} additional road segments rendered
              </Text>
            )}
          </View>
          <View style={styles.legendRow}>
            <View style={styles.legendItem}>
              <View style={[styles.dot, { backgroundColor: CONSTANTS.COLORS.primary }]} />
              <Text style={styles.legendLabel}>Active Route</Text>
            </View>
            <View style={styles.legendItem}>
              <View style={[styles.dot, { backgroundColor: CONSTANTS.COLORS.success }]} />
              <Text style={styles.legendLabel}>Depot Hub</Text>
            </View>
            {hasIncident && (
              <View style={styles.legendItem}>
                <View style={[styles.dot, { backgroundColor: CONSTANTS.COLORS.danger }]} />
                <Text style={styles.legendLabel}>Congestion Zone</Text>
              </View>
            )}
          </View>
        </View>
      )}
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
  topRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  titleGroup: {
    flex: 1,
  },
  title: {
    fontSize: 16,
    fontWeight: '700',
    color: CONSTANTS.COLORS.textMain,
  },
  subTitle: {
    fontSize: 12,
    color: CONSTANTS.COLORS.textMuted,
    marginTop: 2,
  },
  toggleButton: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 8,
    backgroundColor: 'rgba(56, 189, 248, 0.15)',
    borderWidth: 1,
    borderColor: 'rgba(56, 189, 248, 0.3)',
  },
  toggleText: {
    fontSize: 12,
    fontWeight: '600',
    color: CONSTANTS.COLORS.primary,
  },
  incidentBanner: {
    backgroundColor: 'rgba(239, 68, 68, 0.15)',
    borderWidth: 1,
    borderColor: 'rgba(239, 68, 68, 0.4)',
    borderRadius: 8,
    padding: 8,
    marginBottom: 12,
  },
  incidentText: {
    fontSize: 11,
    fontWeight: '700',
    color: CONSTANTS.COLORS.danger,
    textAlign: 'center',
  },
  mapCanvas: {
    backgroundColor: '#0c1322',
    borderRadius: 10,
    padding: 16,
    borderWidth: 1,
    borderColor: '#1e293b',
  },
  polylineTrack: {
    marginBottom: 12,
  },
  waypointRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginVertical: 4,
  },
  waypointDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: CONSTANTS.COLORS.primary,
    marginRight: 10,
  },
  depotDot: {
    backgroundColor: CONSTANTS.COLORS.success,
  },
  waypointCoord: {
    fontSize: 12,
    fontFamily: 'monospace',
    color: '#cbd5e1',
  },
  moreWaypoints: {
    fontSize: 11,
    color: CONSTANTS.COLORS.textMuted,
    marginTop: 6,
    fontStyle: 'italic',
  },
  legendRow: {
    flexDirection: 'row',
    marginTop: 12,
    paddingTop: 10,
    borderTopWidth: 1,
    borderTopColor: '#1e293b',
  },
  legendItem: {
    flexDirection: 'row',
    alignItems: 'center',
    marginRight: 16,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    marginRight: 6,
  },
  legendLabel: {
    fontSize: 11,
    color: CONSTANTS.COLORS.textMuted,
  },
});
