import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { LiveEvidenceCapture } from "./live-evidence-capture";
import type { Monitoring, ProbeReading } from "@/lib/api";

afterEach(cleanup);

const snapshot: Monitoring = {
  observed_at: "2026-11-02T10:00:00Z", topology_name: "netrca_lab_v1", network_state: "RUNNING",
  collection_status: "COMPLETE", counter_unit: "bytes_and_packets", errors: [],
  devices: [
    { name: "h1", device_type: "HOST", interfaces: [{ name: "h1-eth0", status: "UP", rx_bytes: 120, tx_bytes: 80, rx_packets: 4, tx_packets: 3, rx_errors: 0, tx_errors: 0 }] },
    { name: "h2", device_type: "HOST", interfaces: [{ name: "h2-eth0", status: "UP", rx_bytes: 80, tx_bytes: 120, rx_packets: 3, tx_packets: 4, rx_errors: 0, tx_errors: 0 }] },
    { name: "server1", device_type: "SERVER", interfaces: [{ name: "server1-eth0", status: "UP", rx_bytes: null, tx_bytes: null, rx_errors: null, tx_errors: null, error_code: "COUNTERS_UNAVAILABLE" }] },
  ],
  links: [{ source: "h1", destination: "s1", status: "UP", interface_source: "h1-eth0", interface_destination: "s1-eth1" }],
};

const probe: ProbeReading = {
  observed_at: "2026-11-02T10:01:00Z", source: "h1", destination: "h2",
  packets_sent: 2, packets_received: 2, packet_loss_percent: 0, latency_ms: 0.025, status: "REACHABLE",
};

test("renders timestamped counters, link state and measured probe provenance", () => {
  render(<LiveEvidenceCapture snapshot={snapshot} probe={probe} networkRunning presentationMode={false} onCapture={vi.fn()} onProbe={vi.fn()} />);
  expect(screen.getByText("Ephemeral Mininet observation")).toBeInTheDocument();
  expect(screen.getByText("bytes_and_packets")).toBeInTheDocument();
  expect(screen.getAllByText("120")).toHaveLength(2);
  expect(screen.getByText("h1 ↔ s1")).toBeInTheDocument();
  expect(screen.getByText(/h1 → h2: REACHABLE/)).toBeInTheDocument();
  expect(screen.getByText(/2 \/ 2 packets · 0% loss/)).toBeInTheDocument();
});

test("captures only when running and submits a bounded known-host probe", async () => {
  const capture = vi.fn();
  const runProbe = vi.fn();
  render(<LiveEvidenceCapture snapshot={snapshot} networkRunning presentationMode={false} onCapture={capture} onProbe={runProbe} />);
  fireEvent.click(screen.getByRole("button", { name: "Capture live snapshot" }));
  expect(capture).toHaveBeenCalledOnce();
  await waitFor(() => expect(screen.getAllByRole("combobox")[0]).toHaveValue("h1"));
  fireEvent.change(screen.getAllByRole("combobox")[1], { target: { value: "server1" } });
  fireEvent.click(screen.getByRole("button", { name: "Run bounded probe" }));
  expect(runProbe).toHaveBeenCalledWith("h1", "server1");
});

test("blocks live capture when stopped and labels presentation evidence as synthetic", () => {
  const { rerender } = render(<LiveEvidenceCapture networkRunning={false} presentationMode={false} onCapture={vi.fn()} onProbe={vi.fn()} />);
  expect(screen.getByRole("button", { name: "Capture live snapshot" })).toBeDisabled();
  expect(screen.getByText(/Start the Mininet lab/)).toBeInTheDocument();
  rerender(<LiveEvidenceCapture snapshot={snapshot} networkRunning={false} presentationMode onCapture={vi.fn()} onProbe={vi.fn()} />);
  expect(screen.getByText("Synthetic presentation fixture")).toBeInTheDocument();
  expect(screen.getByText("No live command was run.")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Capture live snapshot" })).not.toBeInTheDocument();
});
