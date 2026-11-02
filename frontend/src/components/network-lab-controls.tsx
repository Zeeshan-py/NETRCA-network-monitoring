"use client";

import type { Connectivity, NetworkStatus } from "@/lib/api";

type Props = {
  status?: NetworkStatus;
  action?: "start" | "reset" | "connectivity" | "stop";
  connectivity?: Connectivity;
  error?: string;
  presentationMode: boolean;
  onStart: () => void;
  onReset: () => void;
  onConnectivity: () => void;
  onStop: () => void;
};

const transitions = new Set<NetworkStatus["state"]>(["STARTING", "STOPPING", "RESETTING"]);

function actionLabel(action: NonNullable<Props["action"]>) {
  return { start: "Starting lab…", reset: "Resetting lab…", connectivity: "Testing connectivity…", stop: "Stopping lab…" }[action];
}

export function NetworkLabControls({ status, action, connectivity, error, presentationMode, onStart, onReset, onConnectivity, onStop }: Props) {
  const state = status?.state;
  const busy = Boolean(action || status?.operation || state && transitions.has(state));
  const running = state === "RUNNING";
  const stoppable = running || state === "FAILED";
  const unavailable = state === "DISABLED" || state === "UNAVAILABLE";

  return <section className="network-lab-controls" aria-label="Mininet lab controls">
    <div className="network-lab-heading">
      <div>
        <p className="eyebrow">CONTROLLED LAB</p>
        <h3>Mininet lifecycle</h3>
      </div>
      <span className={`badge ${running ? "good" : state === "FAILED" ? "danger" : unavailable ? "warning" : "neutral"}`}>{state ?? "UNKNOWN"}</span>
    </div>

    {presentationMode ? <p className="state-message">Browser-only presentation mode uses synthetic evidence and cannot control Mininet. Start the live Ubuntu backend to demonstrate the real lab.</p> : <>
      <div className="network-lab-facts">
        <span><strong>{status?.topology_name ?? "—"}</strong><small>Scenario</small></span>
        <span><strong>{status?.device_count ?? 0}</strong><small>Live devices</small></span>
        <span><strong>{status?.link_count ?? 0}</strong><small>Live links</small></span>
        <span><strong>{status?.started_at ? new Date(status.started_at).toLocaleTimeString() : "—"}</strong><small>Started</small></span>
      </div>
      <div className="action-row network-lab-actions">
        <button className="button primary" disabled={busy || state !== "STOPPED"} onClick={onStart}>Start lab</button>
        <button className="button secondary" disabled={busy || !running} onClick={onConnectivity}>Test connectivity</button>
        <button className="button secondary" disabled={busy || !running} onClick={onReset}>Reset topology</button>
        <button className="button danger-button" disabled={busy || !stoppable} onClick={onStop}>Stop lab</button>
      </div>
      {action && <p className="state-message" role="status">{actionLabel(action)}</p>}
      {unavailable && <p className="state-message">The API is available, but the simulator is disabled or Mininet is unavailable. Run the backend inside Ubuntu WSL2 with <code>NETRCA_SIMULATION_ENABLED=true</code>.</p>}
      {connectivity && <p className={`network-connectivity ${connectivity.connected ? "connected" : "disconnected"}`} role="status">
        <strong>{connectivity.connected ? "Connectivity passed" : "Connectivity failed"}</strong>
        <span>{connectivity.hosts.length} hosts · {connectivity.packet_loss_percent}% packet loss</span>
      </p>}
      {error && <p className="state-message error-message" role="alert">{error}</p>}
      {status?.last_operation && <p className="network-last-operation">Last operation: <strong>{status.last_operation}</strong>{status.last_result ? ` · ${status.last_result}` : ""}{status.detail ? ` · ${status.detail}` : ""}</p>}
    </>}
  </section>;
}
