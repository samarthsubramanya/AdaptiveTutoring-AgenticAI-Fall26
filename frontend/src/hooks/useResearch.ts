import { useEffect, useState } from "react";
import { api } from "../lib/api";
import type { Activity, RequestRecord } from "../lib/types";

function savedRequest() {
  try {
    return sessionStorage.getItem("kernel.research.id") || "";
  } catch {
    return "";
  }
}

export function useResearch() {
  const [id, setId] = useState(savedRequest);
  const [request, setRequest] = useState<RequestRecord | null>(null);
  const [activity, setActivity] = useState<Activity | null>(null);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [paused, setPaused] = useState(false);
  const [generation, setGeneration] = useState(0);

  useEffect(() => {
    if (!id || paused) return;
    const controller = new AbortController();
    let timer: number | undefined;
    const started = Date.now();
    let failures = 0;
    async function poll() {
      try {
        const state = await api<RequestRecord>(
          `/requests/${id}`,
          undefined,
          controller.signal,
        );
        if (controller.signal.aborted) return;
        setRequest(state);
        failures = 0;
        setError("");
        if (["completed", "failed"].includes(state.status)) return;
        const progress = await api<Activity>(
          `/requests/${id}/activity`,
          undefined,
          controller.signal,
        );
        if (controller.signal.aborted) return;
        setActivity(progress);
      } catch (e) {
        if (controller.signal.aborted) return;
        failures += 1;
        setError((e as Error).message);
      }
      if (Date.now() - started > 15 * 60_000) {
        setPaused(true);
        setError(
          "Still working after 15 minutes. Resume checking when you’re ready.",
        );
        return;
      }
      if (!controller.signal.aborted)
        timer = window.setTimeout(
          poll,
          Math.min(15_000, 1800 * 2 ** Math.min(failures, 3)),
        );
    }
    void poll();
    return () => {
      controller.abort();
      window.clearTimeout(timer);
    };
  }, [id, paused, generation]);

  async function start(query: string) {
    if (
      submitting ||
      (id && request && !["completed", "failed"].includes(request.status))
    )
      return;
    setSubmitting(true);
    setError("");
    try {
      const state = await api<RequestRecord>("/requests", { query });
      setRequest(state);
      setActivity(null);
      setPaused(false);
      setId(state.request_id);
      try {
        sessionStorage.setItem("kernel.research.id", state.request_id);
      } catch {
        /* In-memory tracking remains available. */
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSubmitting(false);
    }
  }
  function reset() {
    setId("");
    setRequest(null);
    setActivity(null);
    setError("");
    setPaused(false);
    try {
      sessionStorage.removeItem("kernel.research.id");
    } catch {
      /* No persistent storage available. */
    }
  }
  return {
    id,
    request,
    activity,
    error,
    submitting,
    paused,
    start,
    reset,
    pause: () => setPaused(true),
    resume: () => {
      setPaused(false);
      setGeneration((g) => g + 1);
    },
  };
}
