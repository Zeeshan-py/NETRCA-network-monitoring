export type Envelope<T> = { success: true; data: T; message?: string };

export type ApiHealth = { api: "UP" };
export type NetworkStatus = {
  available: boolean;
  state: "DISABLED" | "UNAVAILABLE" | "STOPPED" | "STARTING" | "RUNNING" | "STOPPING" | "RESETTING" | "FAILED";
  topology_name: string;
  started_at: string | null;
  device_count: number;
  link_count: number;
  operation: string | null;
};
export type TopologyNode = {
  id: string;
  name?: string;
  device_type: string;
  status?: string;
  state?: string;
  ip_address?: string | null;
};
export type TopologyLink = {
  id: string;
  source?: string;
  destination?: string;
  source_device_id?: string;
  destination_device_id?: string;
  status: string;
  interface_source?: string | null;
  interface_destination?: string | null;
};
export type Topology = { topology_name?: string; nodes: TopologyNode[]; links: TopologyLink[]; components?: string[][] };
export type Monitoring = {
  observed_at: string;
  topology_name: string;
  network_state: string;
  collection_status: string;
  devices: Array<{ name: string; device_type: string; interfaces: Array<{ name: string; status: string; rx_errors: number | null; tx_errors: number | null }> }>;
  links: Array<{ source: string; destination: string; status: string }>;
  errors: string[];
};
export type Page<T> = { data: T[]; pagination: { page: number; limit: number; total: number; pages: number } };
export type EvidenceRecord = Record<string, unknown> & { id: string; timestamp?: string; detected_at?: string; severity?: string; event_type?: string; metric_type?: string; message?: string; name?: string; status?: string };
export type Incident = { id: string; title: string; description?: string | null; severity: string; status: string; start_time: string; end_time?: string | null };
export type IncidentDetail = Incident & { events: EvidenceRecord[]; anomalies: EvidenceRecord[] };

export class ApiError extends Error {
  constructor(message: string, readonly status?: number, readonly code?: string) {
    super(message);
    this.name = "ApiError";
  }
}

function apiBaseUrl(): string {
  const configured = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();
  if (!configured) throw new ApiError("Backend URL is not configured. Set NEXT_PUBLIC_API_BASE_URL in the frontend environment.");
  let url: URL;
  try { url = new URL(configured); } catch { throw new ApiError("Backend URL configuration is invalid."); }
  if (!(["http:", "https:"].includes(url.protocol)) || url.username || url.password || url.search || url.hash) {
    throw new ApiError("Backend URL configuration is invalid.");
  }
  return configured.replace(/\/$/, "");
}

export async function apiRequest<T>(path: string, options: { signal?: AbortSignal; method?: "GET" | "POST"; body?: unknown; localControl?: boolean } = {}): Promise<T> {
  const headers = new Headers({ Accept: "application/json" });
  if (options.body !== undefined) headers.set("Content-Type", "application/json");
  if (options.localControl) headers.set("X-NetRCA-Local-Control", "1");
  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl()}${path}`, {
      method: options.method ?? "GET",
      headers,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
      signal: options.signal,
      cache: "no-store",
    });
  } catch (error) {
    if (options.signal?.aborted) throw error;
    throw new ApiError("Could not reach the NetRCA API. Check that the backend is running and the local origin is allowed.");
  }

  let payload: unknown;
  try { payload = await response.json(); } catch { throw new ApiError("The NetRCA API returned an unreadable response.", response.status); }
  if (!response.ok) {
    const error = isRecord(payload) && isRecord(payload.error) ? payload.error : undefined;
    const code = typeof error?.code === "string" ? error.code : undefined;
    const messages: Record<string, string> = {
      LOCAL_CONTROL_REQUIRED: "This operation requires the local-control header.",
      LOCAL_ONLY: "This operation is available only from the local development host.",
      PIPELINE_WRITES_DISABLED: "Evidence collection is disabled by the backend configuration.",
      CORRELATION_WRITES_DISABLED: "Incident correlation is disabled by the backend configuration.",
      RCA_WRITES_DISABLED: "RCA runs are disabled by the backend configuration.",
      IMPACT_WRITES_DISABLED: "Impact analysis runs are disabled by the backend configuration.",
      DATABASE_UNAVAILABLE: "The database is unavailable. Check the backend database configuration.",
      GEMINI_DISABLED: "Gemini explanations are disabled by the backend configuration.",
      GEMINI_UNAVAILABLE: "The explanation provider is unavailable. Deterministic results remain available.",
    };
    const message = code && messages[code] ? messages[code] : typeof error?.message === "string" ? error.message : "The NetRCA API could not complete the request.";
    throw new ApiError(message, response.status, code);
  }
  if (!isRecord(payload) || payload.success !== true) throw new ApiError("The NetRCA API response did not match the expected contract.", response.status);
  return payload as T;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export async function getApiHealth(signal?: AbortSignal) {
  return apiRequest<Envelope<ApiHealth>>("/health", { signal });
}
export async function getNetworkStatus(signal?: AbortSignal) {
  return apiRequest<Envelope<NetworkStatus>>("/network/status", { signal });
}
export async function getTopology(signal?: AbortSignal) {
  try {
    return await apiRequest<Envelope<Topology>>("/topology", { signal });
  } catch (error) {
    const unavailableSimulator = error instanceof ApiError
      && (["SIMULATION_DISABLED", "NETWORK_UNAVAILABLE", "NETWORK_NOT_RUNNING", "MININET_UNAVAILABLE"].includes(error.code ?? "")
        || error.code === "MININET_UNAVAILABLE" && error.message === "SIMULATION_DISABLED");
    if (!unavailableSimulator) throw error;
    return apiRequest<Envelope<Topology>>("/topology?source=stored", { signal });
  }
}
export async function getMonitoring(signal?: AbortSignal) {
  return apiRequest<Envelope<Monitoring>>("/network/monitoring", { signal });
}

export async function getPage<T>(resource: "metrics" | "logs" | "events" | "anomalies" | "incidents", page = 1, limit = 20, signal?: AbortSignal): Promise<Page<T>> {
  const payload = await apiRequest<Record<string, unknown>>(`/${resource}?page=${page}&limit=${limit}`, { signal });
  const nested = payload.data;
  const candidate = Array.isArray(nested) ? nested : isRecord(nested) ? nested.data : undefined;
  const paginationValue = isRecord(payload.pagination) ? payload.pagination : isRecord(nested) ? nested.pagination : undefined;
  if (!Array.isArray(candidate) || !isRecord(paginationValue) || typeof paginationValue["total"] !== "number"
      || typeof paginationValue["page"] !== "number" || typeof paginationValue["limit"] !== "number"
      || typeof paginationValue["pages"] !== "number") {
    throw new ApiError(`The ${resource} response did not match the expected paginated contract.`);
  }
  return { data: candidate as T[], pagination: paginationValue as Page<T>["pagination"] };
}

export async function getIncident(id: string, signal?: AbortSignal) {
  const payload = await apiRequest<Envelope<IncidentDetail>>(`/incidents/${encodeURIComponent(id)}`, { signal });
  return payload.data;
}
export async function getIncidentRca(id: string, signal?: AbortSignal) {
  return apiRequest<Envelope<Record<string, unknown>>>(`/incidents/${encodeURIComponent(id)}/root-causes`, { signal });
}
export async function runIncidentRca(id: string, signal?: AbortSignal) {
  return apiRequest<Envelope<Record<string, unknown>>>(`/incidents/${encodeURIComponent(id)}/root-cause/analyze`, { method: "POST", localControl: true, signal });
}
export async function getIncidentImpact(id: string, signal?: AbortSignal) {
  return apiRequest<Envelope<Record<string, unknown>>>(`/incidents/${encodeURIComponent(id)}/impact`, { signal });
}
export async function runIncidentImpact(id: string, signal?: AbortSignal) {
  return apiRequest<Envelope<Record<string, unknown>>>(`/incidents/${encodeURIComponent(id)}/impact/analyze`, { method: "POST", localControl: true, signal });
}
export async function correlateEvidence(eventIds: string[], anomalyIds: string[], signal?: AbortSignal) {
  return apiRequest<Envelope<Record<string, unknown>>>("/events/correlate", { method: "POST", localControl: true, body: { event_ids: eventIds, anomaly_ids: anomalyIds }, signal });
}
export async function generateIncidentExplanation(id: string, signal?: AbortSignal) {
  return apiRequest<Envelope<Record<string, unknown>>>(`/ai/incidents/${encodeURIComponent(id)}/explain`, { method: "POST", localControl: true, signal });
}
