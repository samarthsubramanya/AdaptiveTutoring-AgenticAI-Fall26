import { useEffect, useRef, useState } from "react";
import { api } from "../lib/api";
import Icon from "../components/Icon";
import Confidence from "../components/Confidence";
import Feedback from "../components/Feedback";
import type { Profile, Verification } from "../lib/types";

type Catalog = {
  skill: string;
  topics: { id: string; label: string; items: number }[];
}[];
type State = {
  session_id: string;
  learner_id: string;
  revision: number;
  item: {
    id: string;
    skill: string;
    topic: string;
    spec: Record<string, unknown>;
    prompt: string;
  };
  mode: string;
  reason: string;
  attempts: number;
  hint_level: number;
  max_hints: number;
  solved: boolean;
  can_next: boolean;
  next_label: string;
  verification: Verification | null;
  profile: Profile;
  history: {
    at: string;
    event: string;
    item_id: string;
    mode: string;
    status?: string;
    reason?: string;
    text?: string;
  }[];
  hint?: {
    status: string;
    message?: string;
    text?: string;
    kind?: string;
    level?: number;
  };
};
const names: Record<string, string> = {
  algebra: "Algebra",
  inequalities: "Inequalities",
  statistics: "Statistics",
  geometry: "Geometry",
  linear_systems: "Linear systems",
};
const modes: Record<string, string> = {
  practice: "Independent attempt",
  prerequisite_review: "Build the foundation",
  return: "Return to your original problem",
  unassisted_check: "Fresh unaided check",
  retrieve: "Welcome back · recall first",
};

export default function Journey({ learnerId }: { learnerId: string }) {
  const [catalog, setCatalog] = useState<Catalog>([]);
  const [skill, setSkill] = useState("algebra");
  const [topic, setTopic] = useState("algebra.two-step");
  const [state, setState] = useState<State | null>(null);
  const [answer, setAnswer] = useState("");
  const [reflection, setReflection] = useState("");
  const [confidence, setConfidence] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [hints, setHints] = useState<string[]>([]);
  const controller = useRef<AbortController | null>(null);
  const storageKey = `kernel.journey.${learnerId}`;
  useEffect(() => {
    const c = new AbortController();
    controller.current?.abort();
    setState(null);
    setHints([]);
    setAnswer("");
    setError("");
    setBusy(false);
    api<Catalog>("/journeys/catalog", undefined, c.signal)
      .then(setCatalog)
      .catch((e) => {
        if (!c.signal.aborted) setError(e.message);
      });
    let saved: string | null = null;
    try {
      saved = sessionStorage.getItem(storageKey);
    } catch {
      /* no storage */
    }
    if (saved)
      api<State>(`/journeys/sessions/${saved}`, undefined, c.signal)
        .then((data) => {
          if (!c.signal.aborted) {
            setState(data);
            setSkill(data.item.skill);
            setHints(
              data.history
                .filter(
                  (e) =>
                    e.item_id === data.item.id &&
                    e.event === "hint_requested" &&
                    e.status === "hint" &&
                    e.text,
                )
                .map((e) => e.text!),
            );
          }
        })
        .catch((e) => {
          if (!c.signal.aborted) {
            setError(e.message);
            try {
              sessionStorage.removeItem(storageKey);
            } catch {
              /* no storage */
            }
          }
        });
    return () => {
      c.abort();
      controller.current?.abort();
    };
  }, [learnerId, storageKey]);

  async function act(
    action: "start" | "answers" | "hints" | "next",
    event?: React.FormEvent,
  ) {
    event?.preventDefault();
    if (busy) return;
    const c = new AbortController();
    controller.current = c;
    setBusy(true);
    setError("");
    try {
      const previousItem = state?.item.id;
      const body =
        action === "start"
          ? { learner_id: learnerId, skill, topic }
          : {
              revision: state!.revision,
              ...(action === "answers"
                ? { answer, confidence_before: confidence ?? undefined }
                : {}),
              ...(action === "hints"
                ? { reflection: reflection.trim() || undefined }
                : {}),
            };
      const data = await api<State>(
        action === "start"
          ? "/journeys/sessions"
          : `/journeys/sessions/${state!.session_id}/${action}`,
        body,
        c.signal,
      );
      if (c.signal.aborted) return;
      setState(data);
      try {
        sessionStorage.setItem(storageKey, data.session_id);
      } catch {
        /* resume is optional */
      }
      if (data.item.id !== previousItem || action === "start") {
        setAnswer("");
        setHints([]);
        setReflection("");
        setConfidence(null);
      }
      if (data.hint?.status === "hint" && data.hint.text) {
        setHints((h) => [...h, data.hint!.text!]);
        setReflection("");
      }
    } catch (e) {
      if (!c.signal.aborted) {
        setError((e as Error).message);
        // An ambiguous network failure may have completed server-side: refresh,
        // never silently replay a grading action or reuse a stale revision.
        if (state) {
          try {
            const fresh = await api<State>(
              `/journeys/sessions/${state.session_id}`,
              undefined,
              c.signal,
            );
            if (!c.signal.aborted) setState(fresh);
          } catch {
            /* keep the actionable error and allow starting again */
          }
        }
      }
    } finally {
      if (!c.signal.aborted) setBusy(false);
    }
  }

  function close() {
    if (!state || busy) return;
    const c = new AbortController();
    controller.current = c;
    setBusy(true);
    setError("");
    api(`/journeys/sessions/${state.session_id}`, undefined, c.signal, "DELETE")
      .then(() => {
        if (c.signal.aborted) return;
        // Close the transient session; verified evidence stays in STUDENT.md.
        try {
          sessionStorage.removeItem(storageKey);
        } catch {
          /* no storage */
        }
        setState(null);
        setHints([]);
        setAnswer("");
      })
      .catch((e) => {
        if (!c.signal.aborted) {
          setError(e.message);
          try {
            sessionStorage.removeItem(storageKey);
          } catch {
            /* no storage */
          }
          setState(null);
        }
      })
      .finally(() => {
        if (!c.signal.aborted) setBusy(false);
      });
  }

  return (
    <>
      <div className="title-row">
        <div>
          <div className="eyebrow">A TUTOR THAT FOLLOWS YOUR PROGRESS</div>
          <h1>Your learning journey.</h1>
          <p>Try. Reflect. Revisit. Show what you can do on your own.</p>
        </div>
        <span className="verification-badge">
          <Icon name="ShieldCheck" size={17} /> Verified, step by step
        </span>
      </div>
      {!state ? (
        <section className="panel journey-start">
          <span className="eyebrow">PICK A STARTING POINT</span>
          <h2>One connected learning session.</h2>
          <p>
            Hints, prerequisite review, and fresh checks adapt to verified
            attempts. Returning learners pick up from their saved evidence.
          </p>
          <div className="form-two">
            <label>
              Subject
              <select
                value={skill}
                onChange={(e) => {
                  setSkill(e.target.value);
                  setTopic(
                    catalog.find((s) => s.skill === e.target.value)?.topics[0]
                      ?.id || "",
                  );
                }}
              >
                {catalog.map((s) => (
                  <option key={s.skill} value={s.skill}>
                    {names[s.skill]}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Starting topic
              <select value={topic} onChange={(e) => setTopic(e.target.value)}>
                {catalog
                  .find((s) => s.skill === skill)
                  ?.topics.map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.label}
                    </option>
                  ))}
              </select>
            </label>
          </div>
          <p className="fine-print">
            Saved learner: <strong>{learnerId}</strong>. The tutor may select a
            different starting point if your verified record calls for one. No
            API key is needed.
          </p>
          <button
            className="primary"
            disabled={busy || !catalog.length}
            onClick={() => act("start")}
          >
            Begin journey <Icon name="ArrowRight" size={17} />
          </button>
        </section>
      ) : (
        <>
          <div className="journey-steps">
            {[
              "Attempt",
              "Feedback & hints",
              "Review & return",
              "Fresh check",
            ].map((step, i) => (
              <span
                className={
                  (state.mode === "unassisted_check"
                    ? 3
                    : ["prerequisite_review", "return"].includes(state.mode)
                      ? 2
                      : state.attempts
                        ? 1
                        : 0) === i
                    ? "active"
                    : ""
                }
                key={step}
              >
                <b>{i + 1}</b>
                {step}
              </span>
            ))}
          </div>
          <div className="workspace-grid">
            <div className="practice-main">
              <section className={`plan-banner plan-${state.mode}`}>
                <div className="plan-head">
                  <span className="eyebrow">YOUR NEXT STEP</span>
                  <span className="support-chip">
                    {state.max_hints} hints available
                  </span>
                </div>
                <h3>{modes[state.mode]}</h3>
                <p>{state.reason}</p>
              </section>
              <section className="panel journey-problem">
                <div className="panel-label">
                  <span>
                    {names[state.item.skill]} · {state.item.id}
                  </span>
                  <span>{state.attempts} attempts</span>
                </div>
                <h2>{state.item.prompt}</h2>
                {state.item.skill === "statistics" && (
                  <p>
                    Use the stated population/sample convention. Fractions and
                    numeric square roots are accepted.
                  </p>
                )}
                {state.item.skill === "inequalities" && (
                  <p>
                    Use intervals, for example (-inf, 4], with U for unions.
                  </p>
                )}
                <form onSubmit={(event) => act("answers", event)}>
                  <label htmlFor="journey-answer">Your answer</label>
                  <div className="answer-input-row">
                    <input
                      id="journey-answer"
                      value={answer}
                      maxLength={300}
                      disabled={busy || state.solved}
                      onChange={(e) => setAnswer(e.target.value)}
                      autoComplete="off"
                      placeholder="Try it in your own way"
                    />
                    <button
                      className="primary"
                      disabled={busy || state.solved || !answer.trim()}
                    >
                      Check attempt{" "}
                      <Icon
                        name={busy ? "LoaderCircle" : "Check"}
                        size={16}
                        className={busy ? "spin" : ""}
                      />
                    </button>
                  </div>
                  <Confidence
                    label="How confident are you? (optional)"
                    value={confidence}
                    onChange={setConfidence}
                    disabled={busy || state.solved}
                  />
                </form>
                <Feedback result={state.verification} />
                <div className="journey-actions">
                  <button
                    className="text-button"
                    onClick={() => act("hints")}
                    disabled={busy || state.solved}
                  >
                    <Icon name="Lightbulb" size={16} />
                    Request a hint
                  </button>
                  {state.can_next && (
                    <button
                      className="primary"
                      onClick={() => act("next")}
                      disabled={busy}
                    >
                      {state.next_label}
                      <Icon name="ArrowRight" size={16} />
                    </button>
                  )}
                </div>
                {hints.map((hint, index) => (
                  <div className="hint-box" key={index}>
                    <span className="eyebrow">HINT {index + 1}</span>
                    <p>{hint}</p>
                  </div>
                ))}
                {state.hint?.message && (
                  <div className="hint-notice" role="status">
                    {state.hint.message}
                  </div>
                )}
                {state.hint?.status === "reflection_required" && (
                  <label className="journey-reflection">
                    What did you try, and where are you stuck?
                    <textarea
                      value={reflection}
                      onChange={(e) => setReflection(e.target.value)}
                      maxLength={500}
                      rows={3}
                    />
                    <button
                      className="secondary"
                      disabled={busy || reflection.trim().length < 15}
                      onClick={() => act("hints")}
                    >
                      Reflect and request the next hint
                    </button>
                  </label>
                )}
              </section>
              <details className="panel journey-trace">
                <summary>
                  How the tutor responded · {state.history.length} steps
                </summary>
                {state.history.map((event, i) => (
                  <div key={i}>
                    <span>{i + 1}</span>
                    <p>
                      <strong>{event.event.replaceAll("_", " ")}</strong> ·{" "}
                      {event.item_id}
                      <small>
                        {event.mode.replaceAll("_", " ")}
                        {event.status ? ` · ${event.status}` : ""}
                        {event.reason ? ` · ${event.reason}` : ""}
                      </small>
                    </p>
                  </div>
                ))}
              </details>
              <button className="text-button" onClick={close} disabled={busy}>
                Leave this journey and choose another subject
              </button>
            </div>
            <aside className="practice-aside">
              <section className="coach-card">
                <span className="eyebrow">YOUR VERIFIED EVIDENCE</span>
                <h3>
                  Small steps.
                  <br />A lasting record.
                </h3>
                {state.profile.topics.map((t) => (
                  <div className="journey-topic" key={t.topic}>
                    <strong>{t.label}</strong>
                    <p>
                      {t.independent_correct} unaided · {t.assisted_correct}{" "}
                      assisted successes
                    </p>
                    <small>Support: {t.support}</small>
                  </div>
                ))}
                {!state.profile.topics.length && (
                  <p>
                    Your first attempt will begin the record. Invalid input is
                    never counted as a miss.
                  </p>
                )}
              </section>
              <section className="reference-card">
                <Icon name="CircleHelp" />
                <h3>Evidence, not a mastery claim.</h3>
                <p>
                  A correct answer after help leads to a fresh unaided check.
                  Saved evidence informs future sessions, but is not proof of
                  learning gains.
                </p>
                <a
                  className="text-button"
                  href={`/api/learners/${learnerId}/student.md`}
                  target="_blank"
                  rel="noreferrer"
                >
                  Read your STUDENT.md <Icon name="ArrowUpRight" size={15} />
                </a>
              </section>
            </aside>
          </div>
        </>
      )}
      {error && (
        <div className="error-box" role="alert">
          <Icon name="TriangleAlert" size={18} />
          {error}
        </div>
      )}
    </>
  );
}
