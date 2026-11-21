"""Persistent learner memory and teaching policy.

Each learner has one STUDENT.md: YAML front matter is the source of truth and the
Markdown body below it is regenerated on every write. Only verified results
(correct/incorrect from a deterministic checker) change the record.

Teaching behaviour, adapted from the vault's teaching skills:
- retrieve-first-gate: returning learners recall before getting help; no hint
  is given before an attempt.
- progressive-hint-ladder: conceptual -> strategic -> procedural hints, with a
  short reflection required before levels 2 and 3.
- unassisted-evidence-checkpoint: an assisted success is followed by a fresh,
  hint-free check.
- fading-manager: per-topic support (full -> light -> none) fades after
  independent successes and is restored after misses; transitions are named.
- confidence-calibration-check: optional 1-5 ratings before and after
  feedback, compared with verified accuracy.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import json
import os
from pathlib import Path
import re
from threading import RLock
from typing import Any
import uuid

import yaml


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
LEARNER_ID = re.compile(r"[a-z0-9][a-z0-9_-]{2,39}")
SUPPORT_ORDER = ("full", "light", "none")
MAX_HINTS = {"full": 3, "light": 1, "none": 0}
HINT_KINDS = ("conceptual", "strategic", "procedural")
MIN_EVIDENCE = 2          # verified attempts in a skill before any profile claim
STALE_AFTER = timedelta(days=30)
RETRIEVE_AFTER = timedelta(minutes=30)   # a gap this long counts as a new session

TOPICS: dict[str, str] = {
    "algebra.one-step": "One-step equations",
    "algebra.two-step": "Two-step equations",
    "algebra.distribution": "Distribution",
    "inequalities.linear": "Linear inequalities",
    "inequalities.quadratic": "Quadratic inequalities",
    "statistics.center": "Center (mean, median, range)",
    "statistics.spread": "Spread (variance, standard deviation)",
    "geometry.measurement": "Area and perimeter",
    "geometry.pythagoras": "Pythagorean theorem",
    "geometry.angles": "Triangle angles",
    "geometry.coordinate": "Coordinate geometry",
    "linear_systems.elimination": "Linear systems",
}
ALGEBRA_TOPIC = {"one-step equations": "algebra.one-step", "two-step equations": "algebra.two-step",
                 "distribution": "algebra.distribution"}
PREREQUISITES: dict[str, tuple[str, ...]] = {
    "algebra.two-step": ("algebra.one-step",),
    "algebra.distribution": ("algebra.two-step",),
    "inequalities.linear": ("algebra.two-step",),
    "inequalities.quadratic": ("inequalities.linear",),
    "linear_systems.elimination": ("algebra.two-step",),
    "statistics.spread": ("statistics.center",),
    "geometry.pythagoras": ("geometry.measurement",),
    "geometry.coordinate": ("geometry.pythagoras",),
}


def _phrase(topic: str) -> str:
    """Topic label for use mid-sentence; proper nouns keep their capital."""
    label = TOPICS[topic]
    return label if label.split()[0] in {"Pythagorean"} else label[0].lower() + label[1:]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(moment: datetime) -> str:
    return moment.isoformat(timespec="seconds")


def item_key(skill: str, spec: dict[str, Any]) -> str:
    digest = hashlib.sha1(json.dumps(spec, sort_keys=True).encode()).hexdigest()[:12]
    return f"{skill}:{digest}"


def _empty_topic() -> dict[str, Any]:
    return {"attempts": 0, "correct": 0, "incorrect": 0, "independent_correct": 0,
            "assisted_correct": 0, "hints_used": 0, "support": "full",
            "independent_streak": 0, "miss_streak": 0, "pending_unassisted_check": False,
            "last_verified": None, "recent": []}


class LearnerStore:
    """File-backed store; one process-wide lock keeps read-modify-write atomic."""

    def __init__(self, root: Path | str | None = None) -> None:
        self.root = Path(root or os.getenv("KERNELAI_STUDENT_DIR")
                         or REPOSITORY_ROOT / "learning" / "data" / "students")
        self._lock = RLock()

    # ---------- storage ----------

    def path(self, learner_id: str) -> Path:
        if not isinstance(learner_id, str) or not LEARNER_ID.fullmatch(learner_id):
            raise ValueError("Learner ID: 3-40 characters of lowercase letters, digits, - or _.")
        return self.root / learner_id / "STUDENT.md"

    def load(self, learner_id: str) -> dict[str, Any]:
        path = self.path(learner_id)
        if not path.exists():
            return {"schema": 1, "learner_id": learner_id, "created": None, "updated": None,
                    "topics": {}, "open_items": {}, "calibration": [], "events": []}
        text = path.read_text(encoding="utf-8")
        if not text.startswith("---\n") or "\n---\n" not in text[4:]:
            raise ValueError(f"{path} has no front matter; restore it from version history.")
        data = yaml.safe_load(text[4:text.index("\n---\n", 4)])
        if not isinstance(data, dict) or data.get("learner_id") != learner_id:
            raise ValueError(f"{path} does not belong to learner {learner_id!r}.")
        return data

    def _save(self, data: dict[str, Any]) -> None:
        path = self.path(data["learner_id"])
        path.parent.mkdir(parents=True, exist_ok=True)
        moment = _iso(_now())
        data["created"] = data["created"] or moment
        data["updated"] = moment
        front = yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
        temporary = path.with_suffix(".tmp")
        temporary.write_text(f"---\n{front}---\n\n{render(data)}", encoding="utf-8")
        os.replace(temporary, path)

    # ---------- evidence ----------

    def record(self, learner_id: str, *, skill: str, topic: str, key: str, label: str,
               status: str, mode: str = "practice", confidence_before: int | None = None,
               hint_level: int | None = None) -> dict[str, Any] | None:
        """Record one verified result; anything but correct/incorrect is ignored."""
        if status not in {"correct", "incorrect"}:
            return None
        with self._lock:
            data = self.load(learner_id)
            moment = _iso(_now())
            item = data["open_items"].setdefault(key, {
                "skill": skill, "topic": topic, "label": label, "mode": mode,
                "attempts": 0, "hint_level": 0, "reflections": [], "opened": moment})
            stats = data["topics"].setdefault(topic, _empty_topic())
            if hint_level is not None and hint_level > item["hint_level"]:  # hints given elsewhere (algebra sessions)
                stats["hints_used"] += hint_level - item["hint_level"]
                item["hint_level"] = hint_level
            item["attempts"] += 1
            correct = status == "correct"
            assisted = item["hint_level"] > 0 or item["attempts"] > 1
            stats["attempts"] += 1
            stats["last_verified"] = moment
            transition = None
            if correct:
                stats["correct"] += 1
                stats["miss_streak"] = 0
                if assisted:
                    stats["assisted_correct"] += 1
                    stats["independent_streak"] = 0
                    stats["pending_unassisted_check"] = True
                else:
                    stats["independent_correct"] += 1
                    stats["independent_streak"] += 1
                    stats["pending_unassisted_check"] = False
                    level = SUPPORT_ORDER.index(stats["support"])
                    if stats["independent_streak"] >= 2 and level < 2:
                        stats["support"] = SUPPORT_ORDER[level + 1]
                        stats["independent_streak"] = 0
                        transition = {"light": "Two unaided successes: hints for this topic now stop after the first, conceptual one.",
                                      "none": "Two more unaided successes: hints are now off for this topic. Show what you can do on your own."}[stats["support"]]
                del data["open_items"][key]
            else:
                stats["incorrect"] += 1
                stats["independent_streak"] = 0
                stats["miss_streak"] += 1
                if stats["support"] == "none":
                    stats["support"] = "light"
                    transition = "A miss without hints: one conceptual hint is available again for this topic."
                elif stats["support"] == "light" and stats["miss_streak"] >= 2:
                    stats["support"] = "full"
                    transition = "Two misses in a row: full hints are back for this topic."
            stats["recent"] = (stats["recent"] + ["A" if correct and assisted else "I" if correct else "X"])[-10:]
            event_id = uuid.uuid4().hex[:12]
            if confidence_before is not None:
                data["calibration"] = (data["calibration"] + [{
                    "event_id": event_id, "topic": topic, "before": confidence_before,
                    "after": None, "correct": correct}])[-50:]
            data["events"] = (data["events"] + [{
                "id": event_id, "at": moment, "skill": skill, "topic": topic, "item": label,
                "status": status, "assisted": assisted, "hint_level": item["hint_level"],
                "attempt": item["attempts"], "mode": mode,
                **({"support_change": stats["support"]} if transition else {})}])[-60:]
            self._save(data)
            return {"event_id": event_id, "independent": correct and not assisted,
                    "assisted": assisted, "support": stats["support"],
                    "max_hints": MAX_HINTS[stats["support"]], "transition": transition,
                    "ask_confidence_after": confidence_before is not None}

    def hint(self, learner_id: str, *, key: str, topic: str, hints: tuple[str, ...],
             reflection: str | None = None) -> dict[str, Any]:
        """Next rung of the ladder, subject to the attempt gate, fading and reflection."""
        with self._lock:
            data = self.load(learner_id)
            item = data["open_items"].get(key)
            if not item or item["attempts"] == 0:
                return {"status": "attempt_first",
                        "message": "Try it once on your own first. Your attempt shows which part needs help."}
            support = data["topics"].get(topic, _empty_topic())["support"]
            cap = 0 if item["mode"] == "unassisted_check" else min(MAX_HINTS[support], len(hints))
            if item["hint_level"] >= cap:
                message = ("This is an unaided check, so no hints: the result shows what you can do on your own."
                           if item["mode"] == "unassisted_check" else
                           "Hints are faded for this topic because you have solved it unaided. Give it one more try."
                           if support == "none" else "No further hints for this problem. Compare your working with the last hint.")
                return {"status": "unavailable", "message": message, "level": item["hint_level"], "max_level": cap}
            level = item["hint_level"] + 1
            reflection = (reflection or "").strip()
            if level >= 2 and len(reflection) < 15:
                return {"status": "reflection_required", "level": item["hint_level"], "max_level": cap,
                        "message": "Before the next hint: what did you try, and where exactly are you stuck? A sentence is enough."}
            item["hint_level"] = level
            if reflection:
                item["reflections"] = (item["reflections"] + [reflection[:500]])[-5:]
            stats = data["topics"].setdefault(topic, _empty_topic())
            stats["hints_used"] += 1
            data["events"] = (data["events"] + [{
                "id": uuid.uuid4().hex[:12], "at": _iso(_now()), "skill": item["skill"], "topic": topic,
                "item": item["label"], "status": "hint", "hint_level": level, "mode": item["mode"]}])[-60:]
            self._save(data)
            return {"status": "hint", "level": level, "max_level": cap,
                    "kind": HINT_KINDS[min(level, 3) - 1], "text": hints[level - 1]}

    def confidence_after(self, learner_id: str, event_id: str, value: int) -> dict[str, Any]:
        with self._lock:
            data = self.load(learner_id)
            for sample in data["calibration"]:
                if sample["event_id"] == event_id:
                    sample["after"] = value
                    self._save(data)
                    return calibration(data)
            raise KeyError("No confidence rating was recorded for that check.")

    # ---------- policy ----------

    def plan(self, learner_id: str, skill: str) -> dict[str, Any]:
        """The first action for this skill, justified only by fresh verified evidence."""
        data = self.load(learner_id)
        now = _now()
        fresh = {t: s for t, s in data["topics"].items()
                 if s["last_verified"] and now - datetime.fromisoformat(s["last_verified"]) <= STALE_AFTER}
        mine = {t: s for t, s in fresh.items() if t.startswith(skill + ".")}
        default = next((t for t in TOPICS if t.startswith(skill + ".")), None)
        if sum(s["attempts"] for s in mine.values()) < MIN_EVIDENCE:
            return self._action("start", default, None, data,
                                "Not enough recent verified evidence for this skill yet, so the tutor makes no claim about you. Start with regular practice.")
        for topic, stats in mine.items():
            if stats["miss_streak"] >= 2:
                for prerequisite in PREREQUISITES.get(topic, ()):
                    earlier = fresh.get(prerequisite)
                    if not earlier or earlier["independent_correct"] == 0:
                        return self._action("prerequisite_review", prerequisite, None, data,
                                            f"Two recent misses on {_phrase(topic)}, and {_phrase(prerequisite)} has no unaided success yet. Review it first, then return.",
                                            return_to=topic)
        for topic, stats in mine.items():
            if stats["pending_unassisted_check"]:
                return self._action("unassisted_check", topic, "unassisted-evidence-checkpoint", data,
                                    f"Your last success on {_phrase(topic)} used help. Try a fresh one with no hints to see what you can do alone.")
        last = max(datetime.fromisoformat(s["last_verified"]) for s in mine.values())
        solved = [t for t, s in mine.items() if s["correct"]]
        if solved and now - last >= RETRIEVE_AFTER:
            oldest = min(solved, key=lambda t: mine[t]["last_verified"])
            return self._action("retrieve", oldest, "retrieve-first-gate", data,
                                f"Welcome back. Start by recalling {_phrase(oldest)} from memory: hints open only after your first attempt.")
        order = [t for t in TOPICS if t.startswith(skill + ".")]
        weakest = min(order, key=lambda t: (t in mine and mine[t]["support"] == "none",
                                            mine[t]["independent_correct"] if t in mine else -1,
                                            order.index(t)))
        support = mine.get(weakest, _empty_topic())["support"]
        return self._action("practice", weakest, "fading-manager", data,
                            f"Keep practising {_phrase(weakest)}. Support level: {support} "
                            f"({MAX_HINTS[support]} hint{'s' if MAX_HINTS[support] != 1 else ''} available).")

    def _action(self, action: str, topic: str | None, teaching_skill: str | None,
                data: dict[str, Any], reason: str, **extra: Any) -> dict[str, Any]:
        support = data["topics"].get(topic, _empty_topic())["support"] if topic else "full"
        return {"action": action, "topic": topic, "topic_label": TOPICS.get(topic or "", None),
                "skill": topic.split(".")[0] if topic else None, "teaching_skill": teaching_skill,
                "reason": reason, "support": support,
                "max_hints": 0 if action == "unassisted_check" else MAX_HINTS[support], **extra}

    def profile(self, learner_id: str) -> dict[str, Any]:
        data = self.load(learner_id)
        path = self.path(learner_id)
        return {"learner_id": learner_id, "exists": data["created"] is not None,
                "updated": data["updated"], "topics": topic_rows(data),
                "calibration": calibration(data), "recent_events": deepcopy(data["events"][-10:][::-1]),
                "file": str(path.relative_to(REPOSITORY_ROOT)) if path.is_relative_to(REPOSITORY_ROOT) else str(path)}


def topic_rows(data: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for topic in sorted(data["topics"], key=lambda t: list(TOPICS).index(t) if t in TOPICS else 99):
        s = data["topics"][topic]
        rows.append({"topic": topic, "label": TOPICS.get(topic, topic), "attempts": s["attempts"],
                     "correct": s["correct"], "independent_correct": s["independent_correct"],
                     "assisted_correct": s["assisted_correct"], "hints_used": s["hints_used"],
                     "support": s["support"], "recent": "".join(s["recent"]),
                     "last_verified": s["last_verified"],
                     "prerequisites": list(PREREQUISITES.get(topic, ()))})
    return rows


def calibration(data: dict[str, Any]) -> dict[str, Any]:
    samples = data["calibration"]
    if len(samples) < 3:
        return {"samples": len(samples), "summary": "Fewer than 3 confidence ratings: no calibration claim yet."}
    confidence = sum(s["before"] for s in samples) / len(samples) / 5
    accuracy = sum(s["correct"] for s in samples) / len(samples)
    gap = confidence - accuracy
    verdict = ("well calibrated" if abs(gap) < 0.15 else
               "more confident than your results so far" if gap > 0 else
               "less confident than your results so far")
    after = [s["after"] for s in samples if s["after"] is not None]
    return {"samples": len(samples), "confidence_before": round(confidence, 2),
            "accuracy": round(accuracy, 2), "gap": round(gap, 2),
            "confidence_after": round(sum(after) / len(after) / 5, 2) if after else None,
            "summary": f"Across {len(samples)} rated checks you were {verdict}."}


def render(data: dict[str, Any]) -> str:
    """Readable body of STUDENT.md, regenerated from the front matter on each write."""
    lines = [f"# Learner {data['learner_id']}", "",
             "> Generated from the verified evidence above; edits to this section are overwritten.",
             "> Only results graded by a deterministic checker are recorded. This is practice",
             "> evidence, not a mastery certification.", "", "## Topics", "",
             "| Topic | Attempts | Unaided ✓ | Assisted ✓ | Hints | Support | Recent |",
             "|---|---|---|---|---|---|---|"]
    for row in topic_rows(data):
        lines.append(f"| {row['label']} | {row['attempts']} | {row['independent_correct']} | "
                     f"{row['assisted_correct']} | {row['hints_used']} | {row['support']} | `{row['recent']}` |")
    lines += ["", "Recent: `I` unaided correct, `A` assisted correct, `X` incorrect.", "",
              "## Confidence calibration", "", calibration(data)["summary"], "",
              "## Latest evidence", ""]
    for event in data["events"][-10:][::-1]:
        lines.append(f"- {event['at']} · {TOPICS.get(event['topic'], event['topic'])} · "
                     f"{event['item']} · **{event['status']}**"
                     + (f" (hint {event['hint_level']})" if event.get("hint_level") else ""))
    return "\n".join(lines) + "\n"
