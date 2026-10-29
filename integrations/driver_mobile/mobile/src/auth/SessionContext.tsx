/**
 * React Context for Driver Session lifecycle and state persistence.
 */

import React, { createContext, useContext, useEffect, useState } from 'react';
import { clearSessionToken, getSessionToken } from './tokenStorage';
import { fetchDriverIdentity, logoutDevice, pairDevice } from '../api/session';
import { setUnauthorizedHandler } from '../api/client';
import { DriverIdentity } from '../api/types';

interface SessionContextValue {
  identity: DriverIdentity | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  login: (code: string) => Promise<void>;
  logout: () => Promise<void>;
  clearError: () => void;
}

const SessionContext = createContext<SessionContextValue | undefined>(undefined);

export const SessionProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [identity, setIdentity] = useState<DriverIdentity | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setUnauthorizedHandler(() => {
      setIdentity(null);
      clearSessionToken();
    });

    const initSession = async () => {
      try {
        const token = await getSessionToken();
        if (token) {
          const id = await fetchDriverIdentity();
          setIdentity(id);
        }
      } catch {
        await clearSessionToken();
        setIdentity(null);
      } finally {
        setIsLoading(false);
      }
    };

    initSession();
  }, []);

  const login = async (code: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const resp = await pairDevice(code);
      setIdentity({
        driver_id: resp.driver_id,
        vehicle_id: resp.vehicle_id,
        driver_name: resp.driver_name,
        role: 'driver',
        simulation_mode: true,
      });
    } catch (err: any) {
      setError(err.message || 'Pairing failed. Please check your code.');
      throw err;
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    setIsLoading(true);
    try {
      await logoutDevice();
    } finally {
      setIdentity(null);
      setIsLoading(false);
    }
  };

  return (
    <SessionContext.Provider
      value={{
        identity,
        isAuthenticated: !!identity,
        isLoading,
        error,
        login,
        logout,
        clearError: () => setError(null),
      }}
    >
      {children}
    </SessionContext.Provider>
  );
};

export function useSession(): SessionContextValue {
  const context = useContext(SessionContext);
  if (!context) {
    throw new Error('useSession must be used within a SessionProvider');
  }
  return context;
}
