import { useEffect, useRef, useState } from "react";
import { api } from "../lib/api";
import { numericPreview } from "../lib/content.mjs";
import type {
  Entry,
  GeometryProblem,
  LearnerCheck,
  Learning,
  Plan,
  PlanAction,
  Session,
  Subject,
  Verification,
} from "../lib/types";
import Icon from "../components/Icon";
import Feedback from "../components/Feedback";
import PlanBanner from "../components/PlanBanner";
import HintLadder from "../components/HintLadder";
import Confidence from "../components/Confidence";
import GeometryFigure from "../components/GeometryFigure";
import { DataPlot, NumberLine } from "../components/Charts";

const titles = {
  algebra: "Algebra",
  inequalities: "Inequalities",
  statistics: "Statistics",
  geometry: "Geometry",
};
const symbols = {
  algebra: "ƒ",
  inequalities: "≥",
  statistics: "σ",
  geometry: "△",
};
const geometryTopics: Record<string, string> = {
  measurement: "Area & perimeter",
  pythagoras: "Pythagoras",
  angles: "Triangle angles",
  coordinate: "Coordinates",
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
  learnerId,
}: {
  subject: Subject;
  setSubject: (s: Subject) => void;
  record: (entry: Entry) => void;
  learnerId: string;
}) {
  const [expression, setExpression] = useState("2*x + 3");
  const [relation, setRelation] = useState("<=");
  const [rhs, setRhs] = useState("11");
  const [values, setValues] = useState("4, 7, 7, 9, 13");
  const [metric, setMetric] = useState("mean");
  const [convention, setConvention] = useState("population");
  const [bank, setBank] = useState<GeometryProblem[]>([]);
  const [geometryId, setGeometryId] = useState("geo-rect-area");
  const [answer, setAnswer] = useState("");
  const [result, setResult] = useState<Verification | null>(null);
  const [learning, setLearning] = useState<Learning>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [mode, setMode] = useState<PlanAction>("practice");
  const [applied, setApplied] = useState(false);
  const [confidence, setConfidence] = useState<number | null>(null);
  const [after, setAfter] = useState<number | null>(null);
  const [busy, setBusy] = useState(false);
  const [checks, setChecks] = useState(0);
  const [hint, setHint] = useState(false);
  const [error, setError] = useState("");
  const controller = useRef<AbortController | null>(null);
  const sessionLoading = useRef(false);
  const pending = useRef<Plan | null>(null);
  useEffect(() => () => controller.current?.abort(), []);

  useEffect(() => {
    const c = new AbortController();
    setPlan(null);
    api<Plan>(
      `/learners/${learnerId}/plan?skill=${subject}`,
      undefined,
      c.signal,
    )
      .then((next) => {
        if (c.signal.aborted) return;
        setPlan(next);
        if (pending.current?.skill === subject) {
          applyPlan(pending.current);
          pending.current = null;
        }
      })
      .catch(() => undefined);
    return () => c.abort();
    // applyPlan only reads setters and the plan it is given
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [subject, learnerId]);

  useEffect(() => {
    if (subject !== "geometry" || bank.length) return;
    const c = new AbortController();
    api<GeometryProblem[]>("/studio/geometry/problems", undefined, c.signal)
      .then((items) => !c.signal.aborted && setBank(items))
      .catch((e) => !c.signal.aborted && setError((e as Error).message));
    return () => c.abort();
  }, [subject, bank.length]);

  function resetFeedback(keepMode = false) {
    controller.current?.abort();
    setBusy(false);
    setResult(null);
    setLearning(null);
    setAnswer("");
    setHint(false);
    setError("");
    setConfidence(null);
    setAfter(null);
    if (!keepMode) {
      setMode("practice");
      setApplied(false);
    }
  }
  function changeSubject(next: Subject) {
    resetFeedback();
    setSubject(next);
  }
  const geometryProblem = bank.find((p) => p.id === geometryId) || bank[0];
  const statsValues = values.split(/[\s,;]+/).filter(Boolean);
  const spec: Record<string, unknown> | null =
    subject === "inequalities"
      ? { expression, relation, rhs }
      : subject === "statistics"
        ? { values: statsValues, metric, convention }
        : subject === "geometry" && geometryProblem
          ? { kind: geometryProblem.kind, params: geometryProblem.params }
          : null;
  const problem =
    subject === "inequalities"
      ? `${expression} ${relation} ${rhs}`
      : subject === "statistics"
        ? `${metric.replaceAll("_", " ")} of ${values} (${convention})`
        : subject === "geometry"
          ? geometryProblem?.prompt || "Geometry problem"
          : session?.problem?.equation || "Start a guided algebra session";

  /** Load the plan's suggested item; a prerequisite in another subject switches tabs first. */
  function applyPlan(next: Plan) {
    if (next.skill && next.skill !== subject && next.skill in titles) {
      pending.current = next;
      changeSubject(next.skill as Subject);
      return;
    }
    const items = next.suggested || [];
    resetFeedback(true);
    setMode(next.action === "start" ? "practice" : next.action);
    setApplied(true);
    if (subject === "geometry") {
      const id =
        items.find((i) => typeof i === "string" && i !== geometryId) ??
        items[0];
      if (typeof id === "string") setGeometryId(id);
    } else if (subject === "algebra") {
      const id = items.find((i) => typeof i === "string");
      if (typeof id === "string") beginAlgebra(id);
    } else {
      const current = JSON.stringify(spec);
      const example = (items.find((i) => JSON.stringify(i) !== current) ??
        items[0]) as Record<string, string & string[]> | undefined;
      if (!example) return;
      if (subject === "inequalities") {
        setExpression(example.expression);
        setRelation(example.relation);
        setRhs(example.rhs);
      } else {
        setValues(example.values.join(", "));
        setMetric(example.metric);
        setConvention(example.convention);
      }
    }
  }

  async function beginAlgebra(problemId?: string) {
    if (sessionLoading.current) return;
    sessionLoading.current = true;
    setBusy(true);
    setError("");
    const c = new AbortController();
    controller.current = c;
    try {
      const state = await api<Session>(
        "/tutoring/sessions",
        {
          learner_id: learnerId,
          ...(problemId ? { problem_id: problemId } : {}),
        },
        c.signal,
      );
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
    setLearning(null);
    setAfter(null);
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
        const response = await api<LearnerCheck>(
          `/learners/${learnerId}/check`,
          {
            skill: subject,
            spec,
            answer,
            mode,
            confidence_before: confidence ?? undefined,
          },
          c.signal,
        );
        if (c.signal.aborted) return;
        checked = response.verification;
        setChecks((n) => n + 1);
        setLearning(response.learning);
        setPlan(response.plan);
        setApplied(false);
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

  async function rateAfter(value: number) {
    if (!learning) return;
    setAfter(value);
    try {
      await api(`/learners/${learnerId}/confidence`, {
        event_id: learning.event_id,
        confidence_after: value,
      });
    } catch (e) {
      setError((e as Error).message);
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
  const correct = result?.status === "correct";
  const ladderKey = `${JSON.stringify(spec)}|${mode}`;
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
            {symbols[s]}
            <span>{titles[s]}</span>
            <Icon name="ArrowUpRight" size={15} />
          </button>
        ))}
      </div>
      <div className="workspace-grid">
        <div className="practice-main">
          <PlanBanner
            plan={plan}
            active={applied}
            onUse={() => plan && applyPlan(plan)}
          />
          <section className="panel problem-panel">
            <div className="panel-label">
              <span>
                <span className="tiny-dot" />{" "}
                {subject === "statistics"
                  ? "DATA EXPLORATION"
                  : subject === "geometry"
                    ? "SHAPE LAB"
                    : "GUIDED EXPLORATION"}
              </span>
              <span>
                {subject === "statistics"
                  ? "Center & spread"
                  : subject === "inequalities"
                    ? "Real numbers"
                    : subject === "geometry"
                      ? geometryTopics[geometryProblem?.topic || ""] ||
                        "Geometry"
                      : "Equation practice"}
              </span>
            </div>
            <h2>
              {subject === "statistics"
                ? "Every number has a part to play."
                : subject === "inequalities"
                  ? "Find where the statement is true."
                  : subject === "geometry"
                    ? "Measure it exactly."
                    : "Keep both sides in balance."}
            </h2>
            <p className="problem-description">
              {subject === "statistics"
                ? "Enter your data, choose a measure, and work it out."
                : subject === "inequalities"
                  ? "Find the complete solution set, including its boundaries."
                  : subject === "geometry"
                    ? "Choose a problem, sketch it, and give an exact answer."
                    : "Solve the original equation. A small hint is always nearby."}
            </p>
            {mode !== "practice" && (
              <span className={`mode-chip mode-${mode}`}>
                {mode === "unassisted_check"
                  ? "Unaided check · no hints"
                  : mode === "retrieve"
                    ? "Recall from memory · hints after your first try"
                    : "Prerequisite review"}
              </span>
            )}
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
            {subject === "geometry" && geometryProblem && (
              <>
                <div className="equation-display geometry-prompt">
                  {geometryProblem.prompt}
                </div>
                <label className="geometry-picker">
                  Problem
                  <select
                    value={geometryProblem.id}
                    onChange={(e) => {
                      setGeometryId(e.target.value);
                      resetFeedback();
                    }}
                  >
                    {Object.entries(geometryTopics).map(([topic, name]) => (
                      <optgroup label={name} key={topic}>
                        {bank
                          .filter((p) => p.topic === topic)
                          .map((p) => (
                            <option value={p.id} key={p.id}>
                              {p.prompt}
                            </option>
                          ))}
                      </optgroup>
                    ))}
                  </select>
                </label>
              </>
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
                    onClick={() => beginAlgebra()}
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
              ) : subject === "geometry" && geometryProblem ? (
                <>
                  <div className="visual-label">
                    THE SKETCH <span>Not to scale</span>
                  </div>
                  <GeometryFigure problem={geometryProblem} />
                  {correct && result.exact && (
                    <div className="solution-chip">{result.exact}</div>
                  )}
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
                        : subject === "geometry"
                          ? "Exact is best: 9*pi, 3*sqrt(2), 7/2, (4, 2) or undefined."
                          : "Enter your value for x."}
                  </p>
                </div>
              </div>
              {subject !== "algebra" && (
                <Confidence
                  label="Before you check: how sure are you? (optional)"
                  value={confidence}
                  onChange={setConfidence}
                  disabled={busy}
                />
              )}
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
                    maxLength={
                      subject === "algebra"
                        ? 80
                        : subject === "geometry"
                          ? 120
                          : 300
                    }
                    placeholder={
                      subject === "inequalities"
                        ? "e.g. (-inf, 4]"
                        : subject === "statistics"
                          ? "Your calculated value"
                          : subject === "geometry"
                            ? "e.g. 9*pi"
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
              {learning && (
                <div className="learning-note" role="status">
                  <Icon
                    name={learning.independent ? "CheckCheck" : "History"}
                    size={17}
                  />
                  <div>
                    {result?.status === "correct"
                      ? learning.independent
                        ? "Unaided success saved to your learner record."
                        : "Assisted success saved. An unaided check comes next."
                      : "Saved to your learner record. Misses guide what comes next."}
                    {learning.transition && (
                      <strong>{learning.transition}</strong>
                    )}
                  </div>
                </div>
              )}
              {learning?.ask_confidence_after && (
                <Confidence
                  label="Now that you've seen the result, how sure were you right to be?"
                  value={after}
                  onChange={rateAfter}
                  disabled={after !== null}
                />
              )}
              {error && (
                <div className="error-box" role="alert">
                  <Icon name="TriangleAlert" size={18} />
                  {error}
                </div>
              )}
              <div className="answer-footer">
                {subject === "algebra" ? (
                  <button
                    className="text-button"
                    disabled={busy || !session?.can_hint}
                    onClick={() => algebraAction("hint")}
                  >
                    <Icon name="Lightbulb" size={17} />
                    {hint ? "Hint is open" : "A little nudge?"}
                  </button>
                ) : (
                  <HintLadder
                    key={ladderKey}
                    learnerId={learnerId}
                    skill={subject}
                    spec={spec}
                    disabled={busy}
                    attempts={checks}
                  />
                )}
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
              {hint && subject === "algebra" && (
                <div className="hint-box">
                  <span className="eyebrow">A SMALL HINT</span>
                  <p>{session?.feedback}</p>
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
              Try first. Hints come one rung at a time, and before a bigger one
              you say what you tried. Help fades as you succeed on your own.
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
                  : subject === "geometry"
                    ? "Exact or rounded?"
                    : "Keep your working"}
            </h3>
            <p>
              {subject === "inequalities"
                ? "( ) leaves an endpoint out. [ ] includes it. Use U for separate intervals and open parentheses at infinity."
                : subject === "statistics"
                  ? "Population variance divides by n. Sample variance divides by n − 1 and needs at least two observations."
                  : subject === "geometry"
                    ? "Keep π and square roots exact: 9*pi, 3*sqrt(2). A decimal counts only if it is correctly rounded to the places you give."
                    : "A final answer helps us check correctness. Your working helps you understand the route you took."}
            </p>
            {subject === "inequalities" && <code>(-inf, -2] U [2, inf)</code>}
            {subject === "geometry" && <code>28.27 ✓ · 28.2 ✗ for 9π</code>}
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
