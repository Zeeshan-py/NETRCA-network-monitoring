"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import {
  correlateEvidence, generateIncidentExplanation, getApiHealth, getIncident, getIncidentImpact, getIncidentRca,
  getIncidentTopologyContext, getMonitoring, getNetworkStatus, getPage, getTopology, getTopologyGraph, runIncidentImpact,
  runIncidentRca, type EvidenceRecord, type GraphSource, type GraphSummary, type Incident, type IncidentDetail,
  type IncidentTopologyContext, type Monitoring, type NetworkStatus, type Page, type Topology,
} from "@/lib/api";
import { TopologyExplorer, type TopologySelection } from "@/components/topology-explorer";
import { TopologyEvidence } from "@/components/topology-evidence";

type Section = "Overview" | "Topology" | "Evidence" | "Anomalies" | "Incidents";
type ViewData = {
  api: boolean;
  network?: NetworkStatus;
  topology?: Topology;
  monitoring?: Monitoring;
  metrics?: Page<EvidenceRecord>;
  logs?: Page<EvidenceRecord>;
  events?: Page<EvidenceRecord>;
  anomalies?: Page<EvidenceRecord>;
  incidents?: Page<Incident>;
};
type IncidentAnalysis = { detail?: IncidentDetail; rca?: Record<string, unknown>; impact?: Record<string, unknown> };
type PageResource = "metrics" | "logs" | "events" | "anomalies" | "incidents";

const sections: Section[] = ["Overview", "Topology", "Evidence", "Anomalies", "Incidents"];

function message(error: unknown) {
  return error instanceof Error ? error.message : "The request could not be completed.";
}
function display(value: unknown) {
  if (value === null || value === undefined || value === "") return "—";
  if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") return String(value);
  return JSON.stringify(value);
}
function formatTime(value?: string) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? value : date.toLocaleString();
}
function errorText(error: unknown) { return message(error); }

function State({ loading, error, empty, children }: { loading?: boolean; error?: string; empty?: boolean; children: React.ReactNode }) {
  if (loading) return <p className="state-message" role="status">Loading from the NetRCA API…</p>;
  if (error) return <p className="state-message error-message" role="alert">{error}</p>;
  if (empty) return <p className="state-message">No stored records are available yet.</p>;
  return <>{children}</>;
}

export function Dashboard() {
  const [section, setSection] = useState<Section>("Overview");
  const [data, setData] = useState<ViewData>({ api: false });
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedId, setSelectedId] = useState<string>();
  const [analysis, setAnalysis] = useState<IncidentAnalysis>({});
  const [explanation, setExplanation] = useState<Record<string, unknown>>();
  const [incidentLoading, setIncidentLoading] = useState(false);
  const [pageLoading, setPageLoading] = useState<Partial<Record<PageResource, boolean>>>({});
  const [incidentError, setIncidentError] = useState<string>();
  const [actionMessage, setActionMessage] = useState<string>();
  const [actionError, setActionError] = useState<string>();
  const [topologySource, setTopologySource] = useState<GraphSource>("live");
  const [topologyGraph, setTopologyGraph] = useState<GraphSummary>();
  const [topologyGraphSource, setTopologyGraphSource] = useState<GraphSource>();
  const [topologyGraphLoading, setTopologyGraphLoading] = useState(false);
  const [topologyGraphError, setTopologyGraphError] = useState<string>();
  const [topologySelection, setTopologySelection] = useState<TopologySelection>();
  const [topologyEvidenceFocus, setTopologyEvidenceFocus] = useState<{ selection: TopologySelection; label: string }>();
  const [incidentTopology, setIncidentTopology] = useState<IncidentTopologyContext>();
  const [incidentTopologyTitle, setIncidentTopologyTitle] = useState<string>();
  const [incidentTopologyError, setIncidentTopologyError] = useState<string>();
  const [incidentTopologyLoading, setIncidentTopologyLoading] = useState(false);
  const [topologyReload, setTopologyReload] = useState(0);
  const controllerRef = useRef<AbortController | undefined>(undefined);
  const incidentControllerRef = useRef<AbortController | undefined>(undefined);
  const incidentTopologyControllerRef = useRef<AbortController | undefined>(undefined);
  const selectedIncidentIdRef = useRef<string | undefined>(undefined);
  const pageControllers = useRef<Partial<Record<PageResource, AbortController>>>({});
  const pageSequence = useRef<Partial<Record<PageResource, number>>>({});
  const loadSequence = useRef(0);

  const refresh = useCallback(async () => {
    controllerRef.current?.abort();
    Object.values(pageControllers.current).forEach((controller) => controller?.abort());
    pageControllers.current = {};
    pageSequence.current = {};
    setPageLoading({});
    const controller = new AbortController();
    controllerRef.current = controller;
    const sequence = ++loadSequence.current;
    setRefreshing(true);
    setErrors({});
    const tasks = {
      api: getApiHealth(controller.signal),
      network: getNetworkStatus(controller.signal),
      topology: getTopology(controller.signal),
      monitoring: getMonitoring(controller.signal),
      metrics: getPage<EvidenceRecord>("metrics", 1, 20, controller.signal),
      logs: getPage<EvidenceRecord>("logs", 1, 20, controller.signal),
      events: getPage<EvidenceRecord>("events", 1, 20, controller.signal),
      anomalies: getPage<EvidenceRecord>("anomalies", 1, 20, controller.signal),
      incidents: getPage<Incident>("incidents", 1, 20, controller.signal),
    };
    const entries = Object.entries(tasks) as [keyof ViewData, Promise<unknown>][];
    const results = await Promise.allSettled(entries.map(([, task]) => task));
    if (controller.signal.aborted || sequence !== loadSequence.current) return;
    const next: ViewData = { api: false };
    const nextErrors: Record<string, string> = {};
    results.forEach((result, index) => {
      const key = entries[index][0];
      if (result.status === "rejected") {
        nextErrors[key] = errorText(result.reason);
        return;
      }
      const payload = result.value as { data?: unknown };
      if (key === "api") next.api = true;
      else if (["metrics", "logs", "events", "anomalies", "incidents"].includes(key)) {
        (next as Record<string, unknown>)[key] = result.value;
      } else (next as Record<string, unknown>)[key] = payload.data;
    });
    setData(next);
    setErrors(nextErrors);
    setLoading(false);
    setRefreshing(false);
  }, []);

  useEffect(() => {
    if (section !== "Topology") return;
    const controller = new AbortController();
    setTopologyGraph(undefined);
    setTopologyGraphSource(undefined);
    setTopologyGraphError(undefined);
    setTopologyGraphLoading(true);
    getTopologyGraph(topologySource, controller.signal).then((result) => {
      if (controller.signal.aborted) return;
      setTopologyGraph(result.data);
      setTopologyGraphSource(topologySource);
    }).catch((error: unknown) => {
      if (!controller.signal.aborted) setTopologyGraphError(message(error));
    }).finally(() => {
      if (!controller.signal.aborted) setTopologyGraphLoading(false);
    });
    return () => controller.abort();
  }, [section, topologySource, topologyReload]);

  useEffect(() => {
    const timer = window.setTimeout(() => void refresh(), 0);
    return () => {
      window.clearTimeout(timer);
      controllerRef.current?.abort();
      incidentControllerRef.current?.abort();
      incidentTopologyControllerRef.current?.abort();
      Object.values(pageControllers.current).forEach((controller) => controller?.abort());
    };
  }, [refresh]);

  const loadIncident = useCallback(async (id: string) => {
    incidentControllerRef.current?.abort();
    incidentTopologyControllerRef.current?.abort();
    selectedIncidentIdRef.current = id;
    setIncidentTopologyError(undefined);
    setIncidentTopology(undefined);
    const controller = new AbortController();
    incidentControllerRef.current = controller;
    setSelectedId(id);
    setAnalysis({});
    setExplanation(undefined);
    setIncidentError(undefined);
    setIncidentLoading(true);
    const [detail, rca, impact] = await Promise.allSettled([
      getIncident(id, controller.signal), getIncidentRca(id, controller.signal), getIncidentImpact(id, controller.signal),
    ]);
    if (controller.signal.aborted || incidentControllerRef.current !== controller) return;
    const next: IncidentAnalysis = {};
    if (detail.status === "fulfilled") next.detail = detail.value;
    else setIncidentError(message(detail.reason));
    if (rca.status === "fulfilled") next.rca = rca.value.data;
    if (impact.status === "fulfilled") next.impact = impact.value.data;
    setAnalysis(next);
    setIncidentLoading(false);
  }, []);

  async function openIncidentTopology() {
    if (!selectedId) return;
    incidentTopologyControllerRef.current?.abort();
    const controller = new AbortController();
    incidentTopologyControllerRef.current = controller;
    const incidentId = selectedId;
    setIncidentTopologyLoading(true);
    setIncidentTopologyError(undefined);
    try {
      const result = await getIncidentTopologyContext(incidentId, controller.signal);
      if (controller.signal.aborted || selectedIncidentIdRef.current !== incidentId) return;
      setIncidentTopology(result.data);
      setIncidentTopologyTitle(selectedIncident?.title ?? "Selected incident");
      setTopologySource("stored");
      setTopologySelection(undefined);
      setTopologyEvidenceFocus(undefined);
      setSection("Topology");
    } catch (error) {
      if (!controller.signal.aborted && selectedIncidentIdRef.current === incidentId) setIncidentTopologyError(message(error));
    } finally {
      if (incidentTopologyControllerRef.current === controller) setIncidentTopologyLoading(false);
    }
  }

  function changeTopologySource(source: GraphSource) {
    if (source === topologySource) return;
    setTopologySource(source);
    setTopologySelection(undefined);
    setIncidentTopology(undefined);
    setIncidentTopologyTitle(undefined);
    setTopologyGraph(undefined);
    setTopologyGraphSource(undefined);
  }

  function openTopologyEvidence(selection: TopologySelection, label: string) {
    setTopologyEvidenceFocus({ selection, label });
    setSection("Evidence");
  }

  async function changePage(resource: PageResource, direction: -1 | 1) {
    const current = data[resource] as Page<EvidenceRecord | Incident> | undefined;
    if (!current) return;
    const targetPage = current.pagination.page + direction;
    if (targetPage < 1 || targetPage > current.pagination.pages) return;
    pageControllers.current[resource]?.abort();
    const controller = new AbortController();
    pageControllers.current[resource] = controller;
    const sequence = (pageSequence.current[resource] ?? 0) + 1;
    pageSequence.current[resource] = sequence;
    setPageLoading((previous) => ({ ...previous, [resource]: true }));
    setErrors((previous) => ({ ...previous, [resource]: "" }));
    try {
      const result = await getPage<EvidenceRecord | Incident>(resource, targetPage, 20, controller.signal);
      if (controller.signal.aborted || pageSequence.current[resource] !== sequence) return;
      setData((previous) => ({ ...previous, [resource]: result }));
    } catch (error) {
      if (controller.signal.aborted || pageSequence.current[resource] !== sequence) return;
      setErrors((previous) => ({ ...previous, [resource]: message(error) }));
    } finally {
      if (pageSequence.current[resource] === sequence) setPageLoading((previous) => ({ ...previous, [resource]: false }));
    }
  }

  async function performAction(label: string, action: () => Promise<unknown>) {
    setActionMessage(undefined);
    setActionError(undefined);
    try {
      await action();
      setActionMessage(label);
      await refresh();
      if (selectedId) await loadIncident(selectedId);
    } catch (error) {
      setActionError(message(error));
    }
  }

  const incidents = data.incidents?.data ?? [];
  const selectedIncident = incidents.find((item) => item.id === selectedId);
  const events = data.events?.data ?? [];
  const anomalyRecords = data.anomalies?.data ?? [];
  const metricRecords = data.metrics?.data ?? [];
  const logRecords = data.logs?.data ?? [];
  return (
    <div className="app-shell">
      <aside className="sidebar" aria-label="Application navigation">
        <Link className="brand" href="/" aria-label="NetRCA home">NET<span>RCA</span><small>NETWORK OPERATIONS</small></Link>
        <nav className="sidebar-group" aria-label="Workspace">
          <p className="eyebrow">WORKSPACE</p>
          {sections.map((item) => <button className={`nav-item ${section === item ? "selected" : ""}`} key={item} onClick={() => setSection(item)} aria-current={section === item ? "page" : undefined}>{item}</button>)}
        </nav>
        <div className="sidebar-note"><span className="note-dot" /> PHASE 17 / TOPOLOGY</div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div className="crumb">NETRCA <span>/</span> {section.toUpperCase()}</div>
          <div className="top-actions">
            <span className={`api-status ${data.api ? "up" : loading ? "loading" : "unavailable"}`} role="status">{data.api ? "API connected" : loading ? "Checking API…" : "API unavailable"}</span>
            <button className="button secondary" onClick={() => { setTopologyReload((value) => value + 1); void refresh(); }} disabled={refreshing}>{refreshing ? "Refreshing…" : "Refresh"}</button>
          </div>
        </header>

        <section className="hero compact-hero">
          <p className="eyebrow accent">LIVE DATA · LOCAL API</p>
          <h1>Network <em>operations.</em></h1>
          <p className="hero-description">Review current simulator state and stored evidence, then investigate incidents using the deterministic analysis already enabled by your backend configuration.</p>
        </section>

        {actionMessage && <p className="notice success-message" role="status">{actionMessage}</p>}
        {actionError && <p className="notice error-message" role="alert">{actionError}</p>}

        {section === "Overview" && <div className="dashboard-content">
          <div className="summary-grid">
            <SummaryCard label="SIMULATOR" value={data.network?.state ?? (errors.network ? "Unavailable" : "—")} detail={data.network?.topology_name ?? "Network status"} />
            <SummaryCard label="DEVICES" value={data.network?.device_count ?? data.topology?.nodes.length ?? "—"} detail={`${data.network?.link_count ?? data.topology?.links.length ?? 0} links`} />
            <SummaryCard label="ANOMALIES" value={data.anomalies?.pagination.total ?? "—"} detail={data.anomalies?.data.filter((item) => item.is_anomaly === true).length ? "Anomalies on latest page" : "Stored anomaly history"} />
            <SummaryCard label="INCIDENTS" value={data.incidents?.pagination.total ?? "—"} detail="Stored incident records" />
          </div>
          <div className="content-grid">
            <section className="panel">
              <PanelHeading eyebrow="NETWORK" title="Topology" />
              <State loading={loading} error={errors.topology} empty={!data.topology?.nodes.length}>
                <div className="table-wrap"><table><thead><tr><th>Device</th><th>Type</th><th>Status</th></tr></thead><tbody>{data.topology?.nodes.map((node) => <tr key={node.id}><td>{node.name ?? node.id}</td><td>{node.device_type}</td><td><StatusBadge value={node.status ?? node.state ?? "PRESENT"} /></td></tr>)}</tbody></table></div>
              </State>
            </section>
            <section className="panel">
              <PanelHeading eyebrow="INCIDENT RESPONSE" title="Recent incidents" />
              <State loading={loading} error={errors.incidents} empty={!incidents.length}>
                <div className="record-list">{incidents.slice(0, 5).map((incident) => <button className="record-row" key={incident.id} onClick={() => { setSection("Incidents"); void loadIncident(incident.id); }}><span><strong>{incident.title}</strong><small>{formatTime(incident.start_time)}</small></span><StatusBadge value={incident.severity} /></button>)}</div>
              </State>
            </section>
          </div>
          <section className="panel">
            <PanelHeading eyebrow="COLLECTION" title="Latest monitoring snapshot" />
            <State loading={loading} error={errors.monitoring} empty={!data.monitoring?.devices.length}>
              <p className="muted">{data.monitoring?.collection_status} · observed {formatTime(data.monitoring?.observed_at)} · network {data.monitoring?.network_state}</p>
              <div className="table-wrap"><table><thead><tr><th>Device</th><th>Interfaces</th><th>Errors</th></tr></thead><tbody>{data.monitoring?.devices.map((device) => <tr key={device.name}><td>{device.name} · {device.device_type}</td><td>{device.interfaces.map((item) => `${item.name}: ${item.status}`).join(", ") || "—"}</td><td>{device.interfaces.reduce((sum, item) => sum + (item.rx_errors ?? 0) + (item.tx_errors ?? 0), 0)}</td></tr>)}</tbody></table></div>
            </State>
          </section>
        </div>}

        {section === "Topology" && <section className="panel dashboard-content"><PanelHeading eyebrow="NETWORK GRAPH" title="Interactive topology" /><TopologyExplorer source={topologySource} onSourceChange={changeTopologySource} graph={topologyGraphSource === topologySource ? topologyGraph : undefined} loading={topologyGraphLoading} error={topologyGraphError} selection={topologySelection} onSelect={setTopologySelection} onOpenEvidence={openTopologyEvidence} onBrowseIncidents={() => setSection("Incidents")} incidentContext={incidentTopology} incidentTitle={incidentTopologyTitle} /></section>}

        {section === "Evidence" && topologyEvidenceFocus && <TopologyEvidence selection={topologyEvidenceFocus.selection} label={topologyEvidenceFocus.label} onBack={() => { setTopologyEvidenceFocus(undefined); setSection("Topology"); }} onBrowseIncidents={() => setSection("Incidents")} />}
        {section === "Evidence" && !topologyEvidenceFocus && <div className="dashboard-content">
          <EvidenceTable title="Metrics" records={metricRecords} loading={loading} error={errors.metrics} page={data.metrics?.pagination} pageLoading={pageLoading.metrics} onPage={(direction) => void changePage("metrics", direction)} timeKey="timestamp" valueKey="metric_type" detailKey="value" />
          <EvidenceTable title="Logs" records={logRecords} loading={loading} error={errors.logs} page={data.logs?.pagination} pageLoading={pageLoading.logs} onPage={(direction) => void changePage("logs", direction)} timeKey="timestamp" valueKey="severity" detailKey="message" />
          <EvidenceTable title="Events" records={events} loading={loading} error={errors.events} page={data.events?.pagination} pageLoading={pageLoading.events} onPage={(direction) => void changePage("events", direction)} timeKey="timestamp" valueKey="event_type" detailKey="message" />
          <section className="panel"><PanelHeading eyebrow="CONTROLLED ACTION" title="Correlate the displayed evidence" /><p className="muted">Submits the currently displayed page of stored events and anomalies. This creates or updates incident records only when the backend’s local-control and correlation-write settings allow it.</p><button className="button primary" disabled={!events.length && !anomalyRecords.length || loading || pageLoading.events || pageLoading.anomalies} onClick={() => void performAction("Correlation request completed. Refreshing stored incidents.", () => correlateEvidence(events.map((item) => item.id), anomalyRecords.map((item) => item.id)))}>Correlate current page</button></section>
        </div>}

        {section === "Anomalies" && <section className="panel dashboard-content"><PanelHeading eyebrow="PHASE 8" title="Detected anomalies" /><State loading={loading} error={errors.anomalies} empty={!anomalyRecords.length}><RecordTable records={anomalyRecords} /><PageControls page={data.anomalies?.pagination} loading={pageLoading.anomalies} onPage={(direction) => void changePage("anomalies", direction)} /></State></section>}

        {section === "Incidents" && <div className="dashboard-content incident-layout">
          <section className="panel"><PanelHeading eyebrow="PHASE 9" title="Incident history" /><State loading={loading} error={errors.incidents} empty={!incidents.length}>
            <div className="record-list">{incidents.map((incident) => <button key={incident.id} className={`record-row incident-choice ${selectedId === incident.id ? "active-record" : ""}`} onClick={() => void loadIncident(incident.id)}><span><strong>{incident.title}</strong><small>{incident.severity} · {incident.status} · {formatTime(incident.start_time)}</small></span><span aria-hidden>›</span></button>)}</div>
            <PageControls page={data.incidents?.pagination} loading={pageLoading.incidents} onPage={(direction) => void changePage("incidents", direction)} />
          </State></section>
          <section className="panel incident-detail"><PanelHeading eyebrow="INVESTIGATION" title={selectedIncident?.title ?? "Select an incident"} />
            {!selectedId && <p className="state-message">Choose an incident to load its original evidence and latest analysis.</p>}
            {selectedId && <State loading={incidentLoading} error={incidentError} empty={!analysis.detail}>
              {analysis.detail && <>
                <div className="incident-meta"><StatusBadge value={analysis.detail.severity} /><StatusBadge value={analysis.detail.status} /><span>Started {formatTime(analysis.detail.start_time)}</span></div>
                <p>{analysis.detail.description || "No incident description was recorded."}</p>
                <PanelHeading eyebrow="CORRELATED EVIDENCE" title="Original records" />
                <RecordTable records={[...analysis.detail.events.map((item) => ({ ...item, evidence_kind: "EVENT" })), ...analysis.detail.anomalies.map((item) => ({ ...item, evidence_kind: "ANOMALY" }))]} />
                {incidentTopologyError && <p className="state-message error-message" role="alert">{incidentTopologyError}</p>}
                <button className="button secondary" disabled={incidentTopologyLoading} onClick={() => void openIncidentTopology()}>{incidentTopologyLoading ? "Loading stored topology context…" : "Show evidence in stored topology"}</button>
                <div className="action-row"><button className="button primary" onClick={() => void performAction("RCA run completed.", () => runIncidentRca(selectedId))}>Run deterministic RCA</button><button className="button secondary" onClick={() => void performAction("Impact analysis completed.", () => runIncidentImpact(selectedId))}>Run impact analysis</button></div>
                <AnalysisPanel title="Root-cause analysis" value={analysis.rca} emptyLabel="No current RCA result is available. Run analysis if enabled on the backend." />
                <AnalysisPanel title="Impact and failure chain" value={analysis.impact} emptyLabel="No impact result is available. Run analysis after RCA if enabled on the backend." />
                <section className="analysis-block"><h3>Evidence-grounded explanation</h3><p className="muted">This explicit action sends the current validated incident context to the configured backend explanation provider. It may call Gemini if enabled. Nothing is sent automatically when you open or refresh an incident.</p><button className="button secondary" onClick={() => void generateIncidentExplanation(selectedId).then((response) => { setExplanation(response.data); setActionError(undefined); setActionMessage("Explanation generated from the currently validated incident evidence."); }).catch((error) => { setActionError(message(error)); setActionMessage(undefined); })}>Generate explanation</button>{explanation && <ExplanationPanel value={explanation} />}</section>
              </>}
            </State>}
          </section>
        </div>}

        <footer>NetRCA · Local API integration · Evidence and analysis remain sourced from the backend</footer>
      </main>
    </div>
  );
}

function SummaryCard({ label, value, detail }: { label: string; value: string | number; detail: string }) {
  return <article className="summary-card"><span className="eyebrow">{label}</span><strong>{value}</strong><small>{detail}</small></article>;
}
function PanelHeading({ eyebrow, title }: { eyebrow: string; title: string }) {
  return <div className="panel-heading"><p className="eyebrow">{eyebrow}</p><h2>{title}</h2></div>;
}
function StatusBadge({ value }: { value: string }) {
  const normalized = value.toUpperCase();
  const tone = ["DOWN", "FAILED", "CRITICAL", "CLOSED"].includes(normalized) ? "danger" : ["WARNING", "DEGRADED", "HIGH", "INVESTIGATING"].includes(normalized) ? "warning" : ["UP", "HEALTHY", "RUNNING", "RESOLVED"].includes(normalized) ? "good" : "neutral";
  return <span className={`badge ${tone}`}>{value.replaceAll("_", " ")}</span>;
}
function EvidenceTable({ title, records, loading, error, page, pageLoading, onPage, timeKey, valueKey, detailKey }: { title: string; records: EvidenceRecord[]; loading: boolean; error?: string; page?: Page<EvidenceRecord>["pagination"]; pageLoading?: boolean; onPage?: (direction: -1 | 1) => void; timeKey: string; valueKey: string; detailKey: string }) {
  return <section className="panel"><PanelHeading eyebrow="STORED PHASE 6 DATA" title={title} /><State loading={loading} error={error} empty={!records.length}><RecordTable records={records} timeKey={timeKey} valueKey={valueKey} detailKey={detailKey} /><PageControls page={page} loading={pageLoading} onPage={onPage} /></State></section>;
}
function PageControls({ page, loading, onPage }: { page?: Page<unknown>["pagination"]; loading?: boolean; onPage?: (direction: -1 | 1) => void }) {
  if (!page) return null;
  const first = page.total === 0 ? 0 : (page.page - 1) * page.limit + 1;
  const last = Math.min(page.page * page.limit, page.total);
  return <div className="pagination-controls"><span className="muted">Showing {first}–{last} of {page.total}</span><div><button className="button secondary" disabled={loading || page.page <= 1} onClick={() => onPage?.(-1)}>Previous</button><span className="muted">Page {page.page} of {Math.max(page.pages, 1)}</span><button className="button secondary" disabled={loading || page.page >= page.pages} onClick={() => onPage?.(1)}>Next</button></div></div>;
}
function RecordTable({ records, timeKey = "timestamp", valueKey = "event_type", detailKey = "message" }: { records: EvidenceRecord[]; timeKey?: string; valueKey?: string; detailKey?: string }) {
  if (!records.length) return <p className="state-message">No evidence is attached to this incident.</p>;
  return <div className="table-wrap"><table><thead><tr><th>Time</th><th>Kind</th><th>Source</th><th>Details</th><th>Severity</th></tr></thead><tbody>{records.map((record, index) => <tr key={`${display(record.id)}-${index}`}><td>{formatTime(typeof record[timeKey] === "string" ? record[timeKey] as string : undefined)}</td><td>{display(record.evidence_kind ?? record[valueKey])}</td><td>{display(record.device_id ? (record.device_id as string) : record.link_id ?? record.id)}</td><td>{display(record[detailKey] ?? record.metric_type ?? record.name)}</td><td>{record.severity ? <StatusBadge value={String(record.severity)} /> : "—"}</td></tr>)}</tbody></table></div>;
}
function AnalysisPanel({ title, value, emptyLabel }: { title: string; value?: Record<string, unknown>; emptyLabel: string }) {
  const data = value?.data && typeof value.data === "object" ? value.data as Record<string, unknown> : value;
  return <section className="analysis-block"><h3>{title}</h3>{!data ? <p className="muted">{emptyLabel}</p> : <AnalysisContent data={data} />}</section>;
}
function ExplanationPanel({ value }: { value: Record<string, unknown> }) {
  const labels: Array<[string, string]> = [["summary", "Summary"], ["observed_facts", "Observed evidence"], ["candidate_explanations", "Candidate explanations"], ["failure_chain_explanation", "Failure chain"], ["impact_explanation", "Impact"], ["uncertainties", "Uncertainties"], ["missing_evidence", "Missing evidence"], ["limitations", "Limitations"]];
  return <div className="explanation-claims">{labels.map(([key, label]) => {
    const claims = Array.isArray(value[key]) ? value[key] as Array<Record<string, unknown>> : [];
    return claims.length ? <section key={key}><strong>{label}</strong>{claims.map((claim, index) => <p key={String(claim.claim_id ?? index)}>{display(claim.text)} <small>Evidence references: {Array.isArray(claim.evidence_references) ? claim.evidence_references.length : 0}</small></p>)}</section> : null;
  })}<p className="muted">The backend response is evidence-linked and remains separate from deterministic RCA findings.</p></div>;
}
function AnalysisContent({ data }: { data: Record<string, unknown> }) {
  const result = data.result && typeof data.result === "object" ? data.result as Record<string, unknown> : data;
  const candidates = Array.isArray(result.candidates) ? result.candidates : [];
  const entities = Array.isArray(result.entities) ? result.entities : [];
  const chain = Array.isArray(result.chain) ? result.chain : [];
  const limitations = Array.isArray(result.limitations) ? result.limitations : [];
  return <>
    <p><strong>Status:</strong> {display(result.status ?? data.status)} {result.status === "INCONCLUSIVE" && <span className="muted">· No supported conclusion was produced.</span>}</p>
    {candidates.length > 0 && <div className="analysis-list"><strong>Root-cause candidates</strong>{candidates.map((item, index) => { const candidate = item as Record<string, unknown>; return <article key={index}><StatusBadge value={String(candidate.cause_type ?? "CANDIDATE")} /><p>{display(candidate.explanation)}</p><small>Rule score: {display(candidate.score)} · uncalibrated points, not probability</small><p className="muted">Supporting evidence: {Array.isArray(candidate.supporting_evidence) ? candidate.supporting_evidence.length : 0}; contradictory evidence: {Array.isArray(candidate.contradictory_evidence) ? candidate.contradictory_evidence.length : 0}</p></article>; })}</div>}
    {entities.length > 0 && <div className="analysis-list"><strong>Impact entities</strong>{entities.map((item, index) => { const entity = item as Record<string, unknown>; return <article key={index}><StatusBadge value={String(entity.classification ?? "POTENTIAL")} /><p>{display(entity.kind)} · {display(entity.id)}</p><small>{display(entity.explanation)}</small></article>; })}</div>}
    {chain.length > 0 && <div className="analysis-list"><strong>Potential failure chain</strong>{chain.map((item, index) => { const edge = item as Record<string, unknown>; return <article key={index}><small>Step {display(edge.step)} · {display(edge.classification)} · {display(edge.relationship)}</small><p>{display(edge.source_kind)} {display(edge.source_id)} → {display(edge.target_kind)} {display(edge.target_id)}</p></article>; })}</div>}
    <p className="muted">User/application impact: {display(result.user_application_impact ?? "Not supplied")}</p>
    {limitations.length > 0 && <p className="muted">Limitations: {limitations.map(display).join("; ")}</p>}
  </>;
}
