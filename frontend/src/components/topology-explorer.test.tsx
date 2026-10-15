import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import type { GraphSummary } from "@/lib/api";
import { TopologyExplorer } from "./topology-explorer";

afterEach(() => cleanup());

const graph: GraphSummary = {
  directed: false, semantics: "PHYSICAL_TOPOLOGY", connected: false,
  components: [["device-a", "device-b"], ["device-c"]],
  devices: [
    { id: "device-a", name: "router-a", device_type: "ROUTER", status: "DOWN" },
    { id: "device-b", name: "switch-b", device_type: "SWITCH", status: "DEGRADED" },
    { id: "device-c", name: "host-c", device_type: "HOST" },
  ],
  links: [{ id: "link-ab", source_device_id: "device-a", destination_device_id: "device-b", status: "UNKNOWN" }],
};

function renderExplorer(overrides: Partial<React.ComponentProps<typeof TopologyExplorer>> = {}) {
  return render(<TopologyExplorer source="stored" onSourceChange={vi.fn()} graph={graph} loading={false} onSelect={vi.fn()} onOpenEvidence={vi.fn()} onBrowseIncidents={vi.fn()} {...overrides} />);
}

test("renders statuses and components without treating absent device status as healthy", () => {
  renderExplorer();
  expect(screen.getByText("DISCONNECTED")).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /Device host-c, HOST, status UNKNOWN/ })).toBeInTheDocument();
  expect(screen.getByRole("button", { name: /Link link-ab, router-a to switch-b, status UNKNOWN/ })).toBeInTheDocument();
  expect(screen.getByText(/2 components/)).toBeInTheDocument();
  expect(screen.getByText(/Freshness timestamp is not supplied/)).toBeInTheDocument();
});

test("selects a node and link and exposes the supported stored evidence action", () => {
  const onSelect = vi.fn();
  const onOpenEvidence = vi.fn();
  const view = renderExplorer({ onSelect, onOpenEvidence });
  fireEvent.click(screen.getByTestId("topology-node-device-a"));
  expect(onSelect).toHaveBeenCalledWith({ kind: "device", id: "device-a" });
  view.rerender(<TopologyExplorer source="stored" onSourceChange={vi.fn()} graph={graph} loading={false} selection={{ kind: "device", id: "device-a" }} onSelect={onSelect} onOpenEvidence={onOpenEvidence} onBrowseIncidents={vi.fn()} />);
  expect(screen.getByRole("heading", { name: "router-a" })).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Open related stored evidence" }));
  expect(onOpenEvidence).toHaveBeenCalledWith({ kind: "device", id: "device-a" }, "router-a");
  fireEvent.click(screen.getByTestId("topology-link-link-ab"));
  expect(onSelect).toHaveBeenCalledWith({ kind: "link", id: "link-ab" });
});

test("reports loading, API errors, empty graphs and source switching", () => {
  const onSourceChange = vi.fn();
  const { rerender } = renderExplorer({ loading: true, graph: undefined });
  expect(screen.getByRole("status")).toHaveTextContent("Loading stored topology");
  rerender(<TopologyExplorer source="stored" onSourceChange={onSourceChange} graph={undefined} loading={false} error="Topology unavailable" onSelect={vi.fn()} onOpenEvidence={vi.fn()} onBrowseIncidents={vi.fn()} />);
  expect(screen.getByRole("alert")).toHaveTextContent("Topology unavailable");
  rerender(<TopologyExplorer source="stored" onSourceChange={onSourceChange} graph={{ ...graph, devices: [], links: [], components: [] }} loading={false} onSelect={vi.fn()} onOpenEvidence={vi.fn()} onBrowseIncidents={vi.fn()} />);
  expect(screen.getByText("No devices are available in the stored topology.")).toBeInTheDocument();
  fireEvent.click(screen.getByRole("button", { name: "Live Mininet" }));
  expect(onSourceChange).toHaveBeenCalledWith("live");
});

test("offers incident navigation without inventing a device-incident match", () => {
  const onBrowseIncidents = vi.fn();
  renderExplorer({ selection: { kind: "device", id: "device-a" }, onBrowseIncidents });
  fireEvent.click(screen.getByRole("button", { name: "Browse incident history" }));
  expect(onBrowseIncidents).toHaveBeenCalledOnce();
  expect(screen.getByRole("button", { name: "Browse incident history" })).toBeInTheDocument();
});

test("supports zoom and fit controls", () => {
  renderExplorer();
  const viewport = screen.getByRole("group", { name: /stored topology graph/ });
  fireEvent.click(screen.getByRole("button", { name: "Zoom in" }));
  expect(viewport.querySelector("g")?.getAttribute("transform")).toContain("scale(1.25)");
  fireEvent.click(screen.getByRole("button", { name: "Fit graph" }));
  expect(viewport.querySelector("g")?.getAttribute("transform")).toContain("scale(1)");
});

test("reports incomplete link endpoints as partial data", () => {
  renderExplorer({ graph: { ...graph, links: [{ id: "bad-link", source_device_id: "device-a", destination_device_id: "missing-device", status: "UP" }] } });
  expect(screen.getByRole("alert")).toHaveTextContent("Partial graph: 1 link(s) refer to devices absent");
  expect(screen.queryByTestId("topology-link-bad-link")).not.toBeInTheDocument();
});
