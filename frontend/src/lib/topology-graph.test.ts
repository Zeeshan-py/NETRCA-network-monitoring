import { expect, test } from "vitest";
import type { GraphSummary } from "./api";
import { mapTopologyGraph } from "./topology-graph";

const graph: GraphSummary = {
  directed: false,
  semantics: "PHYSICAL_TOPOLOGY",
  connected: false,
  components: [["a", "b"], ["isolated"]],
  devices: [
    { id: "b", name: "switch-b", device_type: "SWITCH", status: "DOWN" },
    { id: "isolated", name: "host-c", device_type: "HOST" },
    { id: "a", name: "router-a", device_type: "ROUTER", status: "HEALTHY" },
  ],
  links: [
    { id: "link-ab", source_device_id: "a", destination_device_id: "b", status: "DEGRADED" },
    { id: "orphan", source_device_id: "a", destination_device_id: "missing", status: "UP" },
  ],
};

test("maps graph devices and valid links with stable IDs and deterministic positions", () => {
  const first = mapTopologyGraph(graph);
  const second = mapTopologyGraph({ ...graph, devices: graph.devices.slice().reverse(), links: graph.links.slice().reverse() });
  expect(first.nodes.map(({ graphId }) => graphId)).toEqual(["device:a", "device:b", "device:isolated"]);
  expect(first.edges.map(({ graphId, source, target }) => ({ graphId, source, target }))).toEqual([
    { graphId: "link:link-ab", source: "a", target: "b" },
  ]);
  expect(first.nodes.map(({ id, x, y }) => [id, x, y])).toEqual(second.nodes.map(({ id, x, y }) => [id, x, y]));
  expect(first.invalidEndpointCount).toBe(1);
});

test("keeps disconnected and isolated devices in separate components and missing status unknown", () => {
  const result = mapTopologyGraph(graph);
  expect(result.components).toEqual([["a", "b"], ["isolated"]]);
  expect(result.nodes.find((node) => node.id === "isolated")?.status).toBe("UNKNOWN");
  expect(result.nodes.find((node) => node.id === "b")?.status).toBe("DOWN");
  expect(result.edges[0].status).toBe("DEGRADED");
});

test("handles an empty graph without inventing nodes or links", () => {
  const result = mapTopologyGraph({ ...graph, devices: [], links: [], components: [], connected: false });
  expect(result.nodes).toEqual([]);
  expect(result.edges).toEqual([]);
  expect(result.components).toEqual([]);
});
