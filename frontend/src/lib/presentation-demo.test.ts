import { describe, expect, test } from "vitest";
import { PresentationDemoError, presentationDemoResponse } from "./presentation-demo";

describe("presentation fixture", () => {
  test("serves a disconnected stored topology with a failed uplink", () => {
    const response = presentationDemoResponse("/topology/analysis?source=stored") as { data: { connected: boolean; devices: Array<{ name: string }>; links: Array<{ status?: string }> } };
    expect(response.data.connected).toBe(false);
    expect(response.data.devices.map((device) => device.name)).toContain("DEMO-R1");
    expect(response.data.links.some((link) => link.status === "DOWN")).toBe(true);
  });

  test("keeps the live simulator unavailable instead of presenting fixture data as live", () => {
    expect(() => presentationDemoResponse("/topology/analysis?source=live")).toThrowError(PresentationDemoError);
    try {
      presentationDemoResponse("/topology/analysis?source=live");
    } catch (error) {
      expect(error).toMatchObject({ code: "SIMULATION_DISABLED", status: 409 });
    }
  });

  test("returns evidence-linked incident analysis without external model output", () => {
    const incidents = presentationDemoResponse("/incidents?page=1&limit=20") as { data: Array<{ id: string }>; pagination: { total: number } };
    expect(incidents.pagination.total).toBe(1);
    const id = incidents.data[0].id;
    const rca = presentationDemoResponse(`/incidents/${id}/root-causes`) as { data: { result: { candidates: Array<{ supporting_evidence: unknown[] }> } } };
    const explanation = presentationDemoResponse(`/ai/incidents/${id}/explain`, "POST") as { data: { provider: string; summary: Array<{ evidence_references: unknown[] }> } };
    expect(rca.data.result.candidates[0].supporting_evidence.length).toBeGreaterThan(0);
    expect(explanation.data.provider).toBe("STATIC_PRESENTATION_FIXTURE");
    expect(explanation.data.summary[0].evidence_references.length).toBeGreaterThan(0);
  });

  test("filters evidence by stable device identity", () => {
    const topology = presentationDemoResponse("/topology?source=stored") as { data: { nodes: Array<{ id: string; name?: string }> } };
    const router = topology.data.nodes.find((node) => node.name === "DEMO-R1");
    const page = presentationDemoResponse(`/metrics?page=1&limit=20&device_id=${router?.id}`) as { data: Array<{ device_id: string }> };
    expect(page.data.length).toBeGreaterThan(0);
    expect(page.data.every((record) => record.device_id === router?.id)).toBe(true);
  });
});
