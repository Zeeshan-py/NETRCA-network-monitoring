import { render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { ApiStatus } from "./api-status";

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

test("shows API connection after a valid health response", async () => {
  vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://localhost:8000/api/v1");
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => ({ success: true, data: { api: "UP" } }) }));
  render(<ApiStatus />);
  expect(screen.getByRole("status")).toHaveTextContent("Checking API connection");
  expect(await screen.findByText("API connected")).toBeInTheDocument();
});

test("shows unavailable when the health request fails", async () => {
  vi.stubEnv("NEXT_PUBLIC_API_BASE_URL", "http://localhost:8000/api/v1");
  vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("offline")));
  render(<ApiStatus />);
  expect(await screen.findByText("API unavailable")).toBeInTheDocument();
});
