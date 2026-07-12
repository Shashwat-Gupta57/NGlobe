/**
 * NetworkGlobe TypeScript Type Definitions
 *
 * These interfaces mirror the canonical Python NetworkEvent model exactly.
 * Any changes to backend/models.py must be reflected here.
 */

/** Canonical event representing a single intercepted network request. */
export interface NetworkEvent {
  // Core identity
  id: number | null;
  timestamp: string; // ISO 8601 UTC

  // Request metadata
  hostname: string;
  destination_ip: string;
  port: number;
  protocol: string;
  method: string | null;
  path: string | null;
  status_code: number | null;

  // GeoIP enrichment
  country_code: string | null;
  country_name: string | null;
  city: string | null;
  latitude: number | null;
  longitude: number | null;
  organization: string | null;
  asn: number | null;

  // Connection metadata
  tls_version: string | null;
  bytes_sent: number;
  bytes_received: number;
  latency_ms: number | null;

  // Future: Blocking (V2+)
  blocked: boolean;
  block_reason: string | null;
  rule_id: number | null;

  // Future: Process detection (V3+)
  process_name: string | null;

  // Future: Tagging
  tags: string[];
}

/** WebSocket message types from server → client */
export type WsMessageType = 'request' | 'request_batch' | 'status' | 'dropped' | 'shutdown';

/** Individual request message */
export interface WsRequestMessage {
  type: 'request';
  data: NetworkEvent;
}

/** Batched request message (high throughput) */
export interface WsRequestBatchMessage {
  type: 'request_batch';
  data: NetworkEvent[];
}

/** System status message */
export interface WsStatusMessage {
  type: 'status';
  data: {
    proxy_running: boolean;
    total_requests: number;
    requests_per_minute: number;
    active_connections: number;
    uptime_seconds: number;
  };
}

/** Dropped events warning */
export interface WsDroppedMessage {
  type: 'dropped';
  count: number;
}

/** Shutdown notification */
export interface WsShutdownMessage {
  type: 'shutdown';
}

/** Union of all WebSocket messages */
export type WsMessage =
  | WsRequestMessage
  | WsRequestBatchMessage
  | WsStatusMessage
  | WsDroppedMessage
  | WsShutdownMessage;

/** Filter state for the sidebar */
export interface FilterState {
  search: string;
  countries: string[];
  organizations: string[];
  hostnames: string[];
}

/** Health check response */
export interface HealthResponse {
  status: string;
  version: string;
  uptime_seconds: number;
  proxy_running: boolean;
  total_requests: number;
}

/** Analytics summary */
export interface AnalyticsSummary {
  total_requests: number;
  unique_countries: number;
  unique_organizations: number;
  total_bytes_sent: number;
  total_bytes_received: number;
  requests_per_minute: number;
  uptime_seconds: number;
}

/** Country analytics entry */
export interface CountryStats {
  country_code: string;
  country_name: string;
  count: number;
  bytes_total: number;
}

/** Organization analytics entry */
export interface OrgStats {
  organization: string;
  count: number;
  bytes_total: number;
}

/** Hostname analytics entry */
export interface HostnameStats {
  hostname: string;
  count: number;
  bytes_total: number;
  last_seen: string;
}

/** Request rate data point */
export interface RateDataPoint {
  timestamp: string;
  count: number;
}
