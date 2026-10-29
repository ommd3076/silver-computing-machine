/**
 * Authoritative TypeScript contract definitions matching DebugLeaf driver mobile API schemas.
 */

export type SeverityLevel = 'moderate' | 'heavy';
export type DriverStatus = 'assigned' | 'en_route' | 'delayed' | 'completed';
export type JobStatus = 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
export type DecisionOutcome = 'KEEP' | 'PUBLISHED_NEW_ROUTE' | 'PROPOSE_REPLAN' | 'ALERT';

export interface ApiErrorEnvelope {
  error: {
    code: string;
    message: string;
    details?: Array<{ field: string; message: string }>;
  };
}

export interface PairingRequest {
  code: string;
}

export interface PairingResponse {
  token: string;
  expires_at: string;
  driver_id: string;
  vehicle_id: string;
  driver_name: string;
}

export interface DriverIdentity {
  driver_id: string;
  vehicle_id: string;
  driver_name: string;
  role: string;
  simulation_mode: boolean;
}

export interface StopInfo {
  id: string;
  name: string;
  coordinates: [number, number]; // [longitude, latitude]
  status: 'completed' | 'next' | 'pending';
}

export interface GeoJsonProperties {
  route_id: string;
  corridor_id: string;
  name: string;
  vehicle_id?: string;
  stop_ids?: string[];
  duration_seconds?: number;
  distance_metres?: number;
}

export interface GeoJsonFeature {
  type: 'Feature';
  geometry: {
    type: 'LineString';
    coordinates: Array<[number, number]>; // [[lon, lat], ...]
  };
  properties: GeoJsonProperties;
}

export interface DriverStateResponse {
  schema_version: string;
  driver_id: string;
  vehicle_id: string;
  route_id: string;
  corridor_id: string;
  route_version: number;
  manifest_revision: number;
  status: DriverStatus | string;
  estimated_duration_seconds: number;
  estimated_distance_metres: number;
  active_overlays: Record<string, number>;
  simulation_mode: boolean;
  data_provenance: string;
  geojson?: GeoJsonFeature | null;
  stops: StopInfo[];
  last_ack_version: number;
  updated_at: string;
}

export interface CongestionReportRequest {
  event_id: string;
  base_route_version: number;
  kind?: string;
  severity: SeverityLevel;
  note?: string;
}

export interface CongestionReportResponse {
  status: string;
  event_id: string;
  job_id: string;
  delay_applied_seconds: number;
  segment_id: string;
  decision: string;
  published_new_route: boolean;
  current_route_version: number;
}

export interface RoutePlanRequest {
  request_id: string;
  base_route_version: number;
}

export interface RoutePlanResponse {
  job_id: string;
  status: string;
  outcome: string;
  result: Record<string, any>;
}

export interface JobResponse {
  job_id: string;
  status: JobStatus;
  outcome?: string;
  result?: Record<string, any>;
}

export interface AcknowledgementRequest {
  route_version: number;
  client_timestamp?: string;
}

export interface AcknowledgementResponse {
  status: string;
  driver_id: string;
  version: number;
}
