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
  last_operation?: string | null;
  last_result?: "SUCCEEDED" | "FAILED" | null;
  detail?: string | null;
};
export type Connectivity = {
  hosts: string[];
  packet_loss_percent: number;
  connected: boolean;
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
export type GraphSource = "live" | "stored";
export type GraphSummary = {
  directed: false;
  semantics: "PHYSICAL_TOPOLOGY";
  connected: boolean;
  components: string[][];
  devices: Array<{ id: string; name: string; device_type: string; status?: string }>;
  links: Array<{ id: string; source_device_id: string; destination_device_id: string; status?: string }>;
};
export type IncidentTopologyContext = {
  incident_id: string;
  source: "stored";
  evidence: Array<{ kind: "EVENT" | "ANOMALY"; id: string; device_id?: string | null; link_id?: string | null; device_found?: boolean | null; link_found?: boolean | null }>;
  referenced_device_ids: string[];
  referenced_link_ids: string[];
  context_device_ids: string[];
  context_link_ids: string[];
  missing_device_ids: string[];
  missing_link_ids: string[];
  unmapped_service_ids: string[];
};
export type Monitoring = {
  observed_at: string;
  topology_name: string;
  network_state: string;
  collection_status: string;
  counter_unit?: string;
  devices: Array<{ name: string; device_type: string; interfaces: Array<{
    name: string; status: string; operational_state?: string | null;
    rx_bytes?: number | null; tx_bytes?: number | null; rx_packets?: number | null; tx_packets?: number | null;
    rx_errors: number | null; tx_errors: number | null; error_code?: string | null;
  }> }>;
  links: Array<{ source: string; destination: string; status: string; interface_source?: string; interface_destination?: string }>;
  errors: string[];
};
export type ProbeReading = {
  observed_at: string;
  source: string;
  destination: string;
  packets_sent: number | null;
  packets_received: number | null;
  packet_loss_percent: number | null;
  latency_ms: number | null;
  status: "REACHABLE" | "UNREACHABLE" | "TIMEOUT" | "UNAVAILABLE";
  error_code?: string | null;
};
export type FaultType = "INTERFACE_FAILURE" | "LINK_FAILURE" | "PACKET_LOSS" | "HIGH_LATENCY";
export type FaultRequest = {
  fault_type: FaultType;
  device?: string;
  interface?: string;
  source?: string;
  destination?: string;
  packet_loss_percent?: number;
  latency_ms?: number;
  duration_seconds: number;
  severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
};
export type FaultRecord = {
  id: string;
  fault_type: FaultType;
  status: "ACTIVE" | "COMPLETED" | "CANCELLED";
  target: Record<string, string>;
  parameters: Record<string, string | number>;
  severity: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL";
  started_at: string;
  expires_at: string;
  ended_at?: string | null;
  end_reason?: string | null;
  restoration_result: "PENDING" | "SUCCEEDED" | "FAILED";
  error_code?: string | null;
  storage_status: "SYNCED" | "UNMAPPED" | "UNAVAILABLE";
};
export type EvidenceCollectionResult = {
  observed_at: string;
  metrics: number;
  events: number;
  duplicates: number;
  unmapped_links?: number;
  probe_status?: string;
};
export type DetectionResult = {
  metric_id?: string | null;
  observation_key: string;
  device_id?: string | null;
  link_id?: string | null;
  metric_type: string;
  value: number | string;
  unit: string;
  observed_at: string;
  status: "NORMAL" | "ANOMALY" | "INSUFFICIENT_DATA";
  method: "THRESHOLD" | "BASELINE" | "ISOLATION_FOREST" | "NONE";
  reason: string;
  severity?: "LOW" | "MEDIUM" | "HIGH" | "CRITICAL" | null;
  score?: number | null;
  score_kind?: string | null;
  support: Record<string, unknown>;
  baseline_samples: number;
  persistence: "NOT_REQUESTED" | "PERSISTED" | "EXISTING" | "UNAVAILABLE" | "NOT_ELIGIBLE";
};
export type DetectionRun = { items: DetectionResult[]; anomalies_detected: number; insufficient_data: number; persisted: number };
export type CorrelationEvidence = { kind: "EVENT" | "ANOMALY"; id: string; reason: string };
export type CorrelationIncident = { incident_id: string; created: boolean; evidence: CorrelationEvidence[] };
export type CorrelationRun = { incidents: CorrelationIncident[]; skipped_ids: string[]; created: number; attached: number };
export type RcaEvidenceReference = {
  source_type: "EVENT" | "ANOMALY" | "TOPOLOGY";
  source_id: string;
  timestamp?: string | null;
  metric_id?: string | null;
  reason: string;
};
export type RcaRuleContribution = { rule: string; points: number; evidence: RcaEvidenceReference[] };
export type RcaCandidate = {
  cause_type: "LINK_FAILURE" | "INTERFACE_FAILURE" | "DEVICE_UNAVAILABLE";
  target_kind: "LINK" | "DEVICE";
  target_id: string;
  score: number;
  score_kind: "UNCALIBRATED_RULE_POINTS";
  explanation: string;
  contributions: RcaRuleContribution[];
  supporting_evidence: RcaEvidenceReference[];
  contradictory_evidence: RcaEvidenceReference[];
  limitations: string[];
};
export type RcaRun = {
  id: string;
  incident_id: string;
  analysis_version: string;
  input_fingerprint: string;
  status: "CANDIDATES" | "INCONCLUSIVE";
  result: {
    incident_id: string;
    status: "CANDIDATES" | "INCONCLUSIVE";
    candidates: RcaCandidate[];
    limitations: string[];
    evidence_count: number;
    analysis_version: string;
  };
  created_at: string;
  last_analyzed_at: string;
};
export type ImpactEntity = {
  kind: "DEVICE" | "LINK" | "SERVICE";
  id: string;
  classification: "OBSERVED" | "POTENTIAL";
  evidence: RcaEvidenceReference[];
  explanation: string;
};
export type ImpactChainEdge = {
  step: number;
  source_kind: "DEVICE" | "LINK" | "SERVICE";
  source_id: string;
  target_kind: "DEVICE" | "LINK" | "SERVICE";
  target_id: string;
  relationship: "LINK_ENDPOINT" | "DEVICE_ADJACENCY" | "HOSTS_SERVICE";
  classification: "POTENTIAL";
  evidence: RcaEvidenceReference[];
  explanation: string;
};
export type ImpactRun = {
  id: string;
  rca_run_id: string;
  analysis_version: string;
  input_fingerprint: string;
  topology_fingerprint: string;
  status: "ASSESSED" | "INCONCLUSIVE";
  result: {
    incident_id: string;
    rca_run_id: string;
    status: "ASSESSED" | "INCONCLUSIVE";
    candidate_target_kind?: "DEVICE" | "LINK" | null;
    candidate_target_id?: string | null;
    entities: ImpactEntity[];
    chain: ImpactChainEdge[];
    affected_devices: number;
    affected_links: number;
    affected_services: number;
    user_application_impact: "UNKNOWN_UNVERIFIED";
    topology_input: Record<string, unknown>;
    limitations: string[];
    analysis_version: string;
  };
  created_at: string;
  last_analyzed_at: string;
};
export type ExplanationSourceReference = {
  source_type: "EVENT" | "ANOMALY" | "TOPOLOGY" | "RCA_RUN" | "IMPACT_RUN";
  source_id: string;
  timestamp?: string | null;
};
export type ExplanationSection = "summary" | "observed_facts" | "candidate_explanations" | "failure_chain_explanation" | "impact_explanation" | "uncertainties" | "missing_evidence" | "limitations";
export type ExplanationClaim = {
  claim_id: string;
  section: ExplanationSection;
  text: string;
  evidence_references: ExplanationSourceReference[];
};
export type IncidentExplanation = {
  explanation_version: "EXPLANATION_V1";
  incident_id: string;
  rca_run_id: string;
  impact_run_id?: string | null;
  model_name: string;
  summary: ExplanationClaim[];
  observed_facts: ExplanationClaim[];
  candidate_explanations: ExplanationClaim[];
  failure_chain_explanation: ExplanationClaim[];
  impact_explanation: ExplanationClaim[];
  uncertainties: ExplanationClaim[];
  missing_evidence: ExplanationClaim[];
  evidence_references: ExplanationSourceReference[];
  limitations: ExplanationClaim[];
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

export async function apiRequest<T>(path: string, options: { signal?: AbortSignal; method?: "GET" | "POST"; body?: unknown; localControl?: boolean; acceptErrorStatusData?: boolean } = {}): Promise<T> {
  if (path !== "/health") {
    const { presentationModeEnabled, presentationDemoResponse, PresentationDemoError } = await import("@/lib/presentation-demo");
    if (presentationModeEnabled()) {
      if (options.signal?.aborted) throw new DOMException("The operation was aborted.", "AbortError");
      try {
        return presentationDemoResponse(path, options.method ?? "GET") as T;
      } catch (error) {
        if (error instanceof PresentationDemoError) throw new ApiError(error.message, error.status, error.code);
        throw error;
      }
    }
  }
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
  if (!response.ok && options.acceptErrorStatusData && isRecord(payload) && payload.success === true) return payload as T;
  if (!response.ok) {
    const error = isRecord(payload) && isRecord(payload.error) ? payload.error : undefined;
    const code = typeof error?.code === "string" ? error.code : undefined;
    const messages: Record<string, string> = {
      LOCAL_CONTROL_REQUIRED: "This operation requires the local-control header.",
      LOCAL_ONLY: "This operation is available only from the local development host.",
      PIPELINE_WRITES_DISABLED: "Evidence collection is disabled by the backend configuration.",
      ANOMALY_WRITES_DISABLED: "Anomaly persistence is disabled by the backend configuration.",
      METRIC_NOT_FOUND: "A selected stored metric is no longer available.",
      STORED_METRIC_INVALID: "A selected metric is not valid Phase 6 evidence.",
      DUPLICATE_OBSERVATION: "Conflicting observations share the same evidence key.",
      CORRELATION_WRITES_DISABLED: "Incident correlation is disabled by the backend configuration.",
      EVIDENCE_NOT_FOUND: "Selected stored evidence is missing or no longer valid.",
      AMBIGUOUS_MEMBERSHIP: "Selected evidence already belongs to multiple incidents and cannot be assigned safely.",
      CORRELATION_LIMIT: "The correlation window contains too many open incident anchors.",
      RCA_WRITES_DISABLED: "RCA runs are disabled by the backend configuration.",
      IMPACT_WRITES_DISABLED: "Impact analysis runs are disabled by the backend configuration.",
      RCA_INPUT_INVALID: "The stored RCA input is stale or invalid. Re-run deterministic RCA before impact analysis.",
      INVALID_STORED_ANALYSIS: "The stored analysis failed validation and cannot be used for impact analysis.",
      ANALYSIS_LIMIT: "This incident contains too much evidence for one bounded analysis run.",
      DATABASE_UNAVAILABLE: "The database is unavailable. Check the backend database configuration.",
      GEMINI_DISABLED: "Gemini explanations are disabled by the backend configuration.",
      GEMINI_UNAVAILABLE: "The explanation provider is unavailable. Deterministic results remain available.",
      RCA_REQUIRED: "Run deterministic RCA before requesting an explanation.",
      ANALYSIS_NOT_READY: "Stored analysis changed or failed validation. Refresh and rerun deterministic analysis before requesting an explanation.",
      MININET_UNAVAILABLE: "The Mininet lab is unavailable. Run the backend in the approved Ubuntu environment with simulation enabled.",
      NETWORK_NOT_RUNNING: "Start the Mininet lab before using this operation.",
      NETWORK_ALREADY_RUNNING: "The Mininet lab is already running.",
      NETWORK_OPERATION_IN_PROGRESS: "Another Mininet operation is still in progress.",
      CONNECTIVITY_FAILED: "The Mininet connectivity test failed.",
      FAULT_INJECTION_DISABLED: "Fault injection is disabled. Enable it only in the approved local Mininet lab.",
      ACTIVE_FAULT_EXISTS: "Recover the active fault before injecting another.",
      FAULT_NOT_FOUND: "The fault is no longer available in this backend process.",
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
export async function startNetwork(signal?: AbortSignal) {
  return apiRequest<Envelope<NetworkStatus>>("/network/start", { method: "POST", localControl: true, signal });
}
export async function stopNetwork(signal?: AbortSignal) {
  return apiRequest<Envelope<NetworkStatus>>("/network/stop", { method: "POST", localControl: true, signal });
}
export async function resetNetwork(signal?: AbortSignal) {
  return apiRequest<Envelope<NetworkStatus>>("/network/reset", { method: "POST", localControl: true, signal });
}
export async function testNetworkConnectivity(signal?: AbortSignal) {
  return apiRequest<Envelope<Connectivity>>("/network/connectivity-test", { method: "POST", localControl: true, acceptErrorStatusData: true, signal });
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
export async function getTopologyGraph(source: GraphSource, signal?: AbortSignal) {
  const response = await apiRequest<Envelope<GraphSummary>>(`/topology/analysis?source=${source}`, { signal });
  const graph = response.data as unknown;
  if (!isRecord(graph) || graph.directed !== false || graph.semantics !== "PHYSICAL_TOPOLOGY"
      || typeof graph.connected !== "boolean" || !Array.isArray(graph.components)
      || !graph.components.every((component) => Array.isArray(component) && component.every((id) => typeof id === "string"))
      || !Array.isArray(graph.devices) || !graph.devices.every((device) => isRecord(device)
        && typeof device.id === "string" && typeof device.name === "string" && typeof device.device_type === "string"
        && (device.status === undefined || typeof device.status === "string"))
      || !Array.isArray(graph.links) || !graph.links.every((link) => isRecord(link)
        && typeof link.id === "string" && typeof link.source_device_id === "string"
        && typeof link.destination_device_id === "string" && (link.status === undefined || typeof link.status === "string"))) {
    throw new ApiError("The topology analysis response did not match the expected graph contract.");
  }
  const deviceIds = (graph.devices as Array<{ id: string }>).map((device) => device.id);
  const linkIds = (graph.links as Array<{ id: string }>).map((link) => link.id);
  if (new Set(deviceIds).size !== deviceIds.length || new Set(linkIds).size !== linkIds.length) {
    throw new ApiError("The topology analysis response contained duplicate graph IDs.");
  }
  return response;
}
export async function getIncidentTopologyContext(id: string, signal?: AbortSignal) {
  const response = await apiRequest<Envelope<IncidentTopologyContext>>(`/incidents/${encodeURIComponent(id)}/topology-context`, { signal });
  const context = response.data as unknown;
  const validIds = (key: string) => isRecord(context) && Array.isArray(context[key]) && context[key].every((value) => typeof value === "string");
  const validEvidence = (value: unknown) => isRecord(value) && (value.kind === "EVENT" || value.kind === "ANOMALY")
    && typeof value.id === "string"
    && (value.device_id === undefined || value.device_id === null || typeof value.device_id === "string")
    && (value.link_id === undefined || value.link_id === null || typeof value.link_id === "string")
    && (value.device_found === undefined || value.device_found === null || typeof value.device_found === "boolean")
    && (value.link_found === undefined || value.link_found === null || typeof value.link_found === "boolean");
  if (!isRecord(context) || context.source !== "stored" || context.incident_id !== id
      || !validIds("context_device_ids") || !validIds("context_link_ids") || !validIds("missing_device_ids")
      || !validIds("referenced_device_ids") || !validIds("referenced_link_ids") || !validIds("missing_link_ids")
      || !validIds("unmapped_service_ids") || !Array.isArray(context.evidence) || !context.evidence.every(validEvidence)) {
    throw new ApiError("The incident topology context response did not match the expected contract.");
  }
  return response;
}
export async function getMonitoring(signal?: AbortSignal) {
  return apiRequest<Envelope<Monitoring>>("/network/monitoring", { signal });
}
export async function probeNetwork(source: string, destination: string, signal?: AbortSignal) {
  return apiRequest<Envelope<ProbeReading>>("/network/monitoring/probe", {
    method: "POST", localControl: true, signal,
    body: { source, destination, count: 2, timeout_seconds: 2 },
  });
}
export async function getFaultTypes(signal?: AbortSignal) {
  return apiRequest<Envelope<FaultType[]>>("/faults/types", { signal });
}
export async function getFaults(signal?: AbortSignal): Promise<Page<FaultRecord>> {
  const payload = await apiRequest<Record<string, unknown>>("/faults?page=1&limit=100", { signal });
  if (!Array.isArray(payload.data) || !isRecord(payload.pagination)
      || typeof payload.pagination.page !== "number" || typeof payload.pagination.limit !== "number"
      || typeof payload.pagination.total !== "number" || typeof payload.pagination.pages !== "number") {
    throw new ApiError("The fault history response did not match the expected paginated contract.");
  }
  return { data: payload.data as FaultRecord[], pagination: payload.pagination as Page<FaultRecord>["pagination"] };
}
export async function injectFault(value: FaultRequest, signal?: AbortSignal) {
  return apiRequest<Envelope<FaultRecord>>("/faults/inject", { method: "POST", localControl: true, body: value, signal });
}
export async function recoverFault(id: string, signal?: AbortSignal) {
  return apiRequest<Envelope<FaultRecord>>(`/faults/${encodeURIComponent(id)}/recover`, { method: "POST", localControl: true, signal });
}
export async function resetFaults(signal?: AbortSignal) {
  return apiRequest<Envelope<FaultRecord | []>>("/faults/reset", { method: "POST", localControl: true, signal });
}
export async function collectEvidenceSnapshot(signal?: AbortSignal) {
  return apiRequest<Envelope<EvidenceCollectionResult>>("/pipeline/collect", { method: "POST", localControl: true, signal });
}
export async function collectEvidenceProbe(source: string, destination: string, signal?: AbortSignal) {
  return apiRequest<Envelope<EvidenceCollectionResult>>("/pipeline/probe", {
    method: "POST", localControl: true, signal,
    body: { source, destination, count: 2, timeout_seconds: 2 },
  });
}
export async function detectStoredMetrics(metricIds: string[], signal?: AbortSignal) {
  return apiRequest<Envelope<DetectionRun>>("/anomalies/detect", {
    method: "POST", localControl: true, signal,
    body: { metric_ids: metricIds.slice(0, 20), persist: false },
  });
}

export async function getPage<T>(resource: "metrics" | "logs" | "events" | "anomalies" | "incidents", page = 1, limit = 20, signal?: AbortSignal, filter?: { deviceId?: string; linkId?: string }): Promise<Page<T>> {
  const query = new URLSearchParams({ page: String(page), limit: String(limit) });
  if (filter?.deviceId && ["metrics", "logs", "events", "anomalies"].includes(resource)) query.set("device_id", filter.deviceId);
  if (filter?.linkId && ["metrics", "events"].includes(resource)) query.set("link_id", filter.linkId);
  const payload = await apiRequest<Record<string, unknown>>(`/${resource}?${query}`, { signal });
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
  return apiRequest<Envelope<RcaRun>>(`/incidents/${encodeURIComponent(id)}/root-causes`, { signal });
}
export async function runIncidentRca(id: string, signal?: AbortSignal) {
  return apiRequest<Envelope<RcaRun>>(`/incidents/${encodeURIComponent(id)}/root-cause/analyze`, { method: "POST", localControl: true, signal });
}
export async function getIncidentImpact(id: string, signal?: AbortSignal) {
  return apiRequest<Envelope<ImpactRun>>(`/incidents/${encodeURIComponent(id)}/impact`, { signal });
}
export async function runIncidentImpact(id: string, signal?: AbortSignal) {
  return apiRequest<Envelope<ImpactRun>>(`/incidents/${encodeURIComponent(id)}/impact/analyze`, { method: "POST", localControl: true, signal });
}
export async function correlateEvidence(eventIds: string[], anomalyIds: string[], signal?: AbortSignal) {
  return apiRequest<Envelope<CorrelationRun>>("/events/correlate", { method: "POST", localControl: true, body: { event_ids: eventIds.slice(0, 100), anomaly_ids: anomalyIds.slice(0, Math.max(0, 100 - eventIds.length)) }, signal });
}
export async function generateIncidentExplanation(id: string, signal?: AbortSignal) {
  return apiRequest<Envelope<IncidentExplanation>>(`/ai/incidents/${encodeURIComponent(id)}/explain`, { method: "POST", localControl: true, signal });
}
