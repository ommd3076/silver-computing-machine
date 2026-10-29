/**
 * Mobile runtime environment configuration.
 */

export const ENV = {
  API_BASE_URL: process.env.EXPO_PUBLIC_API_URL || 'http://172.80.1.249:8000/api/v1/demo',
  REQUEST_TIMEOUT_MS: 6000,
  APP_VERSION: '1.0.0',
};
