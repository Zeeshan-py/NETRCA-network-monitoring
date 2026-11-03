"use client";

import type { ImpactRun, Incident, IncidentDetail, IncidentExplanation, RcaRun } from "@/lib/api";

type Props = {
  incidents: Incident[];
  selectedId?: string;
  detail?: IncidentDetail;
  rca?: RcaRun;
  impact?: ImpactRun;
  explanation?: IncidentExplanation;
  loading: boolean;
  generating: boolean;
  error?: string;
  presentationMode: boolean;
  onSelect: (id: string) => void;
  onGenerate: (id: string) => void;
  onOpenRca: () => void;
  onOpenImpact: () => void;
};

const sections = [
  ["summary", "Incident summary"],
  ["observed_facts", "Observed facts"],
  ["candidate_explanations", "Candidate explanation"],
  ["failure_chain_explanation", "Failure chain"],
  ["impact_explanation", "Impact"],
  ["uncertainties", "Uncertainties"],
  ["missing_evidence", "Missing evidence"],
  ["limitations", "Limitations"],
] as const;

function time(value?: string | null) {
  if (!value) return "—";
  const parsed = new Date(value);
  return Number.isNaN(parsed.valueOf()) ? value : parsed.toLocaleString();
}

export function ExplanationLab({ incidents, selectedId, detail, rca, impact, explanation, loading, generating, error, presentationMode, onSelect, onGenerate, onOpenRca, onOpenImpact }: Props) {
  const selected = incidents.find((incident) => incident.id === selectedId);
  return <div className="dashboard-content explanation-lab">
    <section className="panel explanation-brief"><div><p className="eyebrow">SEMESTER PHASE 10</p><h2>Evidence-grounded incident explanation</h2><p className="muted">Generate a readable narrative from validated deterministic findings while keeping every public sentence tied to server-authored claims and stored evidence.</p></div><div className="explanation-boundary"><strong>{presentationMode ? "Static explanation replay" : "Explicit Gemini request"}</strong><span>{presentationMode ? "Browser fixture only; Gemini and PostgreSQL are not contacted." : "Gemini may order claim IDs only. It cannot author facts, call tools, or change analysis."}</span></div></section>

    <section className="panel explanation-trust"><div><p className="eyebrow">TRUST BOUNDARY</p><h2>What the model can and cannot do</h2></div><div className="explanation-rule-grid"><article><strong>Backend authors claims</strong><span>Validated evidence, RCA, impact, uncertainty, and limitations become bounded claim records.</span></article><article><strong>Model orders IDs</strong><span>Gemini returns a complete ordering of supplied claim IDs—not free-form incident facts.</span></article><article><strong>Backend renders output</strong><span>Unknown, duplicate, omitted, malformed, or invented claims invalidate the response.</span></article><article><strong>Deterministic fallback</strong><span>RCA and impact remain available when Gemini is disabled, unavailable, or rejected.</span></article></div></section>

    <section className="panel"><div><p className="eyebrow">INCIDENT SELECTION</p><h2>Choose context to explain</h2></div>{incidents.length === 0 ? <p className="state-message">No stored incidents are available on the current page.</p> : <div className="explanation-incident-list">{incidents.map((incident) => <button key={incident.id} className={incident.id === selectedId ? "active" : ""} onClick={() => onSelect(incident.id)}><span><strong>{incident.title}</strong><small>{incident.severity} · {incident.status} · {time(incident.start_time)}</small></span><span aria-hidden>›</span></button>)}</div>}</section>

    {error && <p className="state-message error-message" role="alert">{error}</p>}
    {selectedId && <section className="panel"><div className="explanation-heading"><div><p className="eyebrow">GENERATION INPUT</p><h2>{selected?.title ?? detail?.title ?? "Selected incident"}</h2></div><div className="explanation-input-badges"><span className={`badge ${rca ? "good" : "neutral"}`}>RCA {rca ? rca.status : "REQUIRED"}</span><span className={`badge ${impact ? "good" : "neutral"}`}>IMPACT {impact ? impact.status : "OPTIONAL"}</span></div></div>
      {loading ? <p className="state-message" role="status">Loading validated incident context…</p> : !detail ? <p className="state-message">The selected incident detail is unavailable.</p> : <><p>{detail.description || "No incident description was recorded."}</p><div className="explanation-input-summary"><article><strong>{detail.events.length + detail.anomalies.length}</strong><span>incident evidence records</span></article><article><strong>{rca?.result.candidates.length ?? 0}</strong><span>deterministic candidates</span></article><article><strong>{impact?.result.entities.length ?? 0}</strong><span>impact entities</span></article></div><div className="action-row"><button className="button primary" disabled={generating || !rca} onClick={() => onGenerate(selectedId)}>{generating ? "Generating grounded explanation…" : presentationMode ? "Show static explanation" : "Generate explanation with Gemini"}</button><button className="button secondary" onClick={onOpenRca}>Review RCA</button><button className="button secondary" onClick={onOpenImpact}>Review impact</button></div>{!rca && <p className="state-message">A current deterministic RCA run is required. Gemini cannot replace root-cause analysis.</p>}<p className="muted">Nothing is sent automatically when the incident loads. Explanation output is ephemeral and is not saved to the database.</p></>}
    </section>}

    <section className="panel"><div className="explanation-heading"><div><p className="eyebrow">EXPLANATION OUTPUT</p><h2>Claims with evidence provenance</h2></div>{explanation && <span className="badge good">{explanation.explanation_version}</span>}</div>
      {!selectedId ? <p className="state-message">Select an incident before requesting an explanation.</p> : !explanation ? <p className="state-message">No explanation exists in this browser session. Generate one explicitly when the backend provider is enabled.</p> : <><div className="explanation-result-meta"><span>Model <strong>{explanation.model_name}</strong></span><span>RCA run <strong>{explanation.rca_run_id}</strong></span><span>Impact run <strong>{explanation.impact_run_id ?? "Not included"}</strong></span></div><div className="explanation-section-list">{sections.map(([key, label]) => { const claims = explanation[key]; return <section key={key} className={`explanation-section ${["uncertainties", "missing_evidence", "limitations"].includes(key) ? "caution" : ""}`}><h3>{label}</h3>{claims.length === 0 ? <p className="muted">No claims were supplied for this section.</p> : claims.map((claim) => <article key={claim.claim_id}><div><span className="badge neutral">{claim.claim_id}</span><p>{claim.text}</p></div><details><summary>{claim.evidence_references.length} evidence reference{claim.evidence_references.length === 1 ? "" : "s"}</summary><ul>{claim.evidence_references.map((reference, index) => <li key={`${reference.source_type}-${reference.source_id}-${index}`}><strong>{reference.source_type}</strong><span>{reference.source_id}</span><small>{time(reference.timestamp)}</small></li>)}</ul></details></article>)}</section>; })}</div><div className="explanation-integrity"><strong>Explanation integrity</strong><span>{explanation.evidence_references.length} unique evidence references · deterministic results remain authoritative · no remediation capability</span></div></>}
    </section>
  </div>;
}
