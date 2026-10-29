/**
 * Reducer for state synchronization, route version transitions, and alerts.
 */

import { DriverStateResponse } from '../../api/types';

export interface SyncState {
  driverState: DriverStateResponse | null;
  isOnline: boolean;
  isSyncing: boolean;
  error: string | null;
  routeUpdatedAlert: {
    visible: boolean;
    oldVersion: number;
    newVersion: number;
    oldRouteName?: string;
    newRouteName?: string;
  } | null;
}

export type SyncAction =
  | { type: 'SYNC_START' }
  | { type: 'SYNC_SUCCESS'; payload: DriverStateResponse }
  | { type: 'SYNC_FAILURE'; payload: string }
  | { type: 'DISMISS_ALERT' }
  | { type: 'ACK_SUCCESS'; payload: number };

export const initialSyncState: SyncState = {
  driverState: null,
  isOnline: true,
  isSyncing: false,
  error: null,
  routeUpdatedAlert: null,
};

export function syncReducer(state: SyncState, action: SyncAction): SyncState {
  switch (action.type) {
    case 'SYNC_START':
      return { ...state, isSyncing: true, error: null };

    case 'SYNC_SUCCESS': {
      const newState = action.payload;
      const current = state.driverState;

      // Monotonic version guard: never regress to a lower route version
      if (current && newState.route_version < current.route_version) {
        return { ...state, isSyncing: false };
      }

      // Check if server published a new route revision
      let alert = state.routeUpdatedAlert;
      if (current && newState.route_version > current.route_version) {
        alert = {
          visible: true,
          oldVersion: current.route_version,
          newVersion: newState.route_version,
          oldRouteName: current.geojson?.properties?.name || current.route_id,
          newRouteName: newState.geojson?.properties?.name || newState.route_id,
        };
      }

      return {
        ...state,
        driverState: newState,
        isOnline: true,
        isSyncing: false,
        error: null,
        routeUpdatedAlert: alert,
      };
    }

    case 'SYNC_FAILURE':
      return {
        ...state,
        isOnline: false,
        isSyncing: false,
        error: action.payload,
      };

    case 'ACK_SUCCESS': {
      if (!state.driverState) return state;
      return {
        ...state,
        driverState: {
          ...state.driverState,
          last_ack_version: Math.max(state.driverState.last_ack_version, action.payload),
        },
      };
    }

    case 'DISMISS_ALERT':
      return {
        ...state,
        routeUpdatedAlert: null,
      };

    default:
      return state;
  }
}
