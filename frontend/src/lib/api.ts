const BASE = import.meta.env.VITE_API_BASE || "/api";

export async function api<T>(
  path: string,
  body?: unknown,
  signal?: AbortSignal,
): Promise<T> {
  const controller = new AbortController();
  const abort = () => controller.abort();
  signal?.addEventListener("abort", abort, { once: true });
  if (signal?.aborted) controller.abort();
  const timer = window.setTimeout(abort, 20_000);
  try {
    const response = await fetch(`${BASE}${path}`, {
      method: body === undefined ? "GET" : "POST",
      headers:
        body === undefined ? undefined : { "Content-Type": "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: controller.signal,
    });
    const contentType = response.headers.get("content-type") || "";
    if (!contentType.includes("application/json"))
      throw new Error(
        "The API returned an unexpected response. Check that the Python API is running.",
      );
    const data = await response.json();
    if (!response.ok) {
      const detail =
        typeof data.detail === "string"
          ? data.detail
          : "Check the form fields and try again.";
      throw new Error(detail);
    }
    return data as T;
  } catch (error) {
    if (controller.signal.aborted && !signal?.aborted)
      throw new Error(
        "The request timed out. Check your connection and try again.",
      );
    if (error instanceof TypeError)
      throw new Error(
        "Cannot reach the API. Start the Python server, then try again.",
      );
    throw error;
  } finally {
    window.clearTimeout(timer);
    signal?.removeEventListener("abort", abort);
  }
}
