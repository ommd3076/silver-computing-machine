/**
 * Session API calls: pairing, revocation, driver identity.
 */

import { apiFetch } from './client';
import { DriverIdentity, PairingRequest, PairingResponse } from './types';
import { clearSessionToken, saveSessionToken } from '../auth/tokenStorage';

export async function pairDevice(code: string): Promise<PairingResponse> {
  const payload: PairingRequest = { code: code.trim().toUpperCase() };
  const res = await apiFetch<PairingResponse>('sessions', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
  if (res.token) {
    await saveSessionToken(res.token);
  }
  return res;
}

export async function logoutDevice(): Promise<void> {
  try {
    await apiFetch<{ status: string }>('sessions/current', {
      method: 'DELETE',
    });
  } finally {
    await clearSessionToken();
  }
}

export async function fetchDriverIdentity(): Promise<DriverIdentity> {
  return apiFetch<DriverIdentity>('me', {
    method: 'GET',
  });
}
