"use client";

import { useMemo, useState } from "react";
import type { Monitoring, ProbeReading } from "@/lib/api";

type Props = {
  snapshot?: Monitoring;
  probe?: ProbeReading;
  action?: "snapshot" | "probe";
  error?: string;
  networkRunning: boolean;
  presentationMode: boolean;
  onCapture: () => void;
  onProbe: (source: string, destination: string) => void;
};

function observedTime(value?: string) {
  if (!value) return "Not captured";
  const date = new Date(value);
  return Number.isNaN(date.valueOf()) ? value : date.toLocaleString();
}

function counter(value?: number | null) {
  return value === null || value === undefined ? "Unavailable" : value.toLocaleString();
}

export function LiveEvidenceCapture({ snapshot, probe, action, error, networkRunning, presentationMode, onCapture, onProbe }: Props) {
  const hosts = useMemo(() => snapshot?.devices.filter((device) => ["HOST", "SERVER"].includes(device.device_type)).map((device) => device.name) ?? [], [snapshot]);
  const [source, setSource] = useState("");
  const [destination, setDestination] = useState("");
  const selectedSource = hosts.includes(source) ? source : hosts[0] ?? "";
  const selectedDestination = hosts.includes(destination) && destination !== selectedSource
    ? destination : hosts.find((host) => host !== selectedSource) ?? "";

  return <section className="panel live-evidence-panel" aria-label="Live evidence capture">
    <div className="live-evidence-heading">
      <div><p className="eyebrow">RUNTIME OBSERVATION</p><h2>Live evidence capture</h2></div>
      <span className={`badge ${snapshot?.collection_status === "COMPLETE" ? "good" : snapshot?.collection_status === "PARTIAL" ? "warning" : "neutral"}`}>{snapshot?.collection_status ?? "NOT CAPTURED"}</span>
    </div>
    <p className="live-provenance"><strong>{presentationMode ? "Synthetic presentation fixture" : "Ephemeral Mininet observation"}</strong><span>{presentationMode ? "No live command was run." : "Read from the running lab; not written to PostgreSQL by this panel."}</span></p>

    {!presentationMode && <div className="action-row live-evidence-actions">
      <button className="button primary" disabled={!networkRunning || Boolean(action)} onClick={onCapture}>{action === "snapshot" ? "Capturing snapshot…" : "Capture live snapshot"}</button>
      {!networkRunning && <span className="muted">Start the Mininet lab from Topology before capturing evidence.</span>}
    </div>}

    {snapshot && <>
      <div className="evidence-metadata">
        <span><small>Observed at</small><strong>{observedTime(snapshot.observed_at)}</strong></span>
        <span><small>Topology</small><strong>{snapshot.topology_name}</strong></span>
        <span><small>Network state</small><strong>{snapshot.network_state}</strong></span>
        <span><small>Counter semantics</small><strong>{snapshot.counter_unit ?? "Not supplied"}</strong></span>
      </div>
      {snapshot.errors.length > 0 && <p className="notice warning-message">Limitations: {snapshot.errors.join(", ")}</p>}
      <div className="table-wrap"><table><thead><tr><th>Device / interface</th><th>State</th><th>RX bytes</th><th>TX bytes</th><th>Packets RX / TX</th><th>Errors RX / TX</th></tr></thead><tbody>
        {snapshot.devices.flatMap((device) => device.interfaces.map((item) => <tr key={`${device.name}:${item.name}`}><td><strong>{device.name}</strong> · {item.name}<small className="table-subtext">{device.device_type}</small></td><td><span className={`badge ${item.status === "UP" ? "good" : item.status === "DOWN" ? "danger" : "warning"}`}>{item.status}</span></td><td>{counter(item.rx_bytes)}</td><td>{counter(item.tx_bytes)}</td><td>{counter(item.rx_packets)} / {counter(item.tx_packets)}</td><td>{counter(item.rx_errors)} / {counter(item.tx_errors)}{item.error_code && <small className="table-subtext">{item.error_code}</small>}</td></tr>))}
      </tbody></table></div>
      <div className="live-link-list" aria-label="Observed links">{snapshot.links.map((link) => <span key={`${link.source}:${link.destination}`}><strong>{link.source} ↔ {link.destination}</strong><small>{link.status}{link.interface_source && link.interface_destination ? ` · ${link.interface_source} / ${link.interface_destination}` : ""}</small></span>)}</div>
    </>}

    {!presentationMode && snapshot && hosts.length >= 2 && <div className="probe-controls">
      <div><p className="eyebrow">BOUNDED PROBE</p><h3>Measure one approved host path</h3><p className="muted">Two ICMP packets within the canonical lab; this is route reachability, not long-term device uptime.</p></div>
      <label>Source<select value={selectedSource} onChange={(event) => setSource(event.target.value)}>{hosts.map((host) => <option key={host} value={host}>{host}</option>)}</select></label>
      <label>Destination<select value={selectedDestination} onChange={(event) => setDestination(event.target.value)}>{hosts.filter((host) => host !== selectedSource).map((host) => <option key={host} value={host}>{host}</option>)}</select></label>
      <button className="button secondary" disabled={!selectedSource || !selectedDestination || Boolean(action)} onClick={() => onProbe(selectedSource, selectedDestination)}>{action === "probe" ? "Running probe…" : "Run bounded probe"}</button>
    </div>}

    {probe && <div className={`probe-result ${probe.status === "REACHABLE" ? "reachable" : "unreachable"}`} role="status"><strong>{probe.source} → {probe.destination}: {probe.status}</strong><span>{counter(probe.packets_received)} / {counter(probe.packets_sent)} packets · {counter(probe.packet_loss_percent)}% loss · {counter(probe.latency_ms)} ms average latency</span><small>Observed {observedTime(probe.observed_at)}{probe.error_code ? ` · ${probe.error_code}` : ""}</small></div>}
    {error && <p className="state-message error-message" role="alert">{error}</p>}
  </section>;
}
