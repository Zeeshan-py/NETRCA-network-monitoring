"use client";

import { useState } from "react";
import type { CorrelationRun, EvidenceRecord } from "@/lib/api";

type Props = {
  events: EvidenceRecord[];
  anomalies: EvidenceRecord[];
  result?: CorrelationRun;
  running: boolean;
  error?: string;
  presentationMode: boolean;
  onCorrelate: (eventIds: string[], anomalyIds: string[]) => void;
  onRefresh: () => void;
  onOpenIncident: (id: string) => void;
};

function time(value: unknown) {
  if (typeof value !== "string") return "—";
  const parsed = new Date(value);
  return Number.isNaN(parsed.valueOf()) ? value : parsed.toLocaleString();
}

export function CorrelationLab({ events, anomalies, result, running, error, presentationMode, onCorrelate, onRefresh, onOpenIncident }: Props) {
  const [selectedEvents, setSelectedEvents] = useState<string[]>([]);
  const [selectedAnomalies, setSelectedAnomalies] = useState<string[]>([]);
  const selectedCount = selectedEvents.length + selectedAnomalies.length;

  function toggle(id: string, kind: "EVENT" | "ANOMALY") {
    const values = kind === "EVENT" ? selectedEvents : selectedAnomalies;
    const update = kind === "EVENT" ? setSelectedEvents : setSelectedAnomalies;
    update(values.includes(id) ? values.filter((value) => value !== id)
      : selectedCount < 100 ? [...values, id] : values);
  }

  return <div className="dashboard-content correlation-lab">
    <section className="panel correlation-brief">
      <div><p className="eyebrow">SEMESTER PHASE 7</p><h2>Evidence correlation and incident grouping</h2><p className="muted">Select validated stored evidence, then apply deterministic direct-relationship rules. Time proximity alone never creates an incident.</p></div>
      <div className="correlation-boundary"><strong>{presentationMode ? "Synthetic replay" : "Explicit database write"}</strong><span>{presentationMode ? "Browser fixtures only; no remote write." : "Requires local control and the correlation write flag."}</span></div>
    </section>

    {error && <p className="state-message error-message" role="alert">{error}</p>}

    <section className="panel correlation-rules">
      <div><p className="eyebrow">AUTHORITATIVE RULES</p><h2>What can establish a relationship</h2></div>
      <div className="rule-grid"><article><strong>Direct identity</strong><span>Same device, link, service, source event, or source metric.</span></article><article><strong>Known endpoint</strong><span>A stored link and one of its directly connected devices.</span></article><article><strong>Bounded time</strong><span>Evidence must also fit the configured correlation window and maximum age.</span></article><article><strong>Conservative separation</strong><span>Different explicit services, unrelated resources, stale evidence, and ambiguous memberships remain separate.</span></article></div>
    </section>

    <section className="panel evidence-picker">
      <div className="correlation-heading"><div><p className="eyebrow">STORED EVIDENCE</p><h2>Select evidence to group</h2></div><div className="action-row"><span className="badge neutral">{selectedCount}/100 selected</span><button className="button secondary" disabled={running} onClick={onRefresh}>Refresh evidence</button></div></div>
      {!events.length && !anomalies.length ? <p className="state-message">No stored events or anomalies are available on the current pages.</p> : <div className="correlation-evidence-grid">
        <div><h3>Events</h3>{!events.length ? <p className="state-message">No stored events.</p> : <div className="evidence-choice-list">{events.map((event) => <label key={event.id}><input type="checkbox" aria-label={`Select event ${event.id}`} checked={selectedEvents.includes(event.id)} disabled={running || (!selectedEvents.includes(event.id) && selectedCount >= 100)} onChange={() => toggle(event.id, "EVENT")} /><span><strong>{String(event.event_type ?? "EVENT")}</strong><small>{time(event.timestamp)} · {String(event.severity ?? "severity unavailable")}</small><small>{String(event.message ?? event.id)}</small></span></label>)}</div>}</div>
        <div><h3>Anomalies</h3>{!anomalies.length ? <p className="state-message">No stored anomalies.</p> : <div className="evidence-choice-list">{anomalies.map((anomaly) => <label key={anomaly.id}><input type="checkbox" aria-label={`Select anomaly ${anomaly.id}`} checked={selectedAnomalies.includes(anomaly.id)} disabled={running || (!selectedAnomalies.includes(anomaly.id) && selectedCount >= 100)} onChange={() => toggle(anomaly.id, "ANOMALY")} /><span><strong>{String(anomaly.name ?? anomaly.metric_type ?? "ANOMALY")}</strong><small>{time(anomaly.detected_at ?? anomaly.timestamp)} · {String(anomaly.severity ?? "severity unavailable")}</small><small>{anomaly.is_anomaly === false ? "Not marked anomalous" : String(anomaly.model_name ?? anomaly.id)}</small></span></label>)}</div>}</div>
      </div>}
      <div className="action-row"><button className="button primary" disabled={!selectedCount || running} onClick={() => onCorrelate(selectedEvents, selectedAnomalies)}>{running ? "Correlating…" : presentationMode ? "Replay synthetic correlation" : "Correlate selected evidence"}</button><small className="muted">Only selected IDs are submitted. Repeated runs are idempotent and may reuse a related open incident.</small></div>
    </section>

    <section className="panel correlation-results">
      <div><p className="eyebrow">GROUPING RESULT</p><h2>Incident assignments and reasons</h2></div>
      {!result ? <p className="state-message">Run correlation to inspect grounded memberships.</p> : <><div className="correlation-summary"><article><strong>{result.created}</strong><span>incidents created</span></article><article><strong>{result.attached}</strong><span>memberships attached</span></article><article><strong>{result.skipped_ids.length}</strong><span>evidence items skipped</span></article></div>{!result.incidents.length ? <p className="state-message">No incident group was produced. Unrelated or stale evidence remains separate.</p> : <div className="analysis-list">{result.incidents.map((incident) => <article key={incident.incident_id}><div className="correlation-heading"><div><span className={`badge ${incident.created ? "good" : "neutral"}`}>{incident.created ? "CREATED" : "REUSED"}</span><strong className="mono-value">{incident.incident_id}</strong></div><button className="button secondary" onClick={() => onOpenIncident(incident.incident_id)}>Open incident</button></div><div className="relationship-list">{incident.evidence.map((item) => <span key={`${item.kind}-${item.id}`}><strong>{item.kind}</strong><small>{item.reason.replaceAll("_", " ")} · {item.id}</small></span>)}</div></article>)}</div>}{result.skipped_ids.length > 0 && <p className="muted">Skipped evidence: {result.skipped_ids.join(", ")}</p>}</>}
    </section>
  </div>;
}
