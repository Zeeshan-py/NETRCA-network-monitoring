"use client";

import { useMemo, useState } from "react";
import type { FaultRecord, FaultRequest, FaultType, Monitoring } from "@/lib/api";

type Action = "refresh" | "inject" | "recover" | "reset";

type Props = {
  snapshot?: Monitoring;
  records: FaultRecord[];
  types: FaultType[];
  action?: Action;
  error?: string;
  networkRunning: boolean;
  presentationMode: boolean;
  onRefresh: () => void;
  onInject: (value: FaultRequest) => void;
  onRecover: (id: string) => void;
  onReset: () => void;
  onOpenEvidence: () => void;
};

const labels: Record<FaultType, string> = {
  INTERFACE_FAILURE: "Interface failure",
  LINK_FAILURE: "Link failure",
  PACKET_LOSS: "Packet loss",
  HIGH_LATENCY: "High latency",
};

function time(value: string) {
  const parsed = new Date(value);
  return Number.isNaN(parsed.valueOf()) ? value : parsed.toLocaleString();
}

export function FaultLab({ snapshot, records, types, action, error, networkRunning, presentationMode, onRefresh, onInject, onRecover, onReset, onOpenEvidence }: Props) {
  const [requestedType, setRequestedType] = useState<FaultType>("INTERFACE_FAILURE");
  const [requestedTarget, setRequestedTarget] = useState("");
  const [severity, setSeverity] = useState<FaultRequest["severity"]>("HIGH");
  const [duration, setDuration] = useState(30);
  const [packetLoss, setPacketLoss] = useState(50);
  const [latency, setLatency] = useState(50);

  const faultType = types.includes(requestedType) ? requestedType : types[0] ?? "INTERFACE_FAILURE";
  const interfaceTargets = useMemo(() => (snapshot?.devices ?? []).flatMap((device) =>
    device.interfaces.filter((item) => item.name !== "lo").map((item) => ({
      key: `${device.name}\u0000${item.name}`,
      device: device.name,
      interface: item.name,
      deviceType: device.device_type,
      status: item.operational_state ?? item.status,
    }))), [snapshot]);
  const shapingTargets = interfaceTargets.filter((target) => ["HOST", "SERVER"].includes(target.deviceType));
  const linkTargets = useMemo(() => (snapshot?.links ?? []).map((link) => ({
    key: `${link.source}\u0000${link.destination}`,
    source: link.source,
    destination: link.destination,
    status: link.status,
  })), [snapshot]);
  const targets = faultType === "LINK_FAILURE" ? linkTargets : faultType === "INTERFACE_FAILURE" ? interfaceTargets : shapingTargets;
  const selectedKey = targets.some((target) => target.key === requestedTarget) ? requestedTarget : targets[0]?.key ?? "";
  const active = records.find((record) => record.status === "ACTIVE");
  const busy = Boolean(action);
  const canInject = networkRunning && !presentationMode && !active && Boolean(selectedKey) && types.includes(faultType) && !busy;

  function submit() {
    if (!canInject) return;
    const selected = targets.find((target) => target.key === selectedKey);
    if (!selected) return;
    const base = { fault_type: faultType, duration_seconds: duration, severity } satisfies Partial<FaultRequest>;
    if (faultType === "LINK_FAILURE" && "source" in selected) {
      onInject({ ...base, fault_type: faultType, source: selected.source, destination: selected.destination } as FaultRequest);
      return;
    }
    if (!("device" in selected)) return;
    const parameters = faultType === "PACKET_LOSS" ? { packet_loss_percent: packetLoss }
      : faultType === "HIGH_LATENCY" ? { latency_ms: latency } : {};
    onInject({ ...base, fault_type: faultType, device: selected.device, interface: selected.interface, ...parameters } as FaultRequest);
  }

  if (presentationMode) {
    return <section className="panel fault-lab"><div><p className="eyebrow">CONTROLLED MININET LAB</p><h2>Fault demonstration</h2></div><p className="state-message warning-message">Fault controls are unavailable in the browser-only synthetic presentation. Start the approved Ubuntu WSL2 backend to run a real controlled failure.</p></section>;
  }

  return <div className="dashboard-content fault-lab">
    <section className="panel fault-brief">
      <div><p className="eyebrow">SEMESTER PHASE 5</p><h2>Controlled fault and observable failure</h2><p className="muted">Every target comes from the current canonical Mininet snapshot. Only one bounded fault can be active, and recovery restores captured pre-fault state.</p></div>
      <div className="fault-safety"><strong>Lab only</strong><span>No arbitrary commands, interfaces, IPs, or external targets.</span></div>
    </section>

    {error && <p className="state-message error-message" role="alert">{error}</p>}

    <section className="panel fault-controls">
      <div className="fault-heading"><div><p className="eyebrow">FAULT CONTROL</p><h2>Inject one bounded scenario</h2></div><button className="button secondary" disabled={busy} onClick={onRefresh}>{action === "refresh" ? "Refreshing…" : "Refresh safe targets"}</button></div>
      {!networkRunning && <p className="state-message warning-message">Start the Mininet lab from Topology before injecting a fault.</p>}
      {networkRunning && !snapshot?.devices.length && <p className="state-message warning-message">Refresh the live snapshot to load validated fault targets.</p>}
      {active && <div className="active-fault"><div><span className="eyebrow">ACTIVE FAULT</span><strong>{labels[active.fault_type]}</strong><small>{Object.values(active.target).join(" → ")} · expires {time(active.expires_at)}</small></div><span className="badge warning">{active.severity}</span></div>}

      <div className="fault-form">
        <label>Fault type<select aria-label="Fault type" value={faultType} disabled={busy || Boolean(active)} onChange={(event) => { setRequestedType(event.target.value as FaultType); setRequestedTarget(""); }}>{types.map((type) => <option key={type} value={type}>{labels[type]}</option>)}</select></label>
        <label>Validated target<select aria-label="Validated target" value={selectedKey} disabled={busy || Boolean(active) || !targets.length} onChange={(event) => setRequestedTarget(event.target.value)}>{targets.map((target) => <option key={target.key} value={target.key}>{"source" in target ? `${target.source} ↔ ${target.destination}` : `${target.device} · ${target.interface}`} ({target.status ?? "UNKNOWN"})</option>)}</select></label>
        <label>Severity<select aria-label="Fault severity" value={severity} disabled={busy || Boolean(active)} onChange={(event) => setSeverity(event.target.value as FaultRequest["severity"])}><option>LOW</option><option>MEDIUM</option><option>HIGH</option><option>CRITICAL</option></select></label>
        <label>Duration<select aria-label="Fault duration" value={duration} disabled={busy || Boolean(active)} onChange={(event) => setDuration(Number(event.target.value))}><option value={15}>15 seconds</option><option value={30}>30 seconds</option><option value={60}>60 seconds</option></select></label>
        {faultType === "PACKET_LOSS" && <label>Packet loss<select aria-label="Packet loss" value={packetLoss} disabled={busy || Boolean(active)} onChange={(event) => setPacketLoss(Number(event.target.value))}><option value={25}>25%</option><option value={50}>50%</option><option value={100}>100%</option></select></label>}
        {faultType === "HIGH_LATENCY" && <label>Added latency<select aria-label="Added latency" value={latency} disabled={busy || Boolean(active)} onChange={(event) => setLatency(Number(event.target.value))}><option value={25}>25 ms</option><option value={50}>50 ms</option><option value={100}>100 ms</option></select></label>}
      </div>
      <div className="action-row"><button className="button primary" disabled={!canInject} onClick={submit}>{action === "inject" ? "Injecting…" : "Inject controlled fault"}</button><button className="button secondary" disabled={!active || busy} onClick={() => active && onRecover(active.id)}>{action === "recover" ? "Recovering…" : "Recover active fault"}</button><button className="button secondary" disabled={!active || busy} onClick={onReset}>{action === "reset" ? "Resetting…" : "Reset fault controller"}</button><button className="button secondary" disabled={!networkRunning || busy} onClick={onOpenEvidence}>Capture post-fault evidence</button></div>
    </section>

    <section className="panel">
      <div><p className="eyebrow">IN-PROCESS HISTORY</p><h2>Fault lifecycle</h2><p className="muted">This list is authoritative for live restoration in the current backend process. Storage status is reported separately and is not assumed.</p></div>
      {!records.length ? <p className="state-message">No controlled faults have been run in this backend process.</p> : <div className="table-wrap"><table><thead><tr><th>Started</th><th>Type</th><th>Target</th><th>Status</th><th>Restoration</th><th>Storage</th></tr></thead><tbody>{records.map((record) => <tr key={record.id}><td>{time(record.started_at)}</td><td>{labels[record.fault_type]}</td><td>{Object.values(record.target).join(" → ")}</td><td><span className={`badge ${record.status === "ACTIVE" ? "warning" : record.status === "COMPLETED" ? "good" : "neutral"}`}>{record.status}</span></td><td>{record.restoration_result}</td><td>{record.storage_status}</td></tr>)}</tbody></table></div>}
    </section>
  </div>;
}
