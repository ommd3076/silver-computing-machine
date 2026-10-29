/**
 * Centralized API client with automatic token injection, timeout, and sanitized error handling.
 */

import { ENV } from '../config/env';
import { getSessionToken } from '../auth/tokenStorage';
import { ApiErrorEnvelope } from './types';

export class ApiClientError extends Error {
  public code: string;
  public status: number;
  public details?: Array<{ field: string; message: string }>;

  constructor(status: number, code: string, message: string, details?: Array<{ field: string; message: string }>) {
    super(message);
    this.name = 'ApiClientError';
    this.status = status;
    this.code = code;
    this.details = details;
  }
}

let unauthorizedHandler: (() => void) | null = null;

export function setUnauthorizedHandler(handler: () => void): void {
  unauthorizedHandler = handler;
}

export function generateRequestId(): string {
  return 'req_' + Math.random().toString(36).substring(2, 11) + Date.now().toString(36);
}

export async function apiFetch<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = await getSessionToken();
  const requestId = generateRequestId();

  const url = endpoint.startsWith('http')
    ? endpoint
    : `${ENV.API_BASE_URL.replace(/\/+$/, '')}/${endpoint.replace(/^\/+/, '')}`;

  const headers: Record<string, string> = {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
    'X-Request-Id': requestId,
    ...(options.headers as Record<string, string> || {}),
  };

  if (token && !headers['Authorization']) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), ENV.REQUEST_TIMEOUT_MS);

  try {
    const response = await fetch(url, {
      ...options,
      headers,
      signal: controller.signal,
    });

    clearTimeout(timeoutId);

    const text = await response.text();
    let data: any = null;
    if (text) {
      try {
        data = JSON.parse(text);
      } catch {
        data = { raw: text };
      }
    }

    if (!response.ok) {
      if (response.status === 401 && unauthorizedHandler) {
        unauthorizedHandler();
      }

      const errorEnvelope = data as ApiErrorEnvelope;
      const code = errorEnvelope?.error?.code || `HTTP_${response.status}`;
      const message = errorEnvelope?.error?.message || 'Server request failed';
      const details = errorEnvelope?.error?.details;

      throw new ApiClientError(response.status, code, message, details);
    }

    return data as T;
  } catch (err: any) {
    clearTimeout(timeoutId);
    if (err instanceof ApiClientError) {
      throw err;
    }
    if (err.name === 'AbortError') {
      throw new ApiClientError(408, 'timeout', 'Request to server timed out');
    }
    throw new ApiClientError(0, 'network_error', err.message || 'Unable to connect to Legion host server');
  }
}
