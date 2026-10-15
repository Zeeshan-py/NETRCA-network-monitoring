"use client";

import { useMemo, useRef, useState } from "react";
import type { GraphSource, GraphSummary, IncidentTopologyContext } from "@/lib/api";
import { mapTopologyGraph } from "@/lib/topology-graph";

export type TopologySelection = { kind: "device" | "link"; id: string };

type Props = {
  source: GraphSource;
  onSourceChange: (source: GraphSource) => void;
  graph?: GraphSummary;
  loading: boolean;
  error?: string;
  selection?: TopologySelection;
  onSelect: (selection?: TopologySelection) => void;
  onOpenEvidence: (selection: TopologySelection, label: string) => void;
  onBrowseIncidents: () => void;
  incidentContext?: IncidentTopologyContext;
  incidentTitle?: string;
};

function statusTone(value: string) {
  const status = value.toUpperCase();
  if (["DOWN", "FAILED"].includes(status)) return "down";
  if (["WARNING", "DEGRADED"].includes(status)) return "warning";
  if (["HEALTHY", "UP"].includes(status)) return "up";
  return "unknown";
}

export function TopologyExplorer({ source, onSourceChange, graph, loading, error, selection, onSelect, onOpenEvidence, onBrowseIncidents, incidentContext, incidentTitle }: Props) {
  const layout = useMemo(() => graph ? mapTopologyGraph(graph) : undefined, [graph]);
  const nodesById = useMemo(() => new Map(layout?.nodes.map((node) => [node.id, node]) ?? []), [layout]);
  const selectedNode = selection?.kind === "device" ? nodesById.get(selection.id) : undefined;
  const selectedLink = selection?.kind === "link" ? layout?.edges.find((link) => link.id === selection.id) : undefined;
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const drag = useRef<{ x: number; y: number; originX: number; originY: number } | undefined>(undefined);
  const highlightedDevices = useMemo(() => new Set(incidentContext?.context_device_ids ?? []), [incidentContext]);
  const highlightedLinks = useMemo(() => new Set(incidentContext?.context_link_ids ?? []), [incidentContext]);

  function startPan(event: React.PointerEvent<SVGSVGElement>) {
    if (event.target !== event.currentTarget) return;
    drag.current = { x: event.clientX, y: event.clientY, originX: pan.x, originY: pan.y };
    event.currentTarget.setPointerCapture(event.pointerId);
  }
  function movePan(event: React.PointerEvent<SVGSVGElement>) {
    if (!drag.current) return;
    setPan({ x: drag.current.originX + (event.clientX - drag.current.x), y: drag.current.originY + (event.clientY - drag.current.y) });
  }
  function stopPan() { drag.current = undefined; }

  return <div className="topology-explorer">
    <div className="topology-toolbar">
      <div className="topology-source" role="group" aria-label="Topology source">
        <button className={`button ${source === "live" ? "primary" : "secondary"}`} aria-pressed={source === "live"} onClick={() => onSourceChange("live")}>Live Mininet</button>
        <button className={`button ${source === "stored" ? "primary" : "secondary"}`} aria-pressed={source === "stored"} onClick={() => onSourceChange("stored")}>Stored topology</button>
      </div>
      {graph && <div className="topology-summary" role="status">
        <span className={`badge ${graph.connected ? "good" : "warning"}`}>{graph.connected ? "CONNECTED" : "DISCONNECTED"}</span>
        <span>{layout?.nodes.length ?? 0} devices · {layout?.edges.length ?? 0} links · {layout?.components.length ?? 0} components</span>
        <span className="muted">Freshness timestamp is not supplied by this API.</span>
      </div>}
    </div>

    {incidentContext && <div className="notice context-notice" role="status">
      Showing stored graph context for <strong>{incidentTitle ?? "the selected incident"}</strong>. Highlighted devices and links come from the backend’s direct references and one-hop stored topology context.
      {(incidentContext.missing_device_ids.length > 0 || incidentContext.missing_link_ids.length > 0) && <span> {incidentContext.missing_device_ids.length + incidentContext.missing_link_ids.length} referenced element(s) are absent from the stored graph.</span>}
    </div>}

    {loading ? <p className="state-message" role="status">Loading {source} topology…</p>
      : error ? <p className="state-message error-message" role="alert">{error}</p>
        : !graph || !layout || layout.nodes.length === 0 ? <p className="state-message">No devices are available in the {source} topology.</p>
          : <>
            {layout.invalidEndpointCount > 0 && <p className="state-message error-message" role="alert">Partial graph: {layout.invalidEndpointCount} link(s) refer to devices absent from this topology response and are not drawn.</p>}
            <div className="topology-workspace">
              <section className="topology-canvas-panel" aria-label={`${source} network graph`}>
                <div className="graph-controls" aria-label="Graph controls">
                  <button className="button secondary" aria-label="Zoom out" onClick={() => setZoom((value) => Math.max(.4, value * .8))}>−</button>
                  <button className="button secondary" aria-label="Zoom in" onClick={() => setZoom((value) => Math.min(2.5, value * 1.25))}>+</button>
                  <button className="button secondary" onClick={() => { setZoom(1); setPan({ x: 0, y: 0 }); }}>Fit graph</button>
                  <span className="muted">Drag empty space to pan · scroll to zoom</span>
                </div>
                <svg className="topology-canvas" role="group" aria-label={`${source} topology graph with ${layout.nodes.length} devices and ${layout.edges.length} links`} viewBox={`0 0 ${layout.width} ${layout.height}`} style={{ width: Math.max(720, layout.width), height: Math.max(440, layout.height) }} onPointerDown={startPan} onPointerMove={movePan} onPointerUp={stopPan} onPointerCancel={stopPan} onWheel={(event) => { event.preventDefault(); setZoom((value) => Math.max(.4, Math.min(2.5, value * (event.deltaY < 0 ? 1.1 : .9)))); }}>
                  <g transform={`translate(${pan.x} ${pan.y}) scale(${zoom})`}>
                    {layout.edges.map((edge) => {
                      const from = nodesById.get(edge.source)!;
                      const to = nodesById.get(edge.target)!;
                      const active = selection?.kind === "link" && selection.id === edge.id;
                      const incident = highlightedLinks.has(edge.id);
                      return <g key={`${source}:${edge.graphId}`} role="button" tabIndex={0} aria-label={`Link ${edge.id}, ${from.name} to ${to.name}, status ${edge.status}`} aria-pressed={active} data-testid={`topology-link-${edge.id}`} onClick={() => onSelect({ kind: "link", id: edge.id })} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); onSelect({ kind: "link", id: edge.id }); } }} className={`graph-link graph-${statusTone(edge.status)} ${active ? "selected" : ""} ${incident ? "incident-context" : ""}`}>
                        <line x1={from.x + 55} y1={from.y + 27} x2={to.x + 55} y2={to.y + 27} />
                        <text x={(from.x + to.x) / 2 + 55} y={(from.y + to.y) / 2 + 18}>{edge.status}</text>
                      </g>;
                    })}
                    {layout.nodes.map((node) => {
                      const active = selection?.kind === "device" && selection.id === node.id;
                      const incident = highlightedDevices.has(node.id);
                      return <g key={`${source}:${node.graphId}`} role="button" tabIndex={0} aria-label={`Device ${node.name}, ${node.device_type}, status ${node.status}`} aria-pressed={active} data-testid={`topology-node-${node.id}`} onClick={() => onSelect({ kind: "device", id: node.id })} onKeyDown={(event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); onSelect({ kind: "device", id: node.id }); } }} className={`graph-device graph-${statusTone(node.status)} ${active ? "selected" : ""} ${incident ? "incident-context" : ""}`}>
                        <rect x={node.x} y={node.y} width="110" height="54" rx="10" />
                        <text x={node.x + 55} y={node.y + 23} className="graph-device-name">{node.name}</text>
                        <text x={node.x + 55} y={node.y + 41} className="graph-device-meta">{node.device_type} · {node.status}</text>
                      </g>;
                    })}
                  </g>
                </svg>
              </section>
              <aside className="panel topology-detail" aria-label="Selected topology details">
                <p className="eyebrow">SELECTION DETAILS</p>
                {!selection && <p className="state-message">Select a device or link to inspect the fields returned by the {source} topology API.</p>}
                {selectedNode && <>
                  <h3>{selectedNode.name}</h3>
                  <dl><dt>Type</dt><dd>{selectedNode.device_type}</dd><dt>Status</dt><dd><span className={`badge ${statusTone(selectedNode.status)}`}>{selectedNode.status}</span></dd><dt>Device ID</dt><dd className="mono-value">{selectedNode.id}</dd><dt>Data source</dt><dd>{source === "live" ? "Live Mininet runtime" : "Stored PostgreSQL topology"}</dd></dl>
                  {source === "stored" ? <button className="button primary" onClick={() => onOpenEvidence({ kind: "device", id: selectedNode.id }, selectedNode.name)}>Open related stored evidence</button> : <p className="muted">Runtime identifiers are separate from stored evidence IDs; no cross-source match is made.</p>}
                  <p className="muted">The topology API does not provide a device-to-incident lookup. Use incident history and its backend-validated topology context to inspect incident relationships.</p>
                  <button className="button secondary" onClick={onBrowseIncidents}>Browse incident history</button>
                </>}
                {selectedLink && <>
                  <h3>Link</h3>
                  <dl><dt>Endpoints</dt><dd>{nodesById.get(selectedLink.source)?.name} ↔ {nodesById.get(selectedLink.target)?.name}</dd><dt>Status</dt><dd><span className={`badge ${statusTone(selectedLink.status)}`}>{selectedLink.status}</span></dd><dt>Link ID</dt><dd className="mono-value">{selectedLink.id}</dd><dt>Data source</dt><dd>{source === "live" ? "Live Mininet runtime" : "Stored PostgreSQL topology"}</dd></dl>
                  {source === "stored" ? <button className="button primary" onClick={() => onOpenEvidence({ kind: "link", id: selectedLink.id }, `${nodesById.get(selectedLink.source)?.name} ↔ ${nodesById.get(selectedLink.target)?.name}`)}>Open related stored evidence</button> : <p className="muted">Runtime identifiers are separate from stored evidence IDs; no cross-source match is made.</p>}
                  <p className="muted">The topology API does not provide a link-to-incident lookup. Use incident history and its backend-validated topology context to inspect incident relationships.</p>
                  <button className="button secondary" onClick={onBrowseIncidents}>Browse incident history</button>
                </>}
                {selection && !selectedNode && !selectedLink && <p className="state-message">That selection is no longer part of the current topology.</p>}
                {incidentContext?.unmapped_service_ids.length ? <p className="muted">The backend reports {incidentContext.unmapped_service_ids.length} service reference(s) without a supported topology mapping.</p> : null}
              </aside>
            </div>
          </>}
  </div>;
}
