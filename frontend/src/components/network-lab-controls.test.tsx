import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { NetworkLabControls } from "./network-lab-controls";
import type { NetworkStatus } from "@/lib/api";

afterEach(cleanup);

function status(state: NetworkStatus["state"], overrides: Partial<NetworkStatus> = {}): NetworkStatus {
  return {
    available: !["DISABLED", "UNAVAILABLE"].includes(state), state, topology_name: "netrca_lab_v1",
    started_at: null, device_count: state === "RUNNING" ? 5 : 0, link_count: state === "RUNNING" ? 4 : 0,
    operation: null, ...overrides,
  };
}

function renderControls(current: NetworkStatus, overrides: Partial<React.ComponentProps<typeof NetworkLabControls>> = {}) {
  const handlers = { onStart: vi.fn(), onReset: vi.fn(), onConnectivity: vi.fn(), onStop: vi.fn() };
  render(<NetworkLabControls status={current} presentationMode={false} {...handlers} {...overrides} />);
  return handlers;
}

test("allows only start while the lab is stopped", () => {
  const handlers = renderControls(status("STOPPED"));
  fireEvent.click(screen.getByRole("button", { name: "Start lab" }));
  expect(handlers.onStart).toHaveBeenCalledOnce();
  expect(screen.getByRole("button", { name: "Test connectivity" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "Reset topology" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "Stop lab" })).toBeDisabled();
});

test("enables runtime operations and reports measured connectivity", () => {
  const handlers = renderControls(status("RUNNING", { started_at: "2026-11-02T10:00:00Z" }), {
    connectivity: { connected: true, hosts: ["h1", "h2", "server1"], packet_loss_percent: 0 },
  });
  expect(screen.getByText("5")).toBeInTheDocument();
  expect(screen.getByText("4")).toBeInTheDocument();
  expect(screen.getByText("Connectivity passed")).toBeInTheDocument();
  expect(screen.getByText(/3 hosts · 0% packet loss/)).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Test connectivity" }));
  fireEvent.click(screen.getByRole("button", { name: "Reset topology" }));
  fireEvent.click(screen.getByRole("button", { name: "Stop lab" }));
  expect(handlers.onConnectivity).toHaveBeenCalledOnce();
  expect(handlers.onReset).toHaveBeenCalledOnce();
  expect(handlers.onStop).toHaveBeenCalledOnce();
});

test("keeps controls unavailable in browser-only presentation mode", () => {
  const handlers = renderControls(status("RUNNING"), { presentationMode: true });
  expect(screen.getByText(/cannot control Mininet/)).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Stop lab" })).not.toBeInTheDocument();
  expect(handlers.onStop).not.toHaveBeenCalled();
});

test("explains disabled simulation and blocks every operation", () => {
  renderControls(status("DISABLED", { detail: "SIMULATION_DISABLED" }));
  expect(screen.getByText(/Run the backend inside Ubuntu WSL2/)).toBeInTheDocument();
  expect(screen.getByRole("button", { name: "Start lab" })).toBeDisabled();
  expect(screen.getByRole("button", { name: "Stop lab" })).toBeDisabled();
});
