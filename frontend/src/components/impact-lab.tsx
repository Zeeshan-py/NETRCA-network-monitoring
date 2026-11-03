"use client";

import type { ImpactEntity, ImpactRun, Incident, IncidentDetail, RcaEvidenceReference, RcaRun } from "@/lib/api";

type Props = {
  incidents: Incident[];
  selectedId?: string;
  detail?: IncidentDetail;
  rca?: RcaRun;
  result?: ImpactRun;
  loading: boolean;
  running: boolean;
  error?: string;
  presentationMode: boolean;
  onSelect: (id: string) => void;
  onRun: (id: string) => void;
  onOpenRca: () => void;
  onOpenTopology: () => void;
};

function time(value?: string | null) {
  if (!value) return "—";
  const parsed = new Date(value);
  return Number.isNaN(parsed.valueOf()) ? value : parsed.toLocaleString();
}

function evidenceLabel(values: RcaEvidenceReference[]) {
  if (values.length === 0) return "No direct evidence reference";
  return values.map((item) => `${item.source_type} ${item.source_id} · ${item.reason.replaceAll("_", " ")}`).join("; ");
}

function EntityCard({ entity }: { entity: ImpactEntity }) {
  return <article className={`impact-entity ${entity.classification.toLowerCase()}`}>
    <div><span className={`badge ${entity.classification === "OBSERVED" ? "good" : "neutral"}`}>{entity.classification}</span><strong>{entity.kind}</strong></div>
    <p className="mono-value">{entity.id}</p>
    <p>{entity.explanation}</p>
    <small>{evidenceLabel(entity.evidence)}</small>
  </article>;
}

export function ImpactLab({ incidents, selectedId, detail, rca, result, loading, running, error, presentationMode, onSelect, onRun, onOpenRca, onOpenTopology }: Props) {
  const selected = incidents.find((incident) => incident.id === selectedId);
  return <div className="dashboard-content impact-lab">
    <section className="panel impact-brief"><div><p className="eyebrow">SEMESTER PHASE 9</p><h2>Impact and failure-chain analysis</h2><p className="muted">Map an evidence-backed RCA candidate to observed components and conservative one-hop structural exposure. Potential does not mean confirmed outage.</p></div><div className="impact-boundary"><strong>{presentationMode ? "Synthetic replay" : "Explicit analysis write"}</strong><span>{presentationMode ? "Static browser fixture; no database, Mininet, or model call." : "Requires a stored RCA run, local control, and the impact write flag."}</span></div></section>

    <section className="panel"><div><p className="eyebrow">INCIDENT SELECTION</p><h2>Choose an investigation</h2></div>{incidents.length === 0 ? <p className="state-message">No stored incidents are available on the current page.</p> : <div className="impact-incident-list">{incidents.map((incident) => <button key={incident.id} className={incident.id === selectedId ? "active" : ""} onClick={() => onSelect(incident.id)}><span><strong>{incident.title}</strong><small>{incident.severity} · {incident.status} · {time(incident.start_time)}</small></span><span aria-hidden>›</span></button>)}</div>}</section>

    {error && <p className="state-message error-message" role="alert">{error}</p>}
    {selectedId && <section className="panel"><div className="impact-heading"><div><p className="eyebrow">ANALYSIS INPUT</p><h2>{selected?.title ?? detail?.title ?? "Selected incident"}</h2></div>{rca && <span className={`badge ${rca.status === "CANDIDATES" ? "good" : "neutral"}`}>RCA {rca.status}</span>}</div>
      {loading ? <p className="state-message" role="status">Loading incident, RCA, and latest impact result…</p> : !detail ? <p className="state-message">The selected incident detail is unavailable.</p> : <><p>{detail.description || "No incident description was recorded."}</p><div className="impact-prerequisites"><article><strong>{detail.events.length + detail.anomalies.length}</strong><span>incident evidence records</span></article><article><strong>{rca?.result.candidates.length ?? 0}</strong><span>RCA candidates</span></article><article><strong>{rca?.result.analysis_version ?? "Not analyzed"}</strong><span>RCA input version</span></article></div><div className="action-row"><button className="button primary" disabled={running || !rca} onClick={() => onRun(selectedId)}>{running ? "Analyzing exposure…" : presentationMode ? "Replay synthetic impact" : "Run impact analysis"}</button><button className="button secondary" onClick={onOpenRca}>Review RCA candidates</button><button className="button secondary" onClick={onOpenTopology}>Review stored topology</button></div>{!rca && <p className="state-message">Run deterministic RCA before impact analysis. The impact engine does not accept a caller-authored root cause.</p>}<p className="muted">The engine follows at most one physical hop and active device-service mappings. It does not infer traffic direction, customer count, or service outage.</p></>}
    </section>}

    <section className="panel"><div className="impact-heading"><div><p className="eyebrow">IMPACT RESULT</p><h2>Observed evidence and potential exposure</h2></div>{result && <span className={`badge ${result.status === "ASSESSED" ? "good" : "neutral"}`}>{result.status}</span>}</div>
      {!selectedId ? <p className="state-message">Select an incident to review or run impact analysis.</p> : !result ? <p className="state-message">No current impact result is available for the latest RCA run.</p> : <><div className="impact-summary"><article><strong>{result.result.affected_devices}</strong><span>devices in result</span></article><article><strong>{result.result.affected_links}</strong><span>links in result</span></article><article><strong>{result.result.affected_services}</strong><span>services in result</span></article><article><strong>UNKNOWN</strong><span>user/application impact</span></article></div><div className="impact-legend"><span><i className="observed" />Observed: directly reported by validated incident evidence</span><span><i className="potential" />Potential: structural exposure only, not confirmed failure</span></div>{result.status === "INCONCLUSIVE" && <div className="notice impact-inconclusive"><strong>Inconclusive by design</strong><span>The RCA or topology evidence could not support a defensible impact map. No affected entity was invented.</span></div>}{result.result.entities.length > 0 ? <div className="impact-entity-grid">{result.result.entities.map((entity) => <EntityCard key={`${entity.kind}-${entity.id}`} entity={entity} />)}</div> : <p className="state-message">No defensible affected entity was produced.</p>}

      <section className="impact-chain"><div><h3>Potential failure chain</h3><p className="muted">Steps order structural exposure outward from the candidate; they are not measured chronology.</p></div>{result.result.chain.length === 0 ? <p className="state-message">No supported structural chain was produced.</p> : <ol>{result.result.chain.map((edge, index) => <li key={`${edge.step}-${edge.source_id}-${edge.target_id}-${index}`}><span>{edge.step}</span><div><strong>{edge.source_kind} {edge.source_id}</strong><em>→ {edge.relationship.replaceAll("_", " ")} →</em><strong>{edge.target_kind} {edge.target_id}</strong><p>{edge.explanation}</p><small>{evidenceLabel(edge.evidence)}</small></div></li>)}</ol>}</section>

      <div className="impact-integrity"><strong>User/application impact: {result.result.user_application_impact.replaceAll("_", " ")}</strong><span>No incident-scoped customer or application observation exists, so NetRCA does not claim confirmed business impact.</span></div>{result.result.limitations.length > 0 && <div className="impact-limitations"><strong>Analysis limitations</strong><ul>{result.result.limitations.map((item) => <li key={item}>{item}</li>)}</ul></div>}<p className="muted">Last analyzed {time(result.last_analyzed_at)} · {result.result.analysis_version}</p></>}
    </section>
  </div>;
}
