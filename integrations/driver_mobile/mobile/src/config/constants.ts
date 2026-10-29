/**
 * Operational constants for driver sync and networking.
 */

export const CONSTANTS = {
  // Foreground synchronization cadence: 1.5 - 2.0s as specified
  SYNC_POLL_INTERVAL_MS: 1500,

  // Offline exponential backoff
  BACKOFF_INITIAL_MS: 1000,
  BACKOFF_MAX_MS: 8000,
  BACKOFF_MULTIPLIER: 1.5,

  // Timeouts
  SESSION_CHECK_TIMEOUT_MS: 4000,
  MUTATION_TIMEOUT_MS: 8000,

  // UI styling tokens
  COLORS: {
    background: '#090d16',
    surface: '#131b2e',
    surfaceBorder: '#23304c',
    primary: '#38bdf8',
    primaryDark: '#0284c7',
    textMain: '#f8fafc',
    textMuted: '#94a3b8',
    success: '#10b981',
    warning: '#f59e0b',
    danger: '#ef4444',
  },
};
