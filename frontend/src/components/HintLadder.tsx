import { useEffect, useState } from "react";
import Icon from "./Icon";
import { api } from "../lib/api";
import type { HintResult } from "../lib/types";

/** Graduated hints from the server: attempt first, then reflect before escalating. */
export default function HintLadder({
  learnerId,
  skill,
  spec,
  disabled,
  attempts,
}: {
  learnerId: string;
  skill: string;
  spec: Record<string, unknown> | null;
  disabled: boolean;
  attempts: number;
}) {
  const [hints, setHints] = useState<HintResult[]>([]);
  const [notice, setNotice] = useState<HintResult | null>(null);
  const [reflection, setReflection] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => setNotice(null), [attempts]); // a new check makes old gate messages stale
  async function ask() {
    if (!spec || busy) return;
    setBusy(true);
    setError("");
    try {
      const result = await api<HintResult>(`/learners/${learnerId}/hint`, {
        skill,
        spec,
        reflection: reflection.trim() || undefined,
      });
      if (result.status === "hint") {
        setHints((previous) => [...previous, result]);
        setNotice(null);
        setReflection("");
      } else setNotice(result);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  const last = hints[hints.length - 1];
  return (
    <div className="hint-ladder">
      <button
        className="text-button"
        onClick={ask}
        disabled={disabled || busy || !spec}
      >
        <Icon name="Lightbulb" size={17} />
        {hints.length ? "Next hint" : "A little nudge?"}
      </button>
      {hints.map((h) => (
        <div className="hint-box" key={h.level}>
          <span className="eyebrow">
            HINT {h.level} OF {h.max_level} · {h.kind?.toUpperCase()}
          </span>
          <p>{h.text}</p>
        </div>
      ))}
      {notice && (
        <div className={`hint-notice ${notice.status}`} role="status">
          <p>{notice.message}</p>
          {notice.status === "reflection_required" && (
            <>
              <label className="sr-only" htmlFor="hint-reflection">
                What you tried and where you are stuck
              </label>
              <textarea
                id="hint-reflection"
                rows={2}
                maxLength={500}
                value={reflection}
                placeholder="I tried … and I'm stuck on …"
                onChange={(e) => setReflection(e.target.value)}
              />
              <button
                className="secondary"
                onClick={ask}
                disabled={busy || reflection.trim().length < 15}
              >
                Ask for hint {(last?.level ?? 0) + 1}
              </button>
            </>
          )}
        </div>
      )}
      {error && (
        <p className="hint-error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
