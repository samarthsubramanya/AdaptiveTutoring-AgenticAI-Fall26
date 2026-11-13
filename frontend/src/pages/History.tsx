import Icon from "../components/Icon";
import type { Entry, Subject } from "../lib/types";
export default function History({
  history,
  clear,
  open,
}: {
  history: Entry[];
  clear: () => void;
  open: (s: Subject) => void;
}) {
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
        This journal stores up to 100 checks locally. It is not a persistent
        student profile or a measure of mastery.
      </p>
    </>
  );
}
