"use client";

import { useEffect, useState } from "react";
import { getApiHealth } from "@/lib/api";

type State = "loading" | "up" | "unavailable";

export function ApiStatus() {
  const [state, setState] = useState<State>("loading");

  useEffect(() => {
    const controller = new AbortController();
    getApiHealth(controller.signal)
      .then(() => setState("up"))
      .catch(() => {
        if (!controller.signal.aborted) setState("unavailable");
      });
    return () => controller.abort();
  }, []);

  const label = {
    loading: "Checking API connection…",
    up: "API connected",
    unavailable: "API unavailable",
  }[state];

  return <span className={`api-status ${state}`} role="status">{label}</span>;
}
