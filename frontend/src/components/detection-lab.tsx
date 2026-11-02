"use client";

import { useMemo, useState } from "react";
import type { DetectionRun, EvidenceCollectionResult, EvidenceRecord, Monitoring } from "@/lib/api";

type Props = {
  snapshot?: Monitoring;
  metrics: EvidenceRecord[];
  collection?: EvidenceCollectionResult;
  detection?: DetectionRun;
  action?: "collect" | "probe" | "detect";
  error?: string;
  networkRunning: boolean;
  presentationMode: boolean;
  onCollect: () => void;
  onProbe: (source: string, destination: string) => void;
  onDetect: (metricIds: string[]) => void;
  onRefresh: () => void;
  onOpenAnomalies: () => void;
};

const supported = new Set(["LATENCY", "PACKET_LOSS", "AVAILABILITY", "INTERFACE_STATE", "LINK_STATE", "RX_ERRORS", "TX_ERRORS"]);

function display(value: unknown) {
  return value === null || value === undefined || value === "" ? "—" : String(value);
}

export function DetectionLab({ snapshot, metrics, collection, detection, action, error, networkRunning, presentationMode, onCollect, onProbe, onDetect, onRefresh, onOpenAnomalies }: Props) {
  const [selected, setSelected] = useState<string[]>([]);
  const hosts = useMemo(() => (snapshot?.devices ?? []).filter((device) => ["HOST", "SERVER"].includes(device.device_type)).map((device) => device.name), [snapshot]);
  const [requestedSource, setRequestedSource] = useState("");
  const [requestedDestination, setRequestedDestination] = useState("");
  const source = hosts.includes(requestedSource) ? requestedSource : hosts[0] ?? "";
  const destinationChoices = hosts.filter((host) => host !== source);
  const destination = destinationChoices.includes(requestedDestination) ? requestedDestination : destinationChoices[0] ?? "";
  const eligible = metrics.filter((metric) => supported.has(String(metric.metric_type ?? "")));
  const selectedEligible = selected.filter((id) => eligible.some((metric) => metric.id === id)).slice(0, 20);
  const busy = Boolean(action);

  function toggle(id: string) {
    setSelected((current) => current.includes(id) ? current.filter((value) => value !== id)
      : current.length < 20 ? [...current, id] : current);
  }

  if (presentationMode) {
    return <section className="panel detection-lab"><p className="eyebrow">SEMESTER PHASE 6</p><h2>Stored evidence and anomaly detection</h2><p className="state-message warning-message">Database writes and live detection controls are unavailable in the synthetic presentation. Its populated findings remain browser-only fixtures.</p></section>;
  }

  return <div className="dashboard-content detection-lab">
    <section className="panel detection-brief">
      <div><p className="eyebrow">SEMESTER PHASE 6</p><h2>Stored evidence and deterministic anomaly detection</h2><p className="muted">Explicitly store validated Mininet observations, then analyze selected stored metrics with inspectable threshold, baseline, or optional Isolation Forest methods.</p></div>
      <div className="detection-boundary"><strong>Explicit actions only</strong><span>No polling, automatic persistence, correlation, RCA, or Gemini calls.</span></div>
    </section>

    {error && <p className="state-message error-message" role="alert">{error}</p>}

    <section className="panel collection-panel">
      <div className="detection-heading"><div><p className="eyebrow">VALIDATED COLLECTION</p><h2>Persist live observations</h2></div><button className="button secondary" disabled={busy} onClick={onRefresh}>Refresh stored evidence</button></div>
      <p className="muted">These controls write only through the existing local pipeline when `NETRCA_PIPELINE_WRITES_ENABLED=true`, the database is reachable, and live node names map to active stored topology.</p>
      {!networkRunning && <p className="state-message warning-message">Start the Mininet lab before collecting a snapshot or probe. Existing stored metrics can still be analyzed below.</p>}
      <div className="collection-actions">
        <button className="button primary" disabled={!networkRunning || busy} onClick={onCollect}>{action === "collect" ? "Storing snapshot…" : "Store current snapshot"}</button>
        <label>Probe source<select aria-label="Stored probe source" value={source} disabled={!networkRunning || busy || hosts.length < 2} onChange={(event) => { setRequestedSource(event.target.value); setRequestedDestination(""); }}>{hosts.map((host) => <option key={host}>{host}</option>)}</select></label>
        <label>Probe destination<select aria-label="Stored probe destination" value={destination} disabled={!networkRunning || busy || hosts.length < 2} onChange={(event) => setRequestedDestination(event.target.value)}>{destinationChoices.map((host) => <option key={host}>{host}</option>)}</select></label>
        <button className="button secondary" disabled={!networkRunning || busy || !source || !destination} onClick={() => onProbe(source, destination)}>{action === "probe" ? "Storing probe…" : "Store bounded probe"}</button>
      </div>
      {collection && <div className="collection-result" role="status"><strong>Collection completed</strong><span>Observed {new Date(collection.observed_at).toLocaleString()}</span><span>{collection.metrics} metrics · {collection.events} events · {collection.duplicates} duplicates{collection.unmapped_links ? ` · ${collection.unmapped_links} unmapped links` : ""}</span>{collection.probe_status && <span>Probe status: {collection.probe_status}</span>}</div>}
    </section>

    <section className="panel metric-selection">
      <div className="detection-heading"><div><p className="eyebrow">STORED PHASE 6 METRICS</p><h2>Select evidence to analyze</h2></div><span className="badge neutral">{selectedEligible.length}/20 selected</span></div>
      <p className="muted">Only supported numerical evidence is selectable. Cumulative traffic counters are excluded because a single sample cannot establish a rate.</p>
      {!eligible.length ? <p className="state-message">No supported stored metrics are available on the current page.</p> : <div className="table-wrap"><table><thead><tr><th>Select</th><th>Time</th><th>Metric</th><th>Value</th><th>Source</th></tr></thead><tbody>{eligible.map((metric) => <tr key={metric.id}><td><input aria-label={`Select ${metric.metric_type} metric ${metric.id}`} type="checkbox" checked={selectedEligible.includes(metric.id)} disabled={busy || (!selectedEligible.includes(metric.id) && selectedEligible.length >= 20)} onChange={() => toggle(metric.id)} /></td><td>{display(metric.timestamp)}</td><td>{display(metric.metric_type)}</td><td>{display(metric.value)} {display(metric.unit)}</td><td>{display(metric.source)}</td></tr>)}</tbody></table></div>}
      <div className="action-row"><button className="button primary" disabled={!selectedEligible.length || busy} onClick={() => onDetect(selectedEligible)}>{action === "detect" ? "Analyzing…" : "Analyze selected metrics"}</button><small className="muted">Detection requests use `persist: false`; findings are returned for review and are not inserted into anomaly history.</small></div>
    </section>

    <section className="panel detection-results">
      <div className="detection-heading"><div><p className="eyebrow">DETERMINISTIC RESULTS</p><h2>Explainable findings</h2></div><button className="button secondary" onClick={onOpenAnomalies}>Open stored anomaly history</button></div>
      {!detection ? <p className="state-message">Select stored metrics and run detection to view findings.</p> : <><div className="detection-summary"><strong>{detection.anomalies_detected} anomalies</strong><span>{detection.items.length} evaluated · {detection.insufficient_data} insufficient · {detection.persisted} persisted</span></div><div className="analysis-list">{detection.items.map((item) => <article key={`${item.metric_id ?? item.observation_key}-${item.metric_type}`}><div className="detection-result-heading"><span className={`badge ${item.status === "ANOMALY" ? "danger" : item.status === "NORMAL" ? "good" : "neutral"}`}>{item.status}</span>{item.severity && <span className="badge warning">{item.severity}</span>}</div><strong>{item.metric_type}: {display(item.value)} {item.unit}</strong><p>{item.reason}</p><small>{item.method} · score {display(item.score)} ({display(item.score_kind)}) · {item.baseline_samples} baseline samples</small><p className="muted">Persistence: {item.persistence}. Scores are method-specific strength, not probability.</p></article>)}</div></>}
    </section>
  </div>;
}
