/**
 * Driver operational calls: state fetch, acknowledgements, plan requests.
 */

import { apiFetch, generateRequestId } from './client';
import {
  AcknowledgementRequest,
  AcknowledgementResponse,
  DriverStateResponse,
  RoutePlanRequest,
  RoutePlanResponse,
} from './types';

export async function fetchDriverState(): Promise<DriverStateResponse> {
  return apiFetch<DriverStateResponse>('state', {
    method: 'GET',
  });
}

export async function submitRouteAcknowledgement(
  routeVersion: number
): Promise<AcknowledgementResponse> {
  const payload: AcknowledgementRequest = {
    route_version: routeVersion,
    client_timestamp: new Date().toISOString(),
  };
  return apiFetch<AcknowledgementResponse>('acknowledgements', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function submitPlanRouteRequest(
  baseRouteVersion: number
): Promise<RoutePlanResponse> {
  const payload: RoutePlanRequest = {
    request_id: generateRequestId(),
    base_route_version: baseRouteVersion,
  };
  return apiFetch<RoutePlanResponse>('route-requests', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}
