import { useEffect, useRef, useState } from "react";
import { api } from "../lib/api";
import { numericPreview } from "../lib/content.mjs";
import type { Entry, Session, Subject, Verification } from "../lib/types";
import Icon from "../components/Icon";
import Feedback from "../components/Feedback";
import { DataPlot, NumberLine } from "../components/Charts";

const titles = {
  algebra: "Algebra",
  inequalities: "Inequalities",
  statistics: "Statistics",
};
const tidy = (s: string) =>
  s
    .replace(/\^2/g, "²")
    .replace(/\^3/g, "³")
    .replace(/\*/g, " · ")
    .replace(/<=/g, "≤")
    .replace(/>=/g, "≥");

export default function Practice({
  subject,
  setSubject,
  record,
}: {
  subject: Subject;
  setSubject: (s: Subject) => void;
  record: (entry: Entry) => void;
}) {
  const [expression, setExpression] = useState("2*x + 3");
  const [relation, setRelation] = useState("<=");
  const [rhs, setRhs] = useState("11");
  const [values, setValues] = useState("4, 7, 7, 9, 13");
  const [metric, setMetric] = useState("mean");
  const [convention, setConvention] = useState("population");
  const [answer, setAnswer] = useState("");
  const [result, setResult] = useState<Verification | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [busy, setBusy] = useState(false);
  const [hint, setHint] = useState(false);
  const [error, setError] = useState("");
  const controller = useRef<AbortController | null>(null);
  const sessionLoading = useRef(false);
  useEffect(() => () => controller.current?.abort(), []);
  function resetFeedback() {
    controller.current?.abort();
    setBusy(false);
    setResult(null);
    setAnswer("");
    setHint(false);
    setError("");
  }
  function changeSubject(next: Subject) {
    resetFeedback();
    setSubject(next);
  }
  const problem =
    subject === "inequalities"
      ? `${expression} ${relation} ${rhs}`
      : subject === "statistics"
        ? `${metric.replaceAll("_", " ")} of ${values} (${convention})`
        : session?.problem?.equation || "Start a guided algebra session";

  async function beginAlgebra() {
    if (sessionLoading.current) return;
    sessionLoading.current = true;
    setBusy(true);
    setError("");
    const c = new AbortController();
    controller.current = c;
    try {
      const state = await api<Session>("/tutoring/sessions", {}, c.signal);
      if (!c.signal.aborted) setSession(state);
    } catch (e) {
      if (!c.signal.aborted) setError((e as Error).message);
    } finally {
      if (!c.signal.aborted) setBusy(false);
      sessionLoading.current = false;
    }
  }

  async function check(event: React.FormEvent) {
    event.preventDefault();
    if (busy || !answer.trim()) return;
    const c = new AbortController();
    controller.current?.abort();
    controller.current = c;
    setBusy(true);
    setError("");
    setResult(null);
    try {
      let checked: Verification;
      if (subject === "algebra") {
        if (!session) throw new Error("Start an algebra session first.");
        const next = await api<Session>(
          `/tutoring/sessions/${session.session_id}/answers`,
          {
            revision: session.revision,
            problem_id: session.problem.id,
            answer,
          },
          c.signal,
        );
        if (c.signal.aborted) return;
        setSession(next);
        checked = next.verification!;
      } else {
        checked = await api<Verification>(
          `/studio/${subject}/check`,
          subject === "inequalities"
            ? { expression, relation, rhs, answer }
            : {
                values: values.split(/[\s,;]+/).filter(Boolean),
                metric,
                convention,
                answer,
              },
          c.signal,
        );
      }
      if (c.signal.aborted) return;
      setResult(checked);
      if (["correct", "incorrect"].includes(checked.status))
        record({
          id: crypto.randomUUID(),
          topic: subject,
          problem,
          answer,
          status: checked.status,
          date: new Date().toISOString(),
        });
    } catch (e) {
      if (!c.signal.aborted) setError((e as Error).message);
    } finally {
      if (!c.signal.aborted) setBusy(false);
    }
  }

  async function algebraAction(action: "hint" | "next") {
    if (!session || busy) return;
    const c = new AbortController();
    controller.current = c;
    setBusy(true);
    setError("");
    try {
      const next = await api<Session>(
        `/tutoring/sessions/${session.session_id}/${action}`,
        { revision: session.revision },
        c.signal,
      );
      if (!c.signal.aborted) {
        setSession(next);
        setHint(action === "hint");
        if (action === "next") {
          setAnswer("");
          setResult(null);
        }
      }
    } catch (e) {
      if (!c.signal.aborted) setError((e as Error).message);
    } finally {
      if (!c.signal.aborted) setBusy(false);
    }
  }
  const hints: Record<string, string> = {
    mean: "Add every observation, including repeated values. Divide the sum by the number of observations.",
    median:
      "Put the observations in order, then find the middle. For an even count, average the middle pair.",
    range: "Find the largest and smallest values, then subtract.",
    variance: `Find squared distances from the mean and add them. Divide by ${convention === "sample" ? "n − 1" : "n"}.`,
    standard_deviation:
      "Compute the variance using the chosen convention, then take its square root.",
  };
  const correct = result?.status === "correct";
  return (
    <>
      <div className="title-row">
        <div>
          <div className="eyebrow">ONE STEP AT A TIME</div>
          <h1>Your math studio.</h1>
          <p>A place to try, notice, and try again.</p>
        </div>
        <span className="verification-badge">
          <Icon name="ShieldCheck" size={16} /> Independently checked
        </span>
      </div>
      <div
        className="subject-tabs"
        role="tablist"
        aria-label="Practice subject"
      >
        {(Object.keys(titles) as Subject[]).map((s) => (
          <button
            role="tab"
            aria-selected={subject === s}
            key={s}
            onClick={() => changeSubject(s)}
          >
            {s === "algebra" ? "ƒ" : s === "inequalities" ? "≥" : "σ"}
            <span>{titles[s]}</span>
            <Icon name="ArrowUpRight" size={15} />
          </button>
        ))}
      </div>
      <div className="workspace-grid">
        <div className="practice-main">
          <section className="panel problem-panel">
            <div className="panel-label">
              <span>
                <span className="tiny-dot" />{" "}
                {subject === "statistics"
                  ? "DATA EXPLORATION"
                  : "GUIDED EXPLORATION"}
              </span>
              <span>
                {subject === "statistics"
                  ? "Center & spread"
                  : subject === "inequalities"
                    ? "Real numbers"
                    : "Equation practice"}
              </span>
            </div>
            <h2>
              {subject === "statistics"
                ? "Every number has a part to play."
                : subject === "inequalities"
                  ? "Find where the statement is true."
                  : "Keep both sides in balance."}
            </h2>
            <p className="problem-description">
              {subject === "statistics"
                ? "Enter your data, choose a measure, and work it out."
                : subject === "inequalities"
                  ? "Find the complete solution set, including its boundaries."
                  : "Solve the original equation. A small hint is always nearby."}
            </p>
            {subject === "inequalities" && (
              <>
                <div className="equation-display">
                  {tidy(expression)} <span>{tidy(relation)}</span> {tidy(rhs)}
                </div>
                <details className="edit-problem">
                  <summary>
                    <Icon name="SlidersHorizontal" size={15} /> Edit this
                    problem
                  </summary>
                  <div className="problem-inputs">
                    <label>
                      Left side
                      <input
                        value={expression}
                        maxLength={300}
                        onChange={(e) => {
                          setExpression(e.target.value);
                          resetFeedback();
                        }}
                      />
                    </label>
                    <label>
                      Relation
                      <select
                        value={relation}
                        onChange={(e) => {
                          setRelation(e.target.value);
                          resetFeedback();
                        }}
                      >
                        <option value="<=">≤</option>
                        <option value="<">&lt;</option>
                        <option value=">=">≥</option>
                        <option value=">">&gt;</option>
                      </select>
                    </label>
                    <label>
                      Right side
                      <input
                        value={rhs}
                        maxLength={300}
                        onChange={(e) => {
                          setRhs(e.target.value);
                          resetFeedback();
                        }}
                      />
                    </label>
                  </div>
                  <p className="fine-print">
                    Use explicit multiplication: 2*x. Supports linear and
                    quadratic polynomials in x.
                  </p>
                </details>
              </>
            )}
            {subject === "statistics" && (
              <div className="stats-controls">
                <label>
                  Observations
                  <input
                    value={values}
                    maxLength={3000}
                    onChange={(e) => {
                      setValues(e.target.value);
                      resetFeedback();
                    }}
                    placeholder="4, 7, 7, 9, 13"
                  />
                </label>
                <div className="form-two">
                  <label>
                    Measure
                    <select
                      value={metric}
                      onChange={(e) => {
                        setMetric(e.target.value);
                        resetFeedback();
                      }}
                    >
                      <option value="mean">Mean</option>
                      <option value="median">Median</option>
                      <option value="range">Range</option>
                      <option value="variance">Variance</option>
                      <option value="standard_deviation">
                        Standard deviation
                      </option>
                    </select>
                  </label>
                  <label>
                    Convention
                    <select
                      value={convention}
                      onChange={(e) => {
                        setConvention(e.target.value);
                        resetFeedback();
                      }}
                    >
                      <option value="population">Population · n</option>
                      <option value="sample">Sample · n − 1</option>
                    </select>
                  </label>
                </div>
              </div>
            )}
            {subject === "algebra" &&
              (session ? (
                <>
                  <div className="equation-display">
                    {tidy(session.problem.equation)}
                  </div>
                  <span className="problem-topic">{session.problem.topic}</span>
                </>
              ) : (
                <div className="algebra-start">
                  <Icon name="BookOpen" size={38} />
                  <p>Eight trusted equations. Start with a small win.</p>
                  <button
                    className="primary"
                    onClick={beginAlgebra}
                    disabled={busy}
                  >
                    {busy ? "Starting…" : "Begin guided practice"}{" "}
                    <Icon name="ArrowRight" size={16} />
                  </button>
                </div>
              ))}
            <div className="visual-area">
              {subject === "inequalities" ? (
                <>
                  <div className="visual-label">
                    THE NUMBER LINE{" "}
                    <span>
                      {correct
                        ? "Your verified solution"
                        : "A little room to reason"}
                    </span>
                  </div>
                  <NumberLine
                    segments={correct ? result.segments : undefined}
                  />
                  {correct && (
                    <div className="solution-chip">{result.solution}</div>
                  )}
                </>
              ) : subject === "statistics" ? (
                <>
                  <div className="visual-label">
                    YOUR OBSERVATIONS{" "}
                    <span>
                      {numericPreview(values).length} values · first 24 plotted
                    </span>
                  </div>
                  <DataPlot values={numericPreview(values)} />
                </>
              ) : (
                <div className="algebra-note">
                  <Icon name="ShieldCheck" size={18} />
                  <span>
                    Every answer is checked against the original equation.
                  </span>
                </div>
              )}
            </div>
          </section>
          {(subject !== "algebra" || session) && (
            <section className="panel answer-panel">
              <div className="answer-label">
                <span className="step-number">02</span>
                <div>
                  <h2>Your turn.</h2>
                  <p>
                    {subject === "inequalities"
                      ? "Write the full answer in interval notation."
                      : subject === "statistics"
                        ? "A number, fraction, or numeric square root is welcome."
                        : "Enter your value for x."}
                  </p>
                </div>
              </div>
              <form onSubmit={check}>
                <label htmlFor="student-answer" className="sr-only">
                  Your answer
                </label>
                <div className="answer-input-row">
                  <input
                    id="student-answer"
                    autoComplete="off"
                    value={answer}
                    onChange={(e) => {
                      setAnswer(e.target.value);
                      setResult(null);
                    }}
                    maxLength={subject === "algebra" ? 80 : 300}
                    placeholder={
                      subject === "inequalities"
                        ? "e.g. (-inf, 4]"
                        : subject === "statistics"
                          ? "Your calculated value"
                          : "x = …"
                    }
                    disabled={
                      busy || (subject === "algebra" && session?.solved)
                    }
                  />
                  <button
                    className="primary"
                    disabled={
                      busy ||
                      !answer.trim() ||
                      (subject === "algebra" && session?.solved)
                    }
                  >
                    {busy ? (
                      <Icon name="LoaderCircle" className="spin" size={17} />
                    ) : (
                      <Icon name="Check" size={17} />
                    )}{" "}
                    Check answer
                  </button>
                </div>
              </form>
              <Feedback result={result} />
              {error && (
                <div className="error-box" role="alert">
                  <Icon name="TriangleAlert" size={18} />
                  {error}
                </div>
              )}
              <div className="answer-footer">
                <button
                  className="text-button"
                  disabled={
                    busy || (subject === "algebra" && !session?.can_hint)
                  }
                  onClick={() =>
                    subject === "algebra"
                      ? algebraAction("hint")
                      : setHint(!hint)
                  }
                >
                  <Icon name="Lightbulb" size={17} />
                  {hint ? "Hint is open" : "A little nudge?"}
                </button>
                {subject === "algebra" && session?.solved && (
                  <button
                    className="text-button"
                    onClick={() => algebraAction("next")}
                    disabled={busy || session.finished}
                  >
                    Next equation <Icon name="ArrowRight" size={16} />
                  </button>
                )}
                <span className="quiet">No timer. Take your time.</span>
              </div>
              {hint && (
                <div className="hint-box">
                  <span className="eyebrow">A SMALL HINT</span>
                  <p>
                    {subject === "algebra"
                      ? session?.feedback
                      : subject === "statistics"
                        ? hints[metric]
                        : "Move constant terms to one side. If you divide by a negative number, reverse the comparison sign. For quadratics, test the sign between roots."}
                  </p>
                </div>
              )}
            </section>
          )}
          {error && subject === "algebra" && !session && (
            <div className="error-box" role="alert">
              {error}
            </div>
          )}
        </div>
        <aside className="practice-aside">
          <section className="coach-card">
            <span className="coach-spark">
              <Icon name="Sparkles" size={24} />
            </span>
            <span className="eyebrow">THINKING TOGETHER</span>
            <h3>
              Understanding
              <br />
              takes a few tries.
            </h3>
            <p>
              Start with what you know. Make an attempt. Use the feedback to
              find your next step.
            </p>
            <div className="coach-divider" />
            <span className="small-label">A GOOD WAY THROUGH</span>
            <ol>
              <li>
                <span>1</span>Read the whole problem
              </li>
              <li>
                <span>2</span>Try it in your own way
              </li>
              <li>
                <span>3</span>Check, reflect, and continue
              </li>
            </ol>
          </section>
          <section className="reference-card">
            <Icon name="CircleHelp" size={21} />
            <h3>
              {subject === "inequalities"
                ? "A note on notation"
                : subject === "statistics"
                  ? "Choose your convention"
                  : "Keep your working"}
            </h3>
            <p>
              {subject === "inequalities"
                ? "( ) leaves an endpoint out. [ ] includes it. Use U for separate intervals and open parentheses at infinity."
                : subject === "statistics"
                  ? "Population variance divides by n. Sample variance divides by n − 1 and needs at least two observations."
                  : "A final answer helps us check correctness. Your working helps you understand the route you took."}
            </p>
            {subject === "inequalities" && <code>(-inf, -2] U [2, inf)</code>}
            {subject === "statistics" && (
              <p className="fine-print">
                Numeric answers use a relative tolerance of 0.0001%, with a
                minimum absolute tolerance of 1e-8.
              </p>
            )}
          </section>
        </aside>
      </div>
    </>
  );
}
