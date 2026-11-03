"use client";

import type { Incident, IncidentDetail, RcaCandidate, RcaEvidenceReference, RcaRun } from "@/lib/api";

type Props = {
  incidents: Incident[];
  selectedId?: string;
  detail?: IncidentDetail;
  result?: RcaRun;
  loading: boolean;
  running: boolean;
  error?: string;
  presentationMode: boolean;
  onSelect: (id: string) => void;
  onRun: (id: string) => void;
  onOpenTopology: () => void;
};

function time(value?: string | null) {
  if (!value) return "—";
  const parsed = new Date(value);
  return Number.isNaN(parsed.valueOf()) ? value : parsed.toLocaleString();
}

function EvidenceList({ title, values, empty }: { title: string; values: RcaEvidenceReference[]; empty: string }) {
  return <section className="rca-evidence-column"><h4>{title}</h4>{values.length === 0 ? <p className="muted">{empty}</p> : <div className="relationship-list">{values.map((item, index) => <span key={`${item.source_type}-${item.source_id}-${index}`}><strong>{item.source_type} · {item.reason.replaceAll("_", " ")}</strong><small>{item.source_id}</small><small>{time(item.timestamp)}{item.metric_id ? ` · metric ${item.metric_id}` : ""}</small></span>)}</div>}</section>;
}

function CandidateCard({ candidate, rank }: { candidate: RcaCandidate; rank: number }) {
  return <article className="rca-candidate">
    <div className="rca-candidate-heading"><div><span className="badge neutral">RANK {rank}</span><h3>{candidate.cause_type.replaceAll("_", " ")}</h3></div><div className="rca-score"><strong>{candidate.score}</strong><span>rule points</span></div></div>
    <p>{candidate.explanation}</p>
    <dl className="rca-target"><div><dt>Target</dt><dd>{candidate.target_kind} · {candidate.target_id}</dd></div><div><dt>Score meaning</dt><dd>Uncalibrated deterministic points, not probability or confidence</dd></div></dl>
    <section className="rca-contributions"><h4>Rule contributions</h4>{candidate.contributions.length === 0 ? <p className="muted">No scored contribution was returned.</p> : candidate.contributions.map((item, index) => <div key={`${item.rule}-${index}`}><strong>{item.points > 0 ? "+" : ""}{item.points}</strong><span>{item.rule.replaceAll("_", " ")}</span><small>{item.evidence.length} evidence reference{item.evidence.length === 1 ? "" : "s"}</small></div>)}</section>
    <div className="rca-evidence-grid"><EvidenceList title="Supporting evidence" values={candidate.supporting_evidence} empty="No supporting reference was returned." /><EvidenceList title="Contradictory evidence" values={candidate.contradictory_evidence} empty="No contradiction was recorded." /></div>
    {candidate.limitations.length > 0 && <p className="rca-limitations"><strong>Candidate limitations:</strong> {candidate.limitations.join("; ")}</p>}
  </article>;
}

export function RcaLab({ incidents, selectedId, detail, result, loading, running, error, presentationMode, onSelect, onRun, onOpenTopology }: Props) {
  const selected = incidents.find((incident) => incident.id === selectedId);
  const evidenceCount = detail ? detail.events.length + detail.anomalies.length : 0;
  return <div className="dashboard-content rca-lab">
    <section className="panel rca-brief"><div><p className="eyebrow">SEMESTER PHASE 8</p><h2>Deterministic root-cause investigation</h2><p className="muted">Analyze one stored incident using its validated memberships and stored physical topology. Candidates remain hypotheses for human review.</p></div><div className="rca-boundary"><strong>{presentationMode ? "Synthetic replay" : "Explicit analysis write"}</strong><span>{presentationMode ? "Static browser fixture; no database or model call." : "Requires loopback access, local control, and the RCA write flag."}</span></div></section>

    <section className="panel"><div><p className="eyebrow">INCIDENT SELECTION</p><h2>Choose evidence to investigate</h2></div>{incidents.length === 0 ? <p className="state-message">No stored incidents are available on the current page.</p> : <div className="rca-incident-list">{incidents.map((incident) => <button key={incident.id} className={incident.id === selectedId ? "active" : ""} onClick={() => onSelect(incident.id)}><span><strong>{incident.title}</strong><small>{incident.severity} · {incident.status} · {time(incident.start_time)}</small></span><span aria-hidden>›</span></button>)}</div>}</section>

    {error && <p className="state-message error-message" role="alert">{error}</p>}
    {selectedId && <section className="panel rca-workspace"><div className="rca-heading"><div><p className="eyebrow">INVESTIGATION INPUT</p><h2>{selected?.title ?? detail?.title ?? "Selected incident"}</h2></div>{detail && <span className="badge neutral">{evidenceCount} evidence records</span>}</div>
      {loading ? <p className="state-message" role="status">Loading incident evidence and latest RCA…</p> : !detail ? <p className="state-message">The selected incident detail is unavailable.</p> : <><p>{detail.description || "No incident description was recorded."}</p><div className="rca-input-summary"><article><strong>{detail.events.length}</strong><span>correlated events</span></article><article><strong>{detail.anomalies.length}</strong><span>correlated anomalies</span></article><article><strong>{result?.result.analysis_version ?? "RULES_V1"}</strong><span>deterministic rules</span></article></div><div className="action-row"><button className="button primary" disabled={running || evidenceCount === 0} onClick={() => onRun(selectedId)}>{running ? "Analyzing incident…" : presentationMode ? "Replay synthetic RCA" : "Run deterministic RCA"}</button><button className="button secondary" disabled={running} onClick={onOpenTopology}>Review stored topology context</button></div><p className="muted">The engine can return multiple ranked candidates or an honest inconclusive result. It does not confirm causation or execute remediation.</p></>}
    </section>}

    <section className="panel"><div className="rca-heading"><div><p className="eyebrow">ANALYSIS RESULT</p><h2>Ranked candidates and provenance</h2></div>{result && <span className={`badge ${result.status === "CANDIDATES" ? "good" : "neutral"}`}>{result.status}</span>}</div>
      {!selectedId ? <p className="state-message">Select an incident to review or run deterministic analysis.</p> : !result ? <p className="state-message">No current RCA result is available. Run analysis when the backend write flag is enabled.</p> : <><div className="rca-result-meta"><span>Evidence analyzed <strong>{result.result.evidence_count}</strong></span><span>Version <strong>{result.result.analysis_version}</strong></span><span>Last analyzed <strong>{time(result.last_analyzed_at)}</strong></span></div>{result.status === "INCONCLUSIVE" && <div className="notice rca-inconclusive"><strong>Inconclusive by design</strong><span>The stored evidence did not support a candidate above the deterministic threshold. No cause was invented.</span></div>}{result.result.candidates.length > 0 ? <div className="rca-candidate-list">{result.result.candidates.map((candidate, index) => <CandidateCard key={`${candidate.target_kind}-${candidate.target_id}`} candidate={candidate} rank={index + 1} />)}</div> : <p className="state-message">No supported candidate was produced.</p>}{result.result.limitations.length > 0 && <div className="rca-run-limitations"><strong>Run limitations</strong><ul>{result.result.limitations.map((item) => <li key={item}>{item}</li>)}</ul></div>}</>}
    </section>
  </div>;
}
