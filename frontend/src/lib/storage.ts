import type { Entry } from "./types";
const KEY = "kernel.practice.v1";
export function readHistory(): Entry[] {
  try {
    const data: unknown = JSON.parse(localStorage.getItem(KEY) || "[]");
    return Array.isArray(data)
      ? data
          .filter(
            (x): x is Entry =>
              x &&
              ["algebra", "inequalities", "statistics", "geometry"].includes(
                x.topic,
              ) &&
              typeof x.id === "string" &&
              typeof x.problem === "string" &&
              typeof x.answer === "string" &&
              typeof x.status === "string" &&
              typeof x.date === "string",
          )
          .slice(0, 100)
      : [];
  } catch {
    return [];
  }
}
export function saveHistory(entries: Entry[]) {
  try {
    localStorage.setItem(KEY, JSON.stringify(entries.slice(0, 100)));
    return true;
  } catch {
    return false;
  }
}
const LEARNER_KEY = "kernel.learner.v1";
export const LEARNER_ID = /^[a-z0-9][a-z0-9_-]{2,39}$/;
/** Per-browser convenience only: the learner record itself lives on the server. */
export function readLearner(): string {
  try {
    const saved = localStorage.getItem(LEARNER_KEY) || "";
    if (LEARNER_ID.test(saved)) return saved;
  } catch {
    /* storage unavailable: fall through to a fresh ID */
  }
  const fresh = `learner-${crypto.randomUUID().slice(0, 8)}`;
  saveLearner(fresh);
  return fresh;
}
export function saveLearner(id: string) {
  try {
    localStorage.setItem(LEARNER_KEY, id);
  } catch {
    /* keep it in memory for this page only */
  }
}
