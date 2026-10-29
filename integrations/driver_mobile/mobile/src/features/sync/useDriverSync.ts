/**
 * Foreground synchronization hook for driver route state and server acknowledgements.
 */

import { useCallback, useEffect, useReducer, useRef } from 'react';
import { initialSyncState, syncReducer } from './syncReducer';
import { fetchDriverState, submitRouteAcknowledgement } from '../../api/driver';
import { CONSTANTS } from '../../config/constants';

export function useDriverSync(isAuthenticated: boolean) {
  const [state, dispatch] = useReducer(syncReducer, initialSyncState);
  const activePollRef = useRef<boolean>(false);
  const backoffRef = useRef<number>(CONSTANTS.SYNC_POLL_INTERVAL_MS);

  const pollState = useCallback(async () => {
    if (!isAuthenticated || activePollRef.current) return;
    activePollRef.current = true;
    dispatch({ type: 'SYNC_START' });

    try {
      const serverState = await fetchDriverState();
      dispatch({ type: 'SYNC_SUCCESS', payload: serverState });
      backoffRef.current = CONSTANTS.SYNC_POLL_INTERVAL_MS;

      // Auto-acknowledge rendered route version if not yet acknowledged
      if (serverState.last_ack_version < serverState.route_version) {
        try {
          const ack = await submitRouteAcknowledgement(serverState.route_version);
          dispatch({ type: 'ACK_SUCCESS', payload: ack.version });
        } catch {
          // Retry acknowledgement on subsequent sync tick
        }
      }
    } catch (err: any) {
      dispatch({
        type: 'SYNC_FAILURE',
        payload: err.message || 'Synchronization failure',
      });
      // Exponential backoff when offline
      backoffRef.current = Math.min(
        backoffRef.current * CONSTANTS.BACKOFF_MULTIPLIER,
        CONSTANTS.BACKOFF_MAX_MS
      );
    } finally {
      activePollRef.current = false;
    }
  }, [isAuthenticated]);

  useEffect(() => {
    if (!isAuthenticated) return;

    let timerId: any = null;

    const scheduleNext = () => {
      timerId = setTimeout(async () => {
        await pollState();
        scheduleNext();
      }, backoffRef.current);
    };

    // Immediate initial sync
    pollState().then(() => scheduleNext());

    return () => {
      if (timerId) clearTimeout(timerId);
    };
  }, [isAuthenticated, pollState]);

  return {
    driverState: state.driverState,
    isOnline: state.isOnline,
    isSyncing: state.isSyncing,
    error: state.error,
    routeUpdatedAlert: state.routeUpdatedAlert,
    dismissAlert: () => dispatch({ type: 'DISMISS_ALERT' }),
    refresh: pollState,
  };
}
