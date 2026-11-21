import { useEffect, useState } from "react";
import Icon from "../components/Icon";
import { api } from "../lib/api";
import type { Entry, Profile, Subject } from "../lib/types";

const supportLabel = {
  full: "Full support",
  light: "Light support",
  none: "Independent",
};
export default function History({
  history,
  clear,
  open,
  learnerId,
}: {
  history: Entry[];
  clear: () => void;
  open: (s: Subject) => void;
  learnerId: string;
}) {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [profileError, setProfileError] = useState("");
  useEffect(() => {
    const c = new AbortController();
    setProfile(null);
    setProfileError("");
    api<Profile>(`/learners/${learnerId}`, undefined, c.signal)
      .then((p) => !c.signal.aborted && setProfile(p))
      .catch((e) => !c.signal.aborted && setProfileError((e as Error).message));
    return () => c.abort();
  }, [learnerId]);
  async function downloadRecord() {
    const base = import.meta.env.VITE_API_BASE || "/api";
    const response = await fetch(`${base}/learners/${learnerId}/student.md`);
    if (!response.ok)
      return setProfileError("No verified evidence recorded yet.");
    const url = URL.createObjectURL(await response.blob());
    const a = document.createElement("a");
    a.href = url;
    a.download = `STUDENT-${learnerId}.md`;
    a.click();
    URL.revokeObjectURL(url);
  }
  function download() {
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(history, null, 2)], {
        type: "application/json",
      }),
    );
    const a = document.createElement("a");
    a.href = url;
    a.download = "kernel-practice.json";
    a.click();
    URL.revokeObjectURL(url);
  }
  return (
    <>
      <div className="title-row">
        <div>
          <span className="eyebrow">A RECORD OF YOUR EFFORT</span>
          <h1>Every attempt counts.</h1>
          <p>Your recent checks, saved on this browser.</p>
        </div>
        {history.length > 0 && (
          <button className="secondary" onClick={download}>
            <Icon name="Download" size={17} /> Export history
          </button>
        )}
      </div>
      <section className="panel learner-record" aria-labelledby="record-title">
        <div className="history-heading">
          <h2 id="record-title">
            Learner record <span>{learnerId}</span>
          </h2>
          {profile?.exists && (
            <button className="text-button" onClick={downloadRecord}>
              <Icon name="Download" size={15} /> STUDENT.md
            </button>
          )}
        </div>
        {profileError && <p className="fine-print">{profileError}</p>}
        {profile && !profile.exists && (
          <p className="record-empty">
            Nothing recorded yet. Verified checks in the math studio build this
            record; hints, misses and unaided successes all shape your next
            step.
          </p>
        )}
        {profile?.exists && (
          <>
            <table className="record-table">
              <thead>
                <tr>
                  <th scope="col">Topic</th>
                  <th scope="col">Unaided ✓</th>
                  <th scope="col">Assisted ✓</th>
                  <th scope="col">Attempts</th>
                  <th scope="col">Support</th>
                </tr>
              </thead>
              <tbody>
                {profile.topics.map((row) => (
                  <tr key={row.topic}>
                    <th scope="row">{row.label}</th>
                    <td>{row.independent_correct}</td>
                    <td>{row.assisted_correct}</td>
                    <td>{row.attempts}</td>
                    <td>
                      <span className={`support-chip support-${row.support}`}>
                        {supportLabel[row.support]}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="record-calibration">
              <Icon name="Compass" size={16} /> {profile.calibration.summary}
            </p>
          </>
        )}
      </section>
      {history.length ? (
        <section className="panel history-panel">
          <div className="history-heading">
            <h2>
              Practice journal <span>{history.length}</span>
            </h2>
            <button className="text-button" onClick={clear}>
              Clear browser history
            </button>
          </div>
          {history.map((entry) => (
            <div className="history-row" key={entry.id}>
              <span className={`history-status ${entry.status}`}>
                <Icon
                  name={entry.status === "correct" ? "Check" : "RotateCcw"}
                  size={18}
                />
              </span>
              <div>
                <span className="history-topic">{entry.topic}</span>
                <h3>{entry.problem}</h3>
                <p>Your answer: {entry.answer}</p>
              </div>
              <div className="history-date">
                <span>
                  {entry.status === "correct" ? "Verified" : "Try again"}
                </span>
                <time dateTime={entry.date}>
                  {new Date(entry.date).toLocaleString(undefined, {
                    month: "short",
                    day: "numeric",
                    hour: "numeric",
                    minute: "2-digit",
                  })}
                </time>
              </div>
            </div>
          ))}
        </section>
      ) : (
        <section className="panel empty-state">
          <span className="empty-icon">
            <Icon name="NotebookPen" size={38} />
          </span>
          <h2>Your journal starts with a try.</h2>
          <p>
            Check an answer in the math studio.
            <br />
            Your attempts will appear here as you go.
          </p>
          <button className="primary" onClick={() => open("inequalities")}>
            Find your first problem <Icon name="ArrowRight" size={17} />
          </button>
        </section>
      )}
      <p className="fine-print history-disclaimer">
        The journal below the learner record keeps up to 100 checks in this
        browser. The learner record is stored on the server as STUDENT.md and
        changes only from verified checks. Neither is a measure of mastery.
      </p>
    </>
  );
}
