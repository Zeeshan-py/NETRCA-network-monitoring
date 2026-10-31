import type { Envelope, GraphSummary, IncidentDetail, IncidentTopologyContext, Monitoring, NetworkStatus, Topology } from "@/lib/api";

export class PresentationDemoError extends Error {
  constructor(message: string, readonly status: number, readonly code: string) {
    super(message);
    this.name = "PresentationDemoError";
  }
}

const IDs = {
  router: "05d50c12-c3a0-55c0-877a-1f1491f84f94",
  switch: "e91444e2-2c6f-59f4-9fc9-d41b662e7214",
  app: "247fd2e3-fd24-5f3e-b798-babffc370f70",
  isolated: "149e4c97-4e26-5ca0-9b92-8134f1f6400a",
  uplink: "195b92f7-e9a1-533e-b923-ffb8a2e60888",
  serverLink: "6fab58fa-4987-5c0f-8597-2dda64a3075f",
  lossMetric: "eddfd1ad-5b9c-5fae-a7c6-7dd2f3ffacc9",
  failureEvent: "ef2317ce-2a9b-53bd-bb7f-dc7e1d8aa99e",
  timeoutEvent: "406bc67f-5e93-5d3b-a5a0-4e7398b889b6",
  anomaly: "f0b65b4f-a95d-5ec2-b42f-514c1a4bb1e5",
  incident: "738c7634-2a2b-58b9-beed-a62853c7b7d3",
} as const;

const observedAt = "2026-10-31T09:42:18Z";

const nodes = [
  { id: IDs.router, name: "DEMO-R1", device_type: "ROUTER", status: "DOWN", ip_address: "10.77.0.1" },
  { id: IDs.switch, name: "DEMO-S1", device_type: "SWITCH", status: "WARNING", ip_address: null },
  { id: IDs.app, name: "DEMO-App01", device_type: "SERVER", status: "WARNING", ip_address: "10.77.0.10" },
  { id: IDs.isolated, name: "DEMO-Backup01", device_type: "HOST", status: "HEALTHY", ip_address: "10.77.0.99" },
];

const links = [
  { id: IDs.uplink, source: IDs.router, destination: IDs.switch, source_device_id: IDs.router, destination_device_id: IDs.switch, status: "DOWN", interface_source: "r1-eth0", interface_destination: "s1-eth1" },
  { id: IDs.serverLink, source: IDs.switch, destination: IDs.app, source_device_id: IDs.switch, destination_device_id: IDs.app, status: "UP", interface_source: "s1-eth2", interface_destination: "app01-eth0" },
];

const topology: Topology = {
  topology_name: "netrca_presentation_scenario",
  nodes,
  links,
  components: [[IDs.router, IDs.switch, IDs.app], [IDs.isolated]],
};

const graph: GraphSummary = {
  directed: false,
  semantics: "PHYSICAL_TOPOLOGY",
  connected: false,
  components: topology.components ?? [],
  devices: nodes.map(({ id, name, device_type, status }) => ({ id, name, device_type, status })),
  links: links.map(({ id, source_device_id, destination_device_id, status }) => ({ id, source_device_id, destination_device_id, status })),
};

const metrics = [
  { id: IDs.lossMetric, device_id: IDs.router, link_id: IDs.uplink, metric_type: "PACKET_LOSS", value: 100, unit: "%", threshold: 5, timestamp: "2026-10-31T09:42:01Z", metadata: { demo: true } },
  { id: "9b0cdbbc-ec26-542a-bb43-1a9ca7889663", device_id: IDs.router, link_id: IDs.uplink, metric_type: "LATENCY", value: 248, unit: "ms", threshold: 100, timestamp: "2026-10-31T09:41:58Z", metadata: { demo: true } },
  { id: "7d8b0348-6f63-5daa-a47e-89d85f4520c0", device_id: IDs.app, metric_type: "AVAILABILITY", value: 92.4, unit: "%", threshold: 99, timestamp: "2026-10-31T09:42:06Z", metadata: { demo: true } },
];

const logs = [
  { id: "a9bada2c-881e-5654-85a4-d82386d49384", device_id: IDs.router, severity: "ERROR", event_type: "INTERFACE_FAILURE", message: "DEMO: WAN uplink transitioned to DOWN.", source: "presentation-fixture", timestamp: "2026-10-31T09:42:00Z" },
  { id: "9411f8a2-4ef6-57cf-9352-aa7746519051", device_id: IDs.app, severity: "WARNING", event_type: "HTTP_TIMEOUT", message: "DEMO: checkout API exceeded the service timeout.", source: "presentation-fixture", timestamp: "2026-10-31T09:42:05Z" },
];

const events = [
  { id: IDs.failureEvent, device_id: IDs.router, link_id: IDs.uplink, event_type: "INTERFACE_FAILURE", severity: "HIGH", message: "DEMO: R1 uplink failed.", status: "DETECTED", timestamp: "2026-10-31T09:42:00Z" },
  { id: IDs.timeoutEvent, device_id: IDs.app, event_type: "SERVER_TIMEOUT", severity: "HIGH", message: "DEMO: downstream application requests timed out.", status: "DETECTED", timestamp: "2026-10-31T09:42:03Z" },
];

const anomalies = [
  { id: IDs.anomaly, metric_id: IDs.lossMetric, device_id: IDs.router, link_id: IDs.uplink, name: "DEMO-FIXTURE-NO-MODEL-RUN", anomaly_type: "PACKET_LOSS", severity: "HIGH", is_anomaly: true, anomaly_score: 0.99, detected_at: "2026-10-31T09:42:02Z", timestamp: "2026-10-31T09:42:02Z", message: "100% packet loss exceeded the configured 5% threshold." },
  { id: "0b4debc9-63b6-5cc6-9216-ff82a194027d", device_id: IDs.app, name: "DEMO-FIXTURE-NO-MODEL-RUN", anomaly_type: "AVAILABILITY", severity: "MEDIUM", is_anomaly: true, anomaly_score: 0.76, detected_at: "2026-10-31T09:42:07Z", timestamp: "2026-10-31T09:42:07Z", message: "Service availability fell below its configured objective." },
];

const incident = {
  id: IDs.incident,
  title: "DEMO: WAN uplink outage affecting checkout",
  description: "Synthetic presentation scenario: a router uplink failure precedes packet loss and application timeouts. No live customer network or Gemini call is involved.",
  severity: "HIGH",
  status: "ROOT_CAUSE_IDENTIFIED",
  start_time: "2026-10-31T09:42:00Z",
  end_time: null,
};

const incidentDetail: IncidentDetail = { ...incident, events, anomalies };

const rca = {
  id: "d61ae586-a513-5b7d-9a36-c418d95a78b9",
  status: "COMPLETED",
  result: {
    status: "CANDIDATES",
    candidates: [{
      cause_type: "LINK_FAILURE",
      target_kind: "LINK",
      target_id: IDs.uplink,
      score: 20,
      score_kind: "UNCALIBRATED_RULE_POINTS",
      explanation: "The stored down uplink is the earliest directly referenced failure and is supported by packet-loss evidence.",
      supporting_evidence: [
        { source_type: "EVENT", source_id: IDs.failureEvent, timestamp: "2026-10-31T09:42:00Z", reason: "INITIAL_FAILURE" },
        { source_type: "ANOMALY", source_id: IDs.anomaly, timestamp: "2026-10-31T09:42:02Z", reason: "PACKET_LOSS" },
      ],
      contradictory_evidence: [],
    }],
    limitations: ["SYNTHETIC_PRESENTATION_FIXTURE", "RULE_SCORE_IS_NOT_A_PROBABILITY"],
    evidence_count: 4,
    analysis_version: "RULES_V1",
  },
};

const impact = {
  id: "32d22e0a-b56b-5793-9fbb-122902d34e4b",
  status: "COMPLETED",
  result: {
    status: "ASSESSED",
    candidate_target_kind: "LINK",
    candidate_target_id: IDs.uplink,
    entities: [
      { kind: "LINK", id: IDs.uplink, classification: "OBSERVED", explanation: "The uplink is directly observed as down." },
      { kind: "DEVICE", id: IDs.app, classification: "POTENTIAL", explanation: "The application server is downstream of the failed uplink and has timeout evidence." },
      { kind: "SERVICE", id: "checkout-api", classification: "POTENTIAL", explanation: "Checkout requests timed out after the upstream failure." },
    ],
    chain: [
      { step: 1, source_kind: "LINK", source_id: IDs.uplink, target_kind: "DEVICE", target_id: IDs.app, relationship: "DOWNSTREAM_PATH", classification: "POTENTIAL", explanation: "Stored physical topology connects the failed uplink to the application path." },
      { step: 2, source_kind: "DEVICE", source_id: IDs.app, target_kind: "SERVICE", target_id: "checkout-api", relationship: "HOSTS_SERVICE", classification: "POTENTIAL", explanation: "The application server hosts the affected checkout API." },
    ],
    affected_devices: 1,
    affected_links: 1,
    affected_services: 1,
    user_application_impact: "POTENTIAL_CHECKOUT_DEGRADATION",
    limitations: ["SYNTHETIC_PRESENTATION_FIXTURE", "CUSTOMER_IMPACT_NOT_EXTERNALLY_CONFIRMED"],
    analysis_version: "IMPACT_RULES_V1",
  },
};

const context: IncidentTopologyContext = {
  incident_id: IDs.incident,
  source: "stored",
  evidence: [
    { kind: "EVENT", id: IDs.failureEvent, device_id: IDs.router, link_id: IDs.uplink, device_found: true, link_found: true },
    { kind: "EVENT", id: IDs.timeoutEvent, device_id: IDs.app, device_found: true },
    { kind: "ANOMALY", id: IDs.anomaly, device_id: IDs.router, link_id: IDs.uplink, device_found: true, link_found: true },
  ],
  referenced_device_ids: [IDs.router, IDs.app],
  referenced_link_ids: [IDs.uplink],
  context_device_ids: [IDs.router, IDs.switch, IDs.app],
  context_link_ids: [IDs.uplink, IDs.serverLink],
  missing_device_ids: [],
  missing_link_ids: [],
  unmapped_service_ids: ["checkout-api"],
};

const monitoring: Monitoring = {
  observed_at: observedAt,
  topology_name: "netrca_presentation_scenario",
  network_state: "SYNTHETIC_DEMO",
  collection_status: "FIXTURE_LOADED",
  devices: [
    { name: "DEMO-R1", device_type: "ROUTER", interfaces: [{ name: "r1-eth0", status: "DOWN", rx_errors: 1842, tx_errors: 916 }] },
    { name: "DEMO-S1", device_type: "SWITCH", interfaces: [{ name: "s1-eth1", status: "DOWN", rx_errors: 44, tx_errors: 128 }] },
    { name: "DEMO-App01", device_type: "SERVER", interfaces: [{ name: "app01-eth0", status: "UP", rx_errors: 0, tx_errors: 3 }] },
  ],
  links: [{ source: "DEMO-R1", destination: "DEMO-S1", status: "DOWN" }, { source: "DEMO-S1", destination: "DEMO-App01", status: "UP" }],
  errors: ["SYNTHETIC_PRESENTATION_DATA"],
};

const network: NetworkStatus = {
  available: false,
  state: "DISABLED",
  topology_name: "netrca_presentation_scenario",
  started_at: null,
  device_count: nodes.length,
  link_count: links.length,
  operation: null,
};

function page(data: unknown[], url: URL) {
  const requestedPage = Math.max(1, Number(url.searchParams.get("page") ?? 1));
  const limit = Math.max(1, Number(url.searchParams.get("limit") ?? 20));
  const deviceId = url.searchParams.get("device_id");
  const linkId = url.searchParams.get("link_id");
  const filtered = data.filter((item) => {
    const record = item as Record<string, unknown>;
    return (!deviceId || record.device_id === deviceId) && (!linkId || record.link_id === linkId);
  });
  const start = (requestedPage - 1) * limit;
  return { success: true, data: filtered.slice(start, start + limit), pagination: { page: requestedPage, limit, total: filtered.length, pages: Math.ceil(filtered.length / limit) } };
}

export function presentationModeEnabled() {
  return process.env.NEXT_PUBLIC_NETRCA_PRESENTATION_MODE?.trim().toLowerCase() === "true";
}

export function presentationDemoResponse(path: string, method: "GET" | "POST" = "GET"): unknown {
  const url = new URL(path, "http://netrca.local");
  const pathname = url.pathname;
  if (pathname === "/network/status") return { success: true, data: network } satisfies Envelope<NetworkStatus>;
  if (pathname === "/topology") {
    if (url.searchParams.get("source") !== "stored") throw new PresentationDemoError("Live Mininet is intentionally disabled in presentation mode. Use Stored topology.", 409, "SIMULATION_DISABLED");
    return { success: true, data: topology } satisfies Envelope<Topology>;
  }
  if (pathname === "/topology/analysis") {
    if (url.searchParams.get("source") !== "stored") throw new PresentationDemoError("Live Mininet is intentionally disabled in presentation mode. Use Stored topology.", 409, "SIMULATION_DISABLED");
    return { success: true, data: graph } satisfies Envelope<GraphSummary>;
  }
  if (pathname === "/network/monitoring") return { success: true, data: monitoring } satisfies Envelope<Monitoring>;
  if (pathname === "/metrics") return page(metrics, url);
  if (pathname === "/logs") return page(logs, url);
  if (pathname === "/events") return page(events, url);
  if (pathname === "/anomalies") return page(anomalies, url);
  if (pathname === "/incidents") return page([incident], url);
  if (pathname === `/incidents/${IDs.incident}`) return { success: true, data: incidentDetail };
  if (pathname === `/incidents/${IDs.incident}/topology-context`) return { success: true, data: context };
  if (pathname === `/incidents/${IDs.incident}/root-causes`) return { success: true, data: rca };
  if (pathname === `/incidents/${IDs.incident}/root-cause/analyze` && method === "POST") return { success: true, data: rca, message: "Synthetic deterministic RCA replayed." };
  if (pathname === `/incidents/${IDs.incident}/impact`) return { success: true, data: impact };
  if (pathname === `/incidents/${IDs.incident}/impact/analyze` && method === "POST") return { success: true, data: impact, message: "Synthetic impact analysis replayed." };
  if (pathname === "/events/correlate" && method === "POST") return { success: true, data: { incident_id: IDs.incident, created: false, attached_events: events.length, attached_anomalies: anomalies.length, demo: true } };
  if (pathname === `/ai/incidents/${IDs.incident}/explain` && method === "POST") return {
    success: true,
    data: {
      summary: [{ claim_id: "DEMO-C001", text: "A WAN uplink failure preceded packet loss and downstream checkout timeouts.", evidence_references: [{ source_type: "EVENT", source_id: IDs.failureEvent }, { source_type: "ANOMALY", source_id: IDs.anomaly }] }],
      observed_facts: [{ claim_id: "DEMO-C002", text: "The uplink is down and packet loss reached 100% in the synthetic evidence set.", evidence_references: [{ source_type: "EVENT", source_id: IDs.failureEvent }, { source_type: "METRIC", source_id: IDs.lossMetric }] }],
      candidate_explanations: [{ claim_id: "DEMO-C003", text: "The deterministic rules rank the failed uplink as the leading candidate; the score is not a probability.", evidence_references: [{ source_type: "EVENT", source_id: IDs.failureEvent }] }],
      failure_chain_explanation: [{ claim_id: "DEMO-C004", text: "The stored topology supports a potential path from the failed uplink to the application server and checkout service.", evidence_references: [{ source_type: "EVENT", source_id: IDs.timeoutEvent }] }],
      uncertainties: [{ claim_id: "DEMO-C005", text: "External customer impact was not independently measured.", evidence_references: [] }],
      limitations: [{ claim_id: "DEMO-C006", text: "This explanation is a static presentation fixture; no Gemini request was made.", evidence_references: [] }],
      provider: "STATIC_PRESENTATION_FIXTURE",
    },
  };
  throw new PresentationDemoError("This resource is not part of the synthetic presentation scenario.", 404, "DEMO_RESOURCE_NOT_FOUND");
}
