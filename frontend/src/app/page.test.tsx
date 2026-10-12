import { render, screen } from "@testing-library/react";
import { expect, test, vi } from "vitest";
import Home from "./page";

vi.mock("@/components/api-status", () => ({ ApiStatus: () => <span>Checking API</span> }));

test("renders the Phase 1 application shell without live network claims", () => {
  render(<Home />);
  expect(screen.getByRole("heading", { level: 1 })).toHaveTextContent("Clarity when the network fails.");
  expect(screen.getByText("NETWORK DATA")).toBeInTheDocument();
  expect(screen.getByText("NOT CONNECTED")).toBeInTheDocument();
});
