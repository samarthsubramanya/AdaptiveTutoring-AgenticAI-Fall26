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
              ["algebra", "inequalities", "statistics"].includes(x.topic) &&
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
