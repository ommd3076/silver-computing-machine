/**
 * DriverHomeScreen: Primary operational cockpit for the driver.
 */

import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  SafeAreaView,
  ScrollView,
  TouchableOpacity,
  RefreshControl,
  Alert,
} from 'react-native';
import { useSession } from '../auth/SessionContext';
import { useDriverSync } from '../features/sync/useDriverSync';
import { NetworkBanner } from '../components/NetworkBanner';
import { StatusPill } from '../components/StatusPill';
import { RouteSummaryCard } from '../features/driver/RouteSummaryCard';
import { RouteMap } from '../features/map/RouteMap';
import { StopTimeline } from '../features/driver/StopTimeline';
import { CongestionModal } from '../features/driver/CongestionModal';
import { RouteUpdatedAlert } from './RouteUpdatedAlert';
import { PrimaryButton } from '../components/PrimaryButton';
import { submitPlanRouteRequest } from '../api/driver';
import { CONSTANTS } from '../config/constants';

export const DriverHomeScreen: React.FC = () => {
  const { identity, logout } = useSession();
  const {
    driverState,
    isOnline,
    isSyncing,
    error,
    routeUpdatedAlert,
    dismissAlert,
    refresh,
  } = useDriverSync(true);

  const [congestionModalVisible, setCongestionModalVisible] = useState<boolean>(false);
  const [isPlanning, setIsPlanning] = useState<boolean>(false);

  const handleManualPlanRoute = async () => {
    if (!driverState) return;
    setIsPlanning(true);
    try {
      const res = await submitPlanRouteRequest(driverState.route_version);
      Alert.alert(
        'Route Evaluation Complete',
        res.outcome === 'KEEP'
          ? 'Current corridor remains optimal under active conditions.'
          : `New route published: ${res.outcome}`
      );
      await refresh();
    } catch (err: any) {
      Alert.alert('Evaluation Failed', err.message || 'Server re-evaluation failed');
    } finally {
      setIsPlanning(false);
    }
  };

  return (
    <SafeAreaView style={styles.safeArea}>
      <NetworkBanner isOnline={isOnline} isSyncing={isSyncing} error={error} />

      <View style={styles.topBar}>
        <View style={styles.driverInfo}>
          <Text style={styles.driverName}>{identity?.driver_name || 'Driver Cockpit'}</Text>
          <View style={styles.vehicleRow}>
            <Text style={styles.vehicleId}>{identity?.vehicle_id || 'Vehicle 1'}</Text>
            <View style={styles.dot} />
            <StatusPill status={driverState?.status || 'en_route'} />
          </View>
        </View>

        <TouchableOpacity style={styles.logoutBtn} onPress={logout}>
          <Text style={styles.logoutText}>Logout</Text>
        </TouchableOpacity>
      </View>

      <ScrollView
        style={styles.scrollArea}
        contentContainerStyle={styles.scrollContent}
        refreshControl={
          <RefreshControl
            refreshing={isSyncing}
            onRefresh={refresh}
            tintColor={CONSTANTS.COLORS.primary}
          />
        }
      >
        {driverState ? (
          <>
            <RouteSummaryCard state={driverState} />

            <RouteMap
              geojson={driverState.geojson}
              stops={driverState.stops}
              activeOverlays={driverState.active_overlays}
            />

            <View style={styles.actionSection}>
              <Text style={styles.actionHeading}>Driver Actions</Text>
              <View style={styles.actionRow}>
                <PrimaryButton
                  title="Plan Route"
                  variant="secondary"
                  onPress={handleManualPlanRoute}
                  isLoading={isPlanning}
                  style={styles.planBtn}
                />
                <PrimaryButton
                  title="Report Congestion"
                  variant="danger"
                  onPress={() => setCongestionModalVisible(true)}
                  style={styles.reportBtn}
                />
              </View>
            </View>

            <StopTimeline stops={driverState.stops} />
          </>
        ) : (
          <View style={styles.loadingContainer}>
            <Text style={styles.loadingText}>Fetching authoritative route state...</Text>
          </View>
        )}
      </ScrollView>

      {/* Incident Modal */}
      {driverState && (
        <CongestionModal
          visible={congestionModalVisible}
          baseRouteVersion={driverState.route_version}
          onClose={() => setCongestionModalVisible(false)}
          onSuccess={refresh}
        />
      )}

      {/* Route Version Incremented Alert */}
      {routeUpdatedAlert && (
        <RouteUpdatedAlert
          visible={routeUpdatedAlert.visible}
          oldVersion={routeUpdatedAlert.oldVersion}
          newVersion={routeUpdatedAlert.newVersion}
          oldRouteName={routeUpdatedAlert.oldRouteName}
          newRouteName={routeUpdatedAlert.newRouteName}
          onAcknowledge={dismissAlert}
        />
      )}
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  safeArea: {
    flex: 1,
    backgroundColor: CONSTANTS.COLORS.background,
  },
  topBar: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: CONSTANTS.COLORS.surface,
    borderBottomWidth: 1,
    borderBottomColor: CONSTANTS.COLORS.surfaceBorder,
  },
  driverInfo: {
    flex: 1,
  },
  driverName: {
    fontSize: 16,
    fontWeight: '800',
    color: CONSTANTS.COLORS.textMain,
  },
  vehicleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 4,
  },
  vehicleId: {
    fontSize: 12,
    color: CONSTANTS.COLORS.textMuted,
    fontWeight: '600',
  },
  dot: {
    width: 4,
    height: 4,
    borderRadius: 2,
    backgroundColor: '#64748b',
    marginHorizontal: 8,
  },
  logoutBtn: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 8,
    backgroundColor: '#1e293b',
    borderWidth: 1,
    borderColor: '#334155',
  },
  logoutText: {
    fontSize: 12,
    fontWeight: '600',
    color: '#cbd5e1',
  },
  scrollArea: {
    flex: 1,
  },
  scrollContent: {
    padding: 16,
    paddingBottom: 40,
  },
  actionSection: {
    marginVertical: 10,
  },
  actionHeading: {
    fontSize: 14,
    fontWeight: '700',
    color: CONSTANTS.COLORS.textMuted,
    marginBottom: 8,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  actionRow: {
    flexDirection: 'row',
    gap: 12,
  },
  planBtn: {
    flex: 1,
  },
  reportBtn: {
    flex: 1,
  },
  loadingContainer: {
    paddingVertical: 60,
    alignItems: 'center',
  },
  loadingText: {
    fontSize: 14,
    color: CONSTANTS.COLORS.textMuted,
  },
});
