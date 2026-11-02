import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { DetectionLab } from "./detection-lab";
import type { Monitoring } from "@/lib/api";

afterEach(cleanup);

const snapshot: Monitoring = {
  observed_at: "2026-11-02T10:00:00Z", topology_name: "netrca_lab_v1", network_state: "RUNNING", collection_status: "COMPLETE", errors: [], links: [],
  devices: [{ name: "h1", device_type: "HOST", interfaces: [] }, { name: "server1", device_type: "SERVER", interfaces: [] }],
};
const metrics = [
  { id: "metric-1", metric_type: "PACKET_LOSS", value: 100, unit: "%", timestamp: "2026-11-02T10:00:00Z", source: "mininet_probe" },
  { id: "metric-2", metric_type: "RX_BYTES", value: 200, unit: "bytes", timestamp: "2026-11-02T10:00:00Z", source: "mininet_snapshot" },
];
const base = { snapshot, metrics, networkRunning: true, presentationMode: false, onCollect: vi.fn(), onProbe: vi.fn(), onDetect: vi.fn(), onRefresh: vi.fn(), onOpenAnomalies: vi.fn() };

test("stores only a bounded known-host probe", () => {
  const onProbe = vi.fn();
  render(<DetectionLab {...base} onProbe={onProbe} />);
  fireEvent.click(screen.getByRole("button", { name: "Store bounded probe" }));
  expect(onProbe).toHaveBeenCalledWith("h1", "server1");
});

test("excludes unsupported cumulative counters and analyzes selected stored IDs", () => {
  const onDetect = vi.fn();
  render(<DetectionLab {...base} onDetect={onDetect} />);
  expect(screen.getByText("PACKET_LOSS")).toBeInTheDocument();
  expect(screen.queryByText("RX_BYTES")).not.toBeInTheDocument();
  fireEvent.click(screen.getByLabelText("Select PACKET_LOSS metric metric-1"));
  fireEvent.click(screen.getByRole("button", { name: "Analyze selected metrics" }));
  expect(onDetect).toHaveBeenCalledWith(["metric-1"]);
});

test("labels scores as non-probability and hides controls in presentation mode", () => {
  const { rerender } = render(<DetectionLab {...base} detection={{ anomalies_detected: 1, insufficient_data: 0, persisted: 0, items: [{ metric_id: "metric-1", observation_key: "probe:key", metric_type: "PACKET_LOSS", value: 100, unit: "%", observed_at: "2026-11-02T10:00:00Z", status: "ANOMALY", method: "THRESHOLD", reason: "Packet loss exceeds 5%", severity: "CRITICAL", score: 1, score_kind: "THRESHOLD_STRENGTH", support: {}, baseline_samples: 0, persistence: "NOT_REQUESTED" }] }} />);
  expect(screen.getByText(/not probability/i)).toBeInTheDocument();
  expect(screen.getByText("Packet loss exceeds 5%")).toBeInTheDocument();
  rerender(<DetectionLab {...base} presentationMode />);
  expect(screen.queryByRole("button", { name: "Store current snapshot" })).not.toBeInTheDocument();
  expect(screen.getByText(/unavailable in the synthetic presentation/i)).toBeInTheDocument();
});
