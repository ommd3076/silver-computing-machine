/**
 * NetworkBanner component displaying online / offline / syncing status.
 */

import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { CONSTANTS } from '../config/constants';

interface NetworkBannerProps {
  isOnline: boolean;
  isSyncing: boolean;
  error?: string | null;
}

export const NetworkBanner: React.FC<NetworkBannerProps> = ({
  isOnline,
  isSyncing,
  error,
}) => {
  if (isOnline && !isSyncing && !error) {
    return null;
  }

  if (!isOnline) {
    return (
      <View style={[styles.banner, styles.bannerOffline]}>
        <Text style={styles.textOffline}>
          OFFLINE — Reconnecting to Legion Host ({error || 'Retrying...'})
        </Text>
      </View>
    );
  }

  if (isSyncing) {
    return (
      <View style={[styles.banner, styles.bannerSyncing]}>
        <Text style={styles.textSyncing}>Synchronizing with Server...</Text>
      </View>
    );
  }

  return null;
};

const styles = StyleSheet.create({
  banner: {
    paddingVertical: 6,
    paddingHorizontal: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  bannerOffline: {
    backgroundColor: '#dc2626',
  },
  bannerSyncing: {
    backgroundColor: 'rgba(56, 189, 248, 0.2)',
  },
  textOffline: {
    color: '#ffffff',
    fontSize: 11,
    fontWeight: '700',
  },
  textSyncing: {
    color: CONSTANTS.COLORS.primary,
    fontSize: 11,
    fontWeight: '600',
  },
});
