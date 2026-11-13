import { useEffect, useRef, useState } from "react";
import Icon from "./components/Icon";
import type { IconName } from "./components/Icon";
import { api } from "./lib/api";
import { readHistory, saveHistory } from "./lib/storage";
import type { Entry, Skill, Subject, View } from "./lib/types";
import { useResearch } from "./hooks/useResearch";
import Overview from "./pages/Overview";
import Practice from "./pages/Practice";
import Research from "./pages/Research";
import History from "./pages/History";

const nav: { view: View; label: string; icon: IconName }[] = [
  { view: "overview", label: "Overview", icon: "House" },
  { view: "practice", label: "Math studio", icon: "BookOpen" },
  { view: "research", label: "Research desk", icon: "Compass" },
  { view: "history", label: "Practice journal", icon: "History" },
];
const fallback: Skill[] = [
  {
    id: "algebra",
    title: "Algebra",
    description: "Build confidence, one equation at a time.",
    kind: "Guided practice",
    topics: ["Equations", "Hints", "Guided practice"],
  },
  {
    id: "inequalities",
    title: "Inequalities",
    description: "Discover the whole set of possibilities.",
    kind: "Visual practice",
    topics: ["Linear", "Quadratic", "Intervals"],
  },
  {
    id: "statistics",
    title: "Statistics",
    description: "Find the story inside your numbers.",
    kind: "Data lab",
    topics: ["Center", "Spread", "Population & sample"],
  },
];
function route(): { view: View; subject: Subject } {
  const [v, s] = location.hash.replace("#/", "").split("/");
  return {
    view: nav.some((n) => n.view === v) ? (v as View) : "overview",
    subject: ["algebra", "inequalities", "statistics"].includes(s)
      ? (s as Subject)
      : "inequalities",
  };
}

export default function App() {
  const [current, setCurrent] = useState(route);
  const [menu, setMenu] = useState(false);
  const [mobile, setMobile] = useState(
    () => matchMedia("(max-width: 700px)").matches,
  );
  const sidebar = useRef<HTMLElement>(null);
  const [history, setHistory] = useState<Entry[]>(readHistory);
  const [undo, setUndo] = useState<Entry[] | null>(null);
  const [skills, setSkills] = useState(fallback);
  const [connected, setConnected] = useState<boolean | null>(null);
  const [storageError, setStorageError] = useState(false);
  const [healthVersion, setHealthVersion] = useState(0);
  const research = useResearch();
  useEffect(() => {
    const query = matchMedia("(max-width: 700px)");
    const update = () => {
      setMobile(query.matches);
      setMenu(false);
    };
    query.addEventListener("change", update);
    return () => query.removeEventListener("change", update);
  }, []);
  useEffect(() => {
    if (!mobile || !menu) return;
    const previous = document.activeElement as HTMLElement | null;
    const links = sidebar.current?.querySelectorAll<HTMLAnchorElement>("a");
    links?.[0]?.focus();
    function keys(event: KeyboardEvent) {
      if (event.key === "Escape") setMenu(false);
      if (event.key === "Tab" && links?.length) {
        const first = links[0],
          last = links[links.length - 1];
        if (event.shiftKey && document.activeElement === first) {
          event.preventDefault();
          last.focus();
        } else if (!event.shiftKey && document.activeElement === last) {
          event.preventDefault();
          first.focus();
        }
      }
    }
    document.addEventListener("keydown", keys);
    return () => {
      document.removeEventListener("keydown", keys);
      previous?.focus({ preventScroll: true });
    };
  }, [menu, mobile]);
  useEffect(() => {
    document.getElementById("main-content")?.focus({ preventScroll: true });
    window.scrollTo(0, 0);
  }, [current.view, current.subject]);
  useEffect(() => {
    setStorageError(!saveHistory(history));
  }, [history]);
  useEffect(() => {
    const onHash = () => {
      setCurrent(route());
      setMenu(false);
    };
    window.addEventListener("hashchange", onHash);
    return () => window.removeEventListener("hashchange", onHash);
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    setConnected(null);
    api<Skill[]>("/studio/skills", undefined, controller.signal)
      .then((data) => {
        if (!controller.signal.aborted) {
          setSkills(data);
          setConnected(true);
        }
      })
      .catch(() => {
        if (!controller.signal.aborted) setConnected(false);
      });
    return () => controller.abort();
  }, [healthVersion]);
  function go(view: View, subject = current.subject) {
    location.hash = `/${view}/${subject}`;
    setMenu(false);
  }
  function record(entry: Entry) {
    setHistory((previous) => [entry, ...previous].slice(0, 100));
  }
  function clear() {
    setUndo(history);
    setHistory([]);
  }
  function restore() {
    if (undo) {
      setHistory(undo);
      setUndo(null);
    }
  }
  return (
    <div className="app-shell">
      <a
        className="skip-link"
        href="#main-content"
        onClick={(event) => {
          event.preventDefault();
          document.getElementById("main-content")?.focus();
        }}
      >
        Skip to content
      </a>
      {menu && (
        <button
          className="sidebar-backdrop"
          aria-label="Close navigation"
          onClick={() => setMenu(false)}
        />
      )}
      <aside
        ref={sidebar}
        className={`sidebar ${menu ? "mobile-open" : ""}`}
        inert={mobile && !menu}
        role={mobile && menu ? "dialog" : undefined}
        aria-modal={mobile && menu ? true : undefined}
        aria-label="Main navigation"
      >
        <a className="brand" href="#/overview">
          <span className="brand-mark">
            <i />
            <i />
            <i />
            <i />
          </span>
          <span>
            kernel<span className="brand-dot">.</span>
            <small>LEARNING STUDIO</small>
          </span>
        </a>
        <div className="sidebar-section-label">YOUR WORKSPACE</div>
        <nav>
          {nav.map((item) => (
            <a
              key={item.view}
              href={`#/${item.view}/${current.subject}`}
              className={current.view === item.view ? "active" : ""}
              aria-current={current.view === item.view ? "page" : undefined}
            >
              <Icon name={item.icon} size={20} />
              <span>{item.label}</span>
              {item.view === "practice" && <span className="nav-count">3</span>}
              {item.view === "research" &&
                research.id &&
                !["completed", "failed"].includes(
                  research.request?.status || "",
                ) && <span className="nav-live" />}
            </a>
          ))}
        </nav>
        <div className="sidebar-note">
          <span className="sidebar-note-star">✳</span>
          <h3>
            A little better,
            <br />
            one question at a time.
          </h3>
          <p>
            Progress begins with curiosity.
            <br />
            Bring yours.
          </p>
          <div className="sidebar-line-art" aria-hidden="true">
            <span />
            <span />
            <span />
            <span />
            <span />
          </div>
        </div>
        <div className="sidebar-bottom">
          <a
            href={import.meta.env.VITE_STREAMLIT_URL || "http://127.0.0.1:8501"}
            target="_blank"
            rel="noreferrer"
          >
            <Icon name="ExternalLink" size={17} />
            <span>Open Streamlit</span>
            <Icon name="ArrowUpRight" size={15} />
          </a>
          <div className="workspace-avatar">
            <span>K</span>
            <div>
              Your workspace<small>Space to grow</small>
            </div>
            <Icon name="Sparkles" size={18} />
          </div>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div className="breadcrumb">
            <button
              className="mobile-menu"
              aria-label="Open navigation"
              onClick={() => setMenu(!menu)}
            >
              <Icon name="Menu" />
            </button>
            <span>Workspace</span>
            <Icon name="ChevronRight" size={14} />
            <strong>{nav.find((n) => n.view === current.view)?.label}</strong>
          </div>
          <div className="topbar-right">
            <span
              className={`connection ${connected ? "online" : connected === false ? "offline" : ""}`}
            >
              <span />
              {connected
                ? "Ready to explore"
                : connected === false
                  ? "API offline"
                  : "Connecting…"}
            </span>
            <span className="topbar-divider" />
            <Icon name="Sparkles" size={18} />
            <span className="topbar-caption">A little more clarity</span>
          </div>
        </header>
        <main id="main-content" className="main-content" tabIndex={-1}>
          {connected === false && (
            <div className="connection-banner" role="alert">
              <Icon name="Wifi" size={18} />
              <span>
                The API is unavailable. Start the Python server to check
                answers.
              </span>
              <button onClick={() => setHealthVersion((v) => v + 1)}>
                Reconnect
              </button>
            </div>
          )}
          {storageError && (
            <div className="connection-banner" role="status">
              Browser storage is unavailable. Your checks remain here until the
              page reloads.
            </div>
          )}
          {current.view === "overview" && (
            <Overview
              skills={skills}
              history={history}
              open={(s) => go("practice", s)}
              research={() => go("research")}
            />
          )}
          {current.view === "practice" && (
            <Practice
              subject={current.subject}
              setSubject={(s) => go("practice", s)}
              record={record}
            />
          )}
          {current.view === "research" && <Research state={research} />}
          {current.view === "history" && (
            <History
              history={history}
              clear={clear}
              open={(s) => go("practice", s)}
            />
          )}
          {undo && (
            <div className="undo-toast" role="status">
              Practice journal cleared.<button onClick={restore}>Undo</button>
              <button aria-label="Dismiss undo" onClick={() => setUndo(null)}>
                <Icon name="X" size={15} />
              </button>
            </div>
          )}
        </main>
        <footer className="app-footer">
          <span>KERNEL LEARNING STUDIO</span>
          <span>
            Keep asking. Keep growing.<span className="footer-spark">✳</span>
          </span>
        </footer>
      </div>
    </div>
  );
}
