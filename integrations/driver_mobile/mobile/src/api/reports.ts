/**
 * Incident & Congestion reporting calls.
 */

import { apiFetch, generateRequestId } from './client';
import { CongestionReportRequest, CongestionReportResponse, SeverityLevel } from './types';

export async function submitCongestionReport(
  baseRouteVersion: number,
  severity: SeverityLevel,
  note: string = ''
): Promise<CongestionReportResponse> {
  const payload: CongestionReportRequest = {
    event_id: generateRequestId(),
    base_route_version: baseRouteVersion,
    kind: 'congestion',
    severity,
    note,
  };
  return apiFetch<CongestionReportResponse>('reports', {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}
