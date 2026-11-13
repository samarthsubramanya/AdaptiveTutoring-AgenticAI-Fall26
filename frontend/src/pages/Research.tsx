import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import Icon from "../components/Icon";
import { answerText, researchError } from "../lib/content.mjs";
import type { useResearch } from "../hooks/useResearch";

type ResearchState = ReturnType<typeof useResearch>;
const prompts = [
  "Compare the latest AI accelerator developments from NVIDIA, AMD, Google, AWS, Intel, Microsoft, Meta, and Cerebras.",
  "Research three practical uses of probability in everyday decisions.",
];

export default function Research({ state }: { state: ResearchState }) {
  const [query, setQuery] = useState("");
  const [raw, setRaw] = useState(false);
  const { request, activity, error, submitting, paused } = state;
  const done = request?.status === "completed";
  const failed = request?.status === "failed";
  const running = !!state.id && !done && !failed;
  return (
    <>
      <div className="title-row">
        <div>
          <div className="eyebrow">A LITTLE FURTHER AFIELD</div>
          <h1>The research desk.</h1>
          <p>Follow a question. Bring the evidence back.</p>
        </div>
        <span className="verification-badge">
          <Icon name="Compass" size={16} /> Agent research
        </span>
      </div>
      {!request && !state.id && (
        <>
          <section className="research-hero">
            <div className="research-orbit" aria-hidden="true">
              <Icon name="Compass" size={92} />
            </div>
            <span className="eyebrow">WHERE DOES YOUR CURIOSITY LEAD?</span>
            <h2>
              Good questions
              <br />
              <em>open new doors.</em>
            </h2>
            <p>
              Specialist agents research, compare their findings,
              <br />
              and bring a response together for you.
            </p>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                if (query.trim()) void state.start(query.trim());
              }}
            >
              <label htmlFor="research-question" className="sr-only">
                Research question
              </label>
              <textarea
                id="research-question"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="What would you like to understand?"
                rows={3}
                maxLength={5000}
                disabled={submitting}
              />
              <div className="research-compose-footer">
                <span>
                  <Icon name="Search" size={15} /> Web research
                </span>
                <button
                  className="primary"
                  disabled={!query.trim() || submitting}
                >
                  {submitting ? "Starting…" : "Start exploring"}
                  <Icon name="ArrowUpRight" size={17} />
                </button>
              </div>
            </form>
          </section>
          <div className="section-heading">
            <h2>A spark to get you started</h2>
            <span className="quiet">Make it your own</span>
          </div>
          <div className="prompt-grid">
            {prompts.map((p, i) => (
              <button key={p} onClick={() => setQuery(p)}>
                <Icon name={i ? "BookOpen" : "Compass"} size={21} />
                <p>{p}</p>
                <Icon name="ArrowUpRight" size={18} />
              </button>
            ))}
          </div>
        </>
      )}
      {(request || state.id) && (
        <section className="research-results">
          <div className="research-query">
            <span className="eyebrow">YOUR QUESTION</span>
            <h2>
              {request?.query || "Reconnecting to your research request…"}
            </h2>
            <span className="request-id">{state.id}</span>
          </div>
          {running && (
            <div className="panel progress-panel">
              <span className="working-symbol">
                <Icon
                  name={paused ? "CircleHelp" : "LoaderCircle"}
                  className={paused ? "" : "spin"}
                  size={25}
                />
              </span>
              <div>
                <h3>
                  {paused
                    ? "Checking is paused."
                    : activity?.activity || "Planning the research."}
                </h3>
                <p>
                  {activity?.task_count
                    ? `${activity.completed_tasks} of ${activity.task_count} tasks completed`
                    : "The agents are getting started. This can take a few minutes."}
                </p>
              </div>
              <button
                className="text-button"
                onClick={paused ? state.resume : state.pause}
              >
                {paused ? "Resume checking" : "Pause checking"}
              </button>
            </div>
          )}
          {activity?.tasks?.length ? (
            <details className="panel research-tasks">
              <summary>
                Research activity{" "}
                <span>
                  {activity.completed_tasks}/{activity.task_count}
                </span>
              </summary>
              {activity.tasks.map((task) => (
                <div className="research-task" key={task.task_id}>
                  <Icon
                    name={
                      task.status === "completed"
                        ? "Check"
                        : task.status === "failed"
                          ? "TriangleAlert"
                          : "Compass"
                    }
                    size={17}
                  />
                  <div>
                    <p>{task.task}</p>
                    <span>{task.status}</span>
                  </div>
                </div>
              ))}
            </details>
          ) : null}
          {done && (
            <article className="panel response-panel">
              <div className="response-heading">
                <span className="eyebrow">
                  <Icon name="CheckCheck" size={16} /> RESEARCH COMPLETE
                </span>
                <button className="text-button" onClick={() => setRaw(!raw)}>
                  {raw ? "Read answer" : "View raw output"}
                </button>
              </div>
              {raw ? (
                <pre className="raw-output">{request?.result?.content}</pre>
              ) : (
                <div className="markdown">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {answerText(request?.result?.content)}
                  </ReactMarkdown>
                </div>
              )}
              <div className="fine-print response-note">
                <Icon name="CircleHelp" size={16} /> Retrieved evidence can be
                incomplete. Check original sources before relying on factual
                claims.
              </div>
            </article>
          )}
          {failed && (
            <div className="error-box" role="alert">
              <Icon name="TriangleAlert" />
              {researchError(request?.error)}
            </div>
          )}
          {(done || failed) && (
            <button className="primary new-research" onClick={state.reset}>
              <Icon name="Plus" size={17} /> Explore another question
            </button>
          )}
          {paused && (
            <p className="fine-print">
              Pausing checks does not cancel the server’s research.
            </p>
          )}
        </section>
      )}
      {error && (
        <div className="error-box" role="alert">
          <Icon name="TriangleAlert" size={18} />
          <span>{error}</span>
          {state.id && (
            <>
              <button className="text-button" onClick={state.resume}>
                Retry connection
              </button>
              <button className="text-button" onClick={state.reset}>
                Start a new request
              </button>
            </>
          )}
        </div>
      )}
      <div className="bottom-note">
        <Icon name="ShieldCheck" size={17} />
        <span>
          Model credentials stay on the server. Research runs through the
          existing Supervisor.
        </span>
      </div>
    </>
  );
}
