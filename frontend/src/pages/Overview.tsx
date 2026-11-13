import Icon from "../components/Icon";
import type { Entry, Skill, Subject } from "../lib/types";

export default function Overview({
  skills,
  history,
  open,
  research,
}: {
  skills: Skill[];
  history: Entry[];
  open: (subject: Subject) => void;
  research: () => void;
}) {
  const correct = history.filter((e) => e.status === "correct").length;
  return (
    <>
      <div className="page-intro">
        <div>
          <div className="eyebrow">YOUR LEARNING SPACE</div>
          <h1>
            Make room for
            <br />
            <em>understanding.</em>
          </h1>
          <p>
            A question, a small step, a moment of clarity.
            <br />
            Let’s find your next one.
          </p>
        </div>
        <div className="hero-art" aria-hidden="true">
          <div className="orbit orbit-one" />
          <div className="orbit orbit-two" />
          <span className="math-float mf-one">x²</span>
          <span className="math-float mf-two">Σ</span>
          <span className="math-float mf-three">&lt;</span>
          <div className="art-center">
            <Icon name="Sparkles" size={45} />
          </div>
          <span className="art-tag">
            <span className="tiny-dot" /> Made for curious minds
          </span>
        </div>
      </div>
      <div className="section-heading">
        <div>
          <span className="eyebrow">FIND YOUR FOCUS</span>
          <h2>What will you explore today?</h2>
        </div>
        <span className="quiet">Three ways to think a little deeper</span>
      </div>
      <div className="subject-grid">
        {skills.map((skill, i) => (
          <button
            className={`subject-card subject-${skill.id}`}
            key={skill.id}
            onClick={() => open(skill.id)}
          >
            <div className="subject-top">
              <span className="subject-symbol">{["ƒ", "≥", "σ"][i]}</span>
              <span className="card-index">0{i + 1}</span>
            </div>
            <span className="subject-kind">{skill.kind}</span>
            <h3>{skill.title}</h3>
            <p>{skill.description}</p>
            <div className="topic-pills">
              {skill.topics.map((t) => (
                <span key={t}>{t}</span>
              ))}
            </div>
            <div className="card-bottom">
              Start exploring <Icon name="ArrowUpRight" size={20} />
            </div>
          </button>
        ))}
      </div>
      <div className="lower-grid">
        <section className="panel practice-summary">
          <div className="panel-icon">
            <Icon name="NotebookPen" />
          </div>
          <div>
            <div className="eyebrow">SMALL STEPS ADD UP</div>
            <h2>Your practice, so far.</h2>
            <p>
              {history.length
                ? "A little evidence of the effort you’re putting in."
                : "Your first attempt is a good place to begin."}
            </p>
          </div>
          <div className="summary-values">
            <div>
              <strong>{history.length}</strong>
              <span>answers checked</span>
            </div>
            <div>
              <strong>{correct}</strong>
              <span>verified correct</span>
            </div>
          </div>
          <p className="fine-print">
            Saved in this browser. Practice counts are not mastery scores.
          </p>
        </section>
        <section className="research-invite">
          <span className="eyebrow">FOLLOW YOUR CURIOSITY</span>
          <h2>
            Some questions
            <br />
            lead beyond the textbook.
          </h2>
          <p>
            Give your research a starting point.
            <br />
            Let the agents follow the evidence.
          </p>
          <button className="text-button" onClick={research}>
            Open research desk <Icon name="ArrowRight" size={18} />
          </button>
          <Icon className="invite-compass" name="Compass" size={100} />
        </section>
      </div>
      <div className="bottom-note">
        <Icon name="ShieldCheck" size={17} />
        <span>
          Answers checked with mathematics. Space to learn at your own pace.
        </span>
      </div>
    </>
  );
}
