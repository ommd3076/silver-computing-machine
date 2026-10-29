/**
 * Secure token storage adapter.
 * Uses expo-secure-store with in-memory fallback for environments where secure store is unavailable.
 */

let memoryToken: string | null = null;

const TOKEN_KEY = 'debugleaf_driver_session_bearer';

export async function saveSessionToken(token: string): Promise<void> {
  memoryToken = token;
  try {
    const SecureStore = await import('expo-secure-store');
    if (SecureStore && typeof SecureStore.setItemAsync === 'function') {
      await SecureStore.setItemAsync(TOKEN_KEY, token);
    }
  } catch {
    // Retain in memory when native secure store is unavailable
  }
}

export async function getSessionToken(): Promise<string | null> {
  if (memoryToken) return memoryToken;
  try {
    const SecureStore = await import('expo-secure-store');
    if (SecureStore && typeof SecureStore.getItemAsync === 'function') {
      const stored = await SecureStore.getItemAsync(TOKEN_KEY);
      if (stored) {
        memoryToken = stored;
        return stored;
      }
    }
  } catch {
    // Return memory fallback
  }
  return memoryToken;
}

export async function clearSessionToken(): Promise<void> {
  memoryToken = null;
  try {
    const SecureStore = await import('expo-secure-store');
    if (SecureStore && typeof SecureStore.deleteItemAsync === 'function') {
      await SecureStore.deleteItemAsync(TOKEN_KEY);
    }
  } catch {
    // Memory cleared
  }
}
