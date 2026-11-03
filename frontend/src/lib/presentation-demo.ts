import type { Envelope, GraphSummary, ImpactRun, IncidentDetail, IncidentTopologyContext, Monitoring, NetworkStatus, Topology } from "@/lib/api";
import labScenario from "../../../scenarios/netrca_lab_v1.json";

export class PresentationDemoError extends Error {
  constructor(message: string, readonly status: number, readonly code: string) {
    super(message);
    this.name = "PresentationDemoError";
  }
}

function nodeId(key: string) {
  const node = labScenario.nodes.find((item) => item.key === key);
  if (!node) throw new Error(`Canonical scenario is missing node ${key}`);
  return node.id;
}

function linkId(key: string) {
  const link = labScenario.links.find((item) => item.key === key);
  if (!link) throw new Error(`Canonical scenario is missing link ${key}`);
  return link.id;
}

const IDs = {
  switch1: nodeId("s1"),
  switch2: nodeId("s2"),
  server: nodeId("server1"),
  failedLink: linkId("s1--s2"),
  lossMetric: "eddfd1ad-5b9c-5fae-a7c6-7dd2f3ffacc9",
  failureEvent: "ef2317ce-2a9b-53bd-bb7f-dc7e1d8aa99e",
  timeoutEvent: "406bc67f-5e93-5d3b-a5a0-4e7398b889b6",
  anomaly: "f0b65b4f-a95d-5ec2-b42f-514c1a4bb1e5",
  incident: "738c7634-2a2b-58b9-beed-a62853c7b7d3",
  service: "ae9169c9-80e3-53a5-a027-d61ce322937a",
} as const;

const observedAt = "2026-10-31T09:42:18Z";

const nodeStatus: Record<string, string> = { s1: "WARNING", s2: "WARNING", h1: "HEALTHY", h2: "WARNING", server1: "WARNING" };
const nodes = labScenario.nodes.map((node) => ({
  id: node.id,
  name: node.name,
  device_type: node.device_type,
  status: nodeStatus[node.key] ?? "HEALTHY",
  ip_address: node.ip_address,
}));

const links = labScenario.links.map((link) => ({
  id: link.id,
  source: nodeId(link.source),
  destination: nodeId(link.destination),
  source_device_id: nodeId(link.source),
  destination_device_id: nodeId(link.destination),
  status: link.key === "s1--s2" ? "DOWN" : "UP",
  interface_source: link.interface_source,
  interface_destination: link.interface_destination,
}));

const topology: Topology = {
  topology_name: labScenario.name,
  nodes,
  links,
  components: [labScenario.nodes.map((node) => node.id)],
};

const graph: GraphSummary = {
  directed: false,
  semantics: "PHYSICAL_TOPOLOGY",
  connected: true,
  components: topology.components ?? [],
  devices: nodes.map(({ id, name, device_type, status }) => ({ id, name, device_type, status })),
  links: links.map(({ id, source_device_id, destination_device_id, status }) => ({ id, source_device_id, destination_device_id, status })),
};

const metrics = [
  { id: IDs.lossMetric, device_id: IDs.switch1, link_id: IDs.failedLink, metric_type: "PACKET_LOSS", value: 100, unit: "%", threshold: 5, timestamp: "2026-10-31T09:42:01Z", metadata: { demo: true } },
  { id: "9b0cdbbc-ec26-542a-bb43-1a9ca7889663", device_id: IDs.switch1, link_id: IDs.failedLink, metric_type: "LATENCY", value: 248, unit: "ms", threshold: 100, timestamp: "2026-10-31T09:41:58Z", metadata: { demo: true } },
  { id: "7d8b0348-6f63-5daa-a47e-89d85f4520c0", device_id: IDs.server, metric_type: "AVAILABILITY", value: 92.4, unit: "%", threshold: 99, timestamp: "2026-10-31T09:42:06Z", metadata: { demo: true } },
];

const logs = [
  { id: "a9bada2c-881e-5654-85a4-d82386d49384", device_id: IDs.switch1, severity: "ERROR", event_type: "INTERFACE_FAILURE", message: "DEMO: the s1-to-s2 inter-switch link transitioned to DOWN.", source: "presentation-fixture", timestamp: "2026-10-31T09:42:00Z" },
  { id: "9411f8a2-4ef6-57cf-9352-aa7746519051", device_id: IDs.server, severity: "WARNING", event_type: "HTTP_TIMEOUT", message: "DEMO: checkout API exceeded the service timeout on server1.", source: "presentation-fixture", timestamp: "2026-10-31T09:42:05Z" },
];

const events = [
  { id: IDs.failureEvent, device_id: IDs.switch1, link_id: IDs.failedLink, event_type: "INTERFACE_FAILURE", severity: "HIGH", message: "DEMO: the s1-to-s2 link failed.", status: "DETECTED", timestamp: "2026-10-31T09:42:00Z" },
  { id: IDs.timeoutEvent, device_id: IDs.server, event_type: "SERVER_TIMEOUT", severity: "HIGH", message: "DEMO: downstream application requests to server1 timed out.", status: "DETECTED", timestamp: "2026-10-31T09:42:03Z" },
];

const anomalies = [
  { id: IDs.anomaly, metric_id: IDs.lossMetric, device_id: IDs.switch1, link_id: IDs.failedLink, name: "DEMO-FIXTURE-NO-MODEL-RUN", anomaly_type: "PACKET_LOSS", severity: "HIGH", is_anomaly: true, anomaly_score: 0.99, detected_at: "2026-10-31T09:42:02Z", timestamp: "2026-10-31T09:42:02Z", message: "100% packet loss exceeded the configured 5% threshold." },
  { id: "0b4debc9-63b6-5cc6-9216-ff82a194027d", device_id: IDs.server, name: "DEMO-FIXTURE-NO-MODEL-RUN", anomaly_type: "AVAILABILITY", severity: "MEDIUM", is_anomaly: true, anomaly_score: 0.76, detected_at: "2026-10-31T09:42:07Z", timestamp: "2026-10-31T09:42:07Z", message: "Service availability fell below its configured objective." },
];

const incident = {
  id: IDs.incident,
  title: "DEMO: inter-switch link outage affecting checkout",
  description: "Synthetic presentation evidence for the canonical Mininet topology: the s1-to-s2 link failure precedes packet loss and server1 timeouts. No live customer network or Gemini call is involved.",
  severity: "HIGH",
  status: "ROOT_CAUSE_IDENTIFIED",
  start_time: "2026-10-31T09:42:00Z",
  end_time: null,
};

const incidentDetail: IncidentDetail = { ...incident, events, anomalies };

const rca = {
  id: "d61ae586-a513-5b7d-9a36-c418d95a78b9",
  incident_id: IDs.incident,
  analysis_version: "RULES_V1",
  input_fingerprint: "synthetic-presentation-fixture",
  status: "CANDIDATES",
  created_at: "2026-10-31T09:42:08Z",
  last_analyzed_at: "2026-10-31T09:42:08Z",
  result: {
    incident_id: IDs.incident,
    status: "CANDIDATES",
    candidates: [{
      cause_type: "LINK_FAILURE",
      target_kind: "LINK",
      target_id: IDs.failedLink,
      score: 20,
      score_kind: "UNCALIBRATED_RULE_POINTS",
      explanation: "The stored down uplink is the earliest directly referenced failure and is supported by packet-loss evidence.",
      contributions: [
        { rule: "DIRECT_FAILURE", points: 4, evidence: [{ source_type: "EVENT", source_id: IDs.failureEvent, timestamp: "2026-10-31T09:42:00Z", reason: "INITIAL_FAILURE" }] },
        { rule: "INDEPENDENT_DIRECT_EVIDENCE", points: 4, evidence: [{ source_type: "ANOMALY", source_id: IDs.anomaly, timestamp: "2026-10-31T09:42:02Z", metric_id: IDs.lossMetric, reason: "PACKET_LOSS" }] },
        { rule: "LATER_RELATED_SYMPTOM", points: 2, evidence: [{ source_type: "EVENT", source_id: IDs.timeoutEvent, timestamp: "2026-10-31T09:42:03Z", reason: "DOWNSTREAM_SYMPTOM" }] },
      ],
      supporting_evidence: [
        { source_type: "EVENT", source_id: IDs.failureEvent, timestamp: "2026-10-31T09:42:00Z", reason: "INITIAL_FAILURE" },
        { source_type: "ANOMALY", source_id: IDs.anomaly, timestamp: "2026-10-31T09:42:02Z", reason: "PACKET_LOSS" },
      ],
      contradictory_evidence: [],
      limitations: ["SYNTHETIC_PRESENTATION_FIXTURE", "RULE_SCORE_IS_NOT_A_PROBABILITY"],
    }],
    limitations: ["SYNTHETIC_PRESENTATION_FIXTURE", "RULE_SCORE_IS_NOT_A_PROBABILITY"],
    evidence_count: 4,
    analysis_version: "RULES_V1",
  },
};

const impact: ImpactRun = {
  id: "32d22e0a-b56b-5793-9fbb-122902d34e4b",
  rca_run_id: rca.id,
  analysis_version: "IMPACT_RULES_V1",
  input_fingerprint: "synthetic-presentation-impact-input",
  topology_fingerprint: "synthetic-presentation-topology",
  status: "ASSESSED",
  created_at: "2026-10-31T09:42:09Z",
  last_analyzed_at: "2026-10-31T09:42:09Z",
  result: {
    incident_id: IDs.incident,
    rca_run_id: rca.id,
    status: "ASSESSED",
    candidate_target_kind: "LINK",
    candidate_target_id: IDs.failedLink,
    entities: [
      { kind: "LINK", id: IDs.failedLink, classification: "OBSERVED", evidence: [{ source_type: "EVENT", source_id: IDs.failureEvent, timestamp: "2026-10-31T09:42:00Z", reason: "DIRECT_FAILURE" }], explanation: "The s1-to-s2 link is directly reported down by validated incident evidence." },
      { kind: "DEVICE", id: IDs.switch1, classification: "POTENTIAL", evidence: [{ source_type: "EVENT", source_id: IDs.failureEvent, timestamp: "2026-10-31T09:42:00Z", reason: "DIRECT_FAILURE" }], explanation: "s1 is a physical endpoint of the observed failed link." },
      { kind: "DEVICE", id: IDs.switch2, classification: "POTENTIAL", evidence: [{ source_type: "EVENT", source_id: IDs.failureEvent, timestamp: "2026-10-31T09:42:00Z", reason: "DIRECT_FAILURE" }], explanation: "s2 is a physical endpoint of the observed failed link." },
      { kind: "SERVICE", id: IDs.service, classification: "POTENTIAL", evidence: [{ source_type: "EVENT", source_id: IDs.failureEvent, timestamp: "2026-10-31T09:42:00Z", reason: "DIRECT_FAILURE" }], explanation: "The synthetic checkout service is mapped to an exposed endpoint; outage is not confirmed." },
    ],
    chain: [
      { step: 1, source_kind: "LINK", source_id: IDs.failedLink, target_kind: "DEVICE", target_id: IDs.switch1, relationship: "LINK_ENDPOINT", classification: "POTENTIAL", evidence: [{ source_type: "EVENT", source_id: IDs.failureEvent, timestamp: "2026-10-31T09:42:00Z", reason: "DIRECT_FAILURE" }], explanation: "The canonical physical topology records s1 as an endpoint." },
      { step: 1, source_kind: "LINK", source_id: IDs.failedLink, target_kind: "DEVICE", target_id: IDs.switch2, relationship: "LINK_ENDPOINT", classification: "POTENTIAL", evidence: [{ source_type: "EVENT", source_id: IDs.failureEvent, timestamp: "2026-10-31T09:42:00Z", reason: "DIRECT_FAILURE" }], explanation: "The canonical physical topology records s2 as an endpoint." },
      { step: 2, source_kind: "DEVICE", source_id: IDs.switch2, target_kind: "SERVICE", target_id: IDs.service, relationship: "HOSTS_SERVICE", classification: "POTENTIAL", evidence: [{ source_type: "EVENT", source_id: IDs.failureEvent, timestamp: "2026-10-31T09:42:00Z", reason: "DIRECT_FAILURE" }], explanation: "The fixture maps the checkout service to s2; this is structural exposure only." },
    ],
    affected_devices: 2,
    affected_links: 1,
    affected_services: 1,
    user_application_impact: "UNKNOWN_UNVERIFIED",
    topology_input: { source: "SYNTHETIC_PRESENTATION_FIXTURE", hop_limit: 1 },
    limitations: ["SYNTHETIC_PRESENTATION_FIXTURE", "CUSTOMER_IMPACT_NOT_EXTERNALLY_CONFIRMED"],
    analysis_version: "IMPACT_RULES_V1",
  },
};

const context: IncidentTopologyContext = {
  incident_id: IDs.incident,
  source: "stored",
  evidence: [
    { kind: "EVENT", id: IDs.failureEvent, device_id: IDs.switch1, link_id: IDs.failedLink, device_found: true, link_found: true },
    { kind: "EVENT", id: IDs.timeoutEvent, device_id: IDs.server, device_found: true },
    { kind: "ANOMALY", id: IDs.anomaly, device_id: IDs.switch1, link_id: IDs.failedLink, device_found: true, link_found: true },
  ],
  referenced_device_ids: [IDs.switch1, IDs.server],
  referenced_link_ids: [IDs.failedLink],
  context_device_ids: labScenario.nodes.map((node) => node.id),
  context_link_ids: labScenario.links.map((link) => link.id),
  missing_device_ids: [],
  missing_link_ids: [],
  unmapped_service_ids: ["checkout-api"],
};

const monitoring: Monitoring = {
  observed_at: observedAt,
  topology_name: labScenario.name,
  network_state: "SYNTHETIC_DEMO",
  collection_status: "FIXTURE_LOADED",
  devices: [
    { name: "s1", device_type: "SWITCH", interfaces: [{ name: "s1-eth1", status: "UP", rx_errors: 0, tx_errors: 2 }, { name: "s1-eth2", status: "DOWN", rx_errors: 1842, tx_errors: 916 }] },
    { name: "s2", device_type: "SWITCH", interfaces: [{ name: "s2-eth1", status: "DOWN", rx_errors: 44, tx_errors: 128 }, { name: "s2-eth2", status: "UP", rx_errors: 0, tx_errors: 1 }, { name: "s2-eth3", status: "UP", rx_errors: 0, tx_errors: 3 }] },
    { name: "h1", device_type: "HOST", interfaces: [{ name: "h1-eth0", status: "UP", rx_errors: 0, tx_errors: 0 }] },
    { name: "h2", device_type: "HOST", interfaces: [{ name: "h2-eth0", status: "UP", rx_errors: 0, tx_errors: 0 }] },
    { name: "server1", device_type: "SERVER", interfaces: [{ name: "server1-eth0", status: "UP", rx_errors: 0, tx_errors: 3 }] },
  ],
  links: labScenario.links.map((link) => ({ source: link.source, destination: link.destination, status: link.key === "s1--s2" ? "DOWN" : "UP" })),
  errors: ["SYNTHETIC_PRESENTATION_DATA"],
};

const network: NetworkStatus = {
  available: false,
  state: "DISABLED",
  topology_name: labScenario.name,
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
      summary: [{ claim_id: "DEMO-C001", text: "The s1-to-s2 link failure preceded packet loss and downstream checkout timeouts on server1.", evidence_references: [{ source_type: "EVENT", source_id: IDs.failureEvent }, { source_type: "ANOMALY", source_id: IDs.anomaly }] }],
      observed_facts: [{ claim_id: "DEMO-C002", text: "The uplink is down and packet loss reached 100% in the synthetic evidence set.", evidence_references: [{ source_type: "EVENT", source_id: IDs.failureEvent }, { source_type: "METRIC", source_id: IDs.lossMetric }] }],
      candidate_explanations: [{ claim_id: "DEMO-C003", text: "The deterministic rules rank the failed uplink as the leading candidate; the score is not a probability.", evidence_references: [{ source_type: "EVENT", source_id: IDs.failureEvent }] }],
      failure_chain_explanation: [{ claim_id: "DEMO-C004", text: "The canonical topology supports a potential path from the failed inter-switch link to server1 and the checkout service.", evidence_references: [{ source_type: "EVENT", source_id: IDs.timeoutEvent }] }],
      uncertainties: [{ claim_id: "DEMO-C005", text: "External customer impact was not independently measured.", evidence_references: [] }],
      limitations: [{ claim_id: "DEMO-C006", text: "This explanation is a static presentation fixture; no Gemini request was made.", evidence_references: [] }],
      provider: "STATIC_PRESENTATION_FIXTURE",
    },
  };
  throw new PresentationDemoError("This resource is not part of the synthetic presentation scenario.", 404, "DEMO_RESOURCE_NOT_FOUND");
}
