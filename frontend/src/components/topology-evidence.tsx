"use client";

import { useEffect, useState } from "react";
import { getPage, type EvidenceRecord, type Page } from "@/lib/api";
import type { TopologySelection } from "./topology-explorer";

type Props = { selection: TopologySelection; label: string; onBack: () => void; onBrowseIncidents: () => void };
type Resource = "metrics" | "logs" | "events" | "anomalies";

function EvidenceResource({ resource, selection }: { resource: Resource; selection: TopologySelection }) {
  const [pageNumber, setPageNumber] = useState(1);
  const [result, setResult] = useState<{ key: string; page?: Page<EvidenceRecord>; error?: string }>();
  const requestKey = `${selection.kind}:${selection.id}:${resource}:${pageNumber}`;
  const loading = result?.key !== requestKey;
  const page = result?.key === requestKey ? result.page : undefined;
  const error = result?.key === requestKey ? result.error : undefined;

  useEffect(() => {
    const controller = new AbortController();
    const filter = selection.kind === "device" ? { deviceId: selection.id } : { linkId: selection.id };
    getPage<EvidenceRecord>(resource, pageNumber, 20, controller.signal, filter)
      .then((value) => { if (!controller.signal.aborted) setResult({ key: requestKey, page: value }); })
      .catch((failure: unknown) => { if (!controller.signal.aborted) setResult({ key: requestKey, error: failure instanceof Error ? failure.message : "Evidence request failed." }); });
    return () => controller.abort();
  }, [resource, selection.id, selection.kind, pageNumber, requestKey]);

  return <section className="panel topology-evidence-resource">
    <h3>{resource[0].toUpperCase() + resource.slice(1)}</h3>
    {loading ? <p className="state-message" role="status">Loading matching {resource}…</p>
      : error ? <p className="state-message error-message" role="alert">{error}</p>
        : !page?.data.length ? <p className="state-message">No {resource} reference this stored {selection.kind} on this page.</p>
          : <>
            <ul className="topology-evidence-list">{page.data.map((record) => <li key={record.id}>
              <strong>{String(record.event_type ?? record.metric_type ?? record.severity ?? resource)}</strong>
              <span>{typeof record.timestamp === "string" ? record.timestamp : typeof record.detected_at === "string" ? record.detected_at : "Timestamp unavailable"}</span>
              <p>{String(record.message ?? record.value ?? record.metric_type ?? "Stored evidence record")}</p>
              <small>Evidence ID: {record.id}</small>
            </li>)}</ul>
            <div className="pagination-controls"><span className="muted">Page {page.pagination.page} of {Math.max(1, page.pagination.pages)} · {page.pagination.total} matching</span><div>
              <button className="button secondary" disabled={pageNumber <= 1 || loading} onClick={() => setPageNumber((value) => value - 1)}>Previous</button>
              <button className="button secondary" disabled={pageNumber >= page.pagination.pages || loading} onClick={() => setPageNumber((value) => value + 1)}>Next</button>
            </div></div>
          </>}
  </section>;
}

export function TopologyEvidence({ selection, label, onBack, onBrowseIncidents }: Props) {
  const resources: Resource[] = selection.kind === "device" ? ["metrics", "logs", "events", "anomalies"] : ["metrics", "events"];
  return <div className="dashboard-content">
    <section className="panel">
      <p className="eyebrow">STORED TOPOLOGY REFERENCE</p>
      <h2>Evidence for {label}</h2>
      <p className="muted">These results are filtered by the selected stored {selection.kind} ID using existing API query fields. No incident association is inferred from proximity or topology alone.</p>
      <div className="action-row"><button className="button secondary" onClick={onBack}>Back to topology</button><button className="button secondary" onClick={onBrowseIncidents}>Browse incident history</button></div>
    </section>
    {resources.map((resource) => <EvidenceResource key={`${selection.kind}-${selection.id}-${resource}`} resource={resource} selection={selection} />)}
  </div>;
}
