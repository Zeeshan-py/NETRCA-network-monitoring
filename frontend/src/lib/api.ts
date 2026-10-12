export type ApiHealth = {
  success: true;
  data: { api: "UP" };
};

export async function getApiHealth(signal?: AbortSignal): Promise<ApiHealth> {
  const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (!baseUrl) {
    throw new Error("Backend URL is not configured");
  }

  const response = await fetch(`${baseUrl.replace(/\/$/, "")}/health`, {
    signal,
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error("Backend health check failed");
  }

  const payload: unknown = await response.json();
  if (
    typeof payload !== "object" ||
    payload === null ||
    !("success" in payload) ||
    payload.success !== true ||
    !("data" in payload) ||
    typeof payload.data !== "object" ||
    payload.data === null ||
    !("api" in payload.data) ||
    payload.data.api !== "UP"
  ) {
    throw new Error("Backend health response is invalid");
  }
  return payload as ApiHealth;
}
