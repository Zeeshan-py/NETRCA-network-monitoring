import type { GraphSummary } from "./api";

export type PositionedDevice = GraphSummary["devices"][number] & { graphId: string; x: number; y: number; status: string };
export type PositionedLink = GraphSummary["links"][number] & { graphId: string; source: string; target: string; status: string };
export type TopologyLayout = {
  nodes: PositionedDevice[];
  edges: PositionedLink[];
  width: number;
  height: number;
  invalidEndpointCount: number;
  components: string[][];
};

/** Stable, source-agnostic rendering IDs; API entity IDs remain unchanged. */
export function mapTopologyGraph(graph: GraphSummary): TopologyLayout {
  const devices = graph.devices
    .filter((device) => typeof device.id === "string" && device.id.length > 0 && typeof device.name === "string")
    .slice().sort((a, b) => a.id.localeCompare(b.id));
  const knownIds = new Set(devices.map((device) => device.id));
  const links = graph.links.slice().sort((a, b) => a.id.localeCompare(b.id));
  const validLinks = links.filter((link) => knownIds.has(link.source_device_id) && knownIds.has(link.destination_device_id));
  const invalidEndpointCount = links.length - validLinks.length;

  const adjacency = new Map(devices.map((device) => [device.id, new Set<string>()]));
  for (const link of validLinks) {
    adjacency.get(link.source_device_id)?.add(link.destination_device_id);
    adjacency.get(link.destination_device_id)?.add(link.source_device_id);
  }
  const components: string[][] = [];
  const visited = new Set<string>();
  for (const device of devices) {
    if (visited.has(device.id)) continue;
    const stack = [device.id];
    const component: string[] = [];
    visited.add(device.id);
    while (stack.length) {
      const current = stack.pop()!;
      component.push(current);
      for (const neighbor of [...(adjacency.get(current) ?? [])].sort().reverse()) {
        if (!visited.has(neighbor)) { visited.add(neighbor); stack.push(neighbor); }
      }
    }
    components.push(component.sort((a, b) => a.localeCompare(b)));
  }
  components.sort((a, b) => a[0].localeCompare(b[0]));

  const positions = new Map<string, { x: number; y: number }>();
  let blockX = 60;
  let blockY = 70;
  let rowHeight = 0;
  let blockRow = 0;
  let maximumWidth = 0;
  for (const component of components) {
    const columns = Math.min(4, Math.max(1, Math.ceil(Math.sqrt(component.length))));
    const rows = Math.ceil(component.length / columns);
    const blockWidth = columns * 180 + 40;
    const currentHeight = rows * 120 + 40;
    if (blockRow >= 3) {
      maximumWidth = Math.max(maximumWidth, blockX);
      blockX = 60;
      blockY += rowHeight + 110;
      rowHeight = 0;
      blockRow = 0;
    }
    component.forEach((id, index) => positions.set(id, {
      x: blockX + (index % columns) * 180,
      y: blockY + Math.floor(index / columns) * 120,
    }));
    blockX += blockWidth;
    rowHeight = Math.max(rowHeight, currentHeight);
    blockRow += 1;
  }
  const nodes = devices.map((device) => ({
    ...device,
    graphId: `device:${device.id}`,
    x: positions.get(device.id)?.x ?? 60,
    y: positions.get(device.id)?.y ?? 70,
    status: typeof device.status === "string" && device.status ? device.status : "UNKNOWN",
  }));
  const edges = validLinks.map((link) => ({
    ...link,
    graphId: `link:${link.id}`,
    source: link.source_device_id,
    target: link.destination_device_id,
    status: typeof link.status === "string" && link.status ? link.status : "UNKNOWN",
  }));
  return {
    nodes,
    edges,
    width: Math.max(500, maximumWidth, blockX + 40),
    height: Math.max(300, blockY + rowHeight + 80),
    invalidEndpointCount,
    components,
  };
}
