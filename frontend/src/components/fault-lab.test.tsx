import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { FaultLab } from "./fault-lab";
import type { FaultRecord, Monitoring } from "@/lib/api";

afterEach(cleanup);

const snapshot: Monitoring = {
  observed_at: "2026-11-02T10:00:00Z", topology_name: "netrca_lab_v1", network_state: "RUNNING", collection_status: "COMPLETE", errors: [],
  devices: [
    { name: "h1", device_type: "HOST", interfaces: [{ name: "h1-eth0", status: "UP", rx_errors: 0, tx_errors: 0 }] },
    { name: "s1", device_type: "SWITCH", interfaces: [{ name: "s1-eth1", status: "UP", rx_errors: 0, tx_errors: 0 }] },
  ],
  links: [{ source: "h1", destination: "s1", status: "UP", interface_source: "h1-eth0", interface_destination: "s1-eth1" }],
};

const base = { records: [], types: ["INTERFACE_FAILURE", "LINK_FAILURE", "PACKET_LOSS", "HIGH_LATENCY"] as const, snapshot, networkRunning: true, presentationMode: false, onRefresh: vi.fn(), onInject: vi.fn(), onRecover: vi.fn(), onReset: vi.fn(), onOpenEvidence: vi.fn() };

test("builds packet-loss requests only from validated host interfaces", () => {
  const onInject = vi.fn();
  render(<FaultLab {...base} types={[...base.types]} onInject={onInject} />);
  fireEvent.change(screen.getByLabelText("Fault type"), { target: { value: "PACKET_LOSS" } });
  expect(screen.getByLabelText("Validated target")).toHaveTextContent("h1 · h1-eth0");
  expect(screen.getByLabelText("Validated target")).not.toHaveTextContent("s1 · s1-eth1");
  fireEvent.click(screen.getByRole("button", { name: "Inject controlled fault" }));
  expect(onInject).toHaveBeenCalledWith({ fault_type: "PACKET_LOSS", device: "h1", interface: "h1-eth0", packet_loss_percent: 50, duration_seconds: 30, severity: "HIGH" });
});

test("shows one active fault and exposes explicit recovery", () => {
  const active: FaultRecord = { id: "fault-1", fault_type: "LINK_FAILURE", status: "ACTIVE", target: { source: "h1", destination: "s1" }, parameters: { duration_seconds: 30 }, severity: "HIGH", started_at: "2026-11-02T10:00:00Z", expires_at: "2026-11-02T10:00:30Z", restoration_result: "PENDING", storage_status: "UNAVAILABLE" };
  const onRecover = vi.fn();
  render(<FaultLab {...base} types={[...base.types]} records={[active]} onRecover={onRecover} />);
  expect(screen.getByText("ACTIVE FAULT")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Inject controlled fault" })).toBeDisabled();
  fireEvent.click(screen.getByRole("button", { name: "Recover active fault" }));
  expect(onRecover).toHaveBeenCalledWith("fault-1");
  expect(screen.getByText("UNAVAILABLE")).toBeInTheDocument();
});

test("keeps fault mutation unavailable in presentation mode", () => {
  render(<FaultLab {...base} types={[...base.types]} presentationMode />);
  expect(screen.getByText(/unavailable in the browser-only synthetic presentation/i)).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Inject controlled fault" })).not.toBeInTheDocument();
});
