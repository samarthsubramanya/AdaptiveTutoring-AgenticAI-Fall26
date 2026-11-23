"""Server-owned interactive tutoring: the browser never chooses a grading mode.

The default policy is the shipped adaptive tutor. Fixed and memoryless variants
are constructor-only ablations for evaluation; HTTP clients cannot select them.
"""

from copy import deepcopy
from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import RLock
import time
import uuid

from tutoring.algebra import PROBLEMS
from tutoring.learner_api import evaluate
from tutoring.learners import LearnerStore, ALGEBRA_TOPIC, MAX_HINTS, PREREQUISITES
import tutoring.learners as memory


def bank():
    items = []
    def add(identifier, skill, topic, spec):
        _, actual, label, hints = evaluate(skill, spec, "")
        assert actual == topic
        items.append({"id": identifier, "skill": skill, "topic": topic,
                      "spec": spec, "prompt": label, "hints": list(hints)})
    for pid, problem in PROBLEMS.items():
        add(pid, "algebra", ALGEBRA_TOPIC[problem.topic], {"problem_id": pid})
    for i in range(1, 7):
        add(f"ineq-linear-{i}", "inequalities", "inequalities.linear",
            {"expression": f"{i + 1}*x+{i}", "relation": "<=", "rhs": str(i + (i + 1) * 3)})
        add(f"ineq-quadratic-{i}", "inequalities", "inequalities.quadratic",
            {"expression": "x^2", "relation": ">=", "rhs": str(i * i)})
        add(f"stats-center-{i}", "statistics", "statistics.center",
            {"values": [str(i), str(i+2), str(i+4)], "metric": "mean", "convention": "population"})
        add(f"stats-spread-{i}", "statistics", "statistics.spread",
            {"values": [str(i), str(i+2), str(i+4)], "metric": "variance", "convention": "population"})
        add(f"geo-measure-{i}", "geometry", "geometry.measurement",
            {"kind": "rectangle_area", "params": {"width": str(i+2), "height": "4"}})
        add(f"geo-pythagoras-{i}", "geometry", "geometry.pythagoras",
            {"kind": "pythagoras_hypotenuse", "params": {"a": str(3*i), "b": str(4*i)}})
        add(f"geo-coordinate-{i}", "geometry", "geometry.coordinate",
            {"kind": "distance", "params": {"x1": "0", "y1": "0", "x2": str(3*i), "y2": str(4*i)}})
        add(f"geo-angles-{i}", "geometry", "geometry.angles",
            {"kind": "triangle_angle", "params": {"angle_a": str(30+i), "angle_b": "60"}})
        add(f"systems-{i}", "linear_systems", "linear_systems.elimination",
            {"equations": [{"a": "1", "b": "1", "c": str(i+2)},
                           {"a": "1", "b": "-1", "c": str(i-2)}]})
    return {item["id"]: item for item in items}


ITEMS = bank()
DEFAULT_TOPIC = {"algebra": "algebra.two-step", "statistics": "statistics.spread",
                 "inequalities": "inequalities.linear", "geometry": "geometry.measurement",
                 "linear_systems": "linear_systems.elimination"}


@dataclass
class Journey:
    id: str
    learner_id: str
    skill: str
    item: dict
    store: LearnerStore
    mode: str = "practice"
    reason: str = "Try the problem independently before asking for support."
    revision: int = 0
    attempts: int = 0
    hint_level: int = 0
    solved: bool = False
    assisted_context: bool = False
    stack: list = field(default_factory=list)
    history: list = field(default_factory=list)
    verification: dict | None = None
    touched: float = field(default_factory=time.monotonic)

    @property
    def key(self):
        return f"journey:{self.id}:{self.item['id']}"


class JourneyConflict(ValueError):
    pass


class JourneyStore:
    def __init__(self, learners: LearnerStore, *, adaptive=True, remember=True,
                 ttl_seconds=3600, max_sessions=256):
        self.learners = learners
        self.adaptive, self.remember = adaptive, remember
        self.ttl_seconds, self.max_sessions = ttl_seconds, max_sessions
        self.sessions: dict[str, Journey] = {}
        self.lock = RLock()

    def _context(self, store, learner):
        return store.load(learner).get("journey", {"seen": [], "return_topic": None, "review_complete": False})

    def _save_context(self, store, learner, context):
        with store._lock:
            data = store.load(learner)
            data["journey"] = context
            store._save(data)

    def _pick(self, store, learner, topic):
        context = self._context(store, learner)
        item = next((i for i in ITEMS.values() if i["topic"] == topic and i["id"] not in context["seen"]), None)
        if item is None:
            raise JourneyConflict("No fresh items remain in this topic. Choose another topic; repeating an answer is not new independent evidence.")
        context["seen"].append(item["id"])
        self._save_context(store, learner, context)
        return deepcopy(item)

    def start(self, learner_id, skill, topic=None):
        with self.lock:
            self.learners.path(learner_id)
            if skill not in DEFAULT_TOPIC or (topic is not None and not any(i["topic"] == topic and i["skill"] == skill for i in ITEMS.values())):
                raise ValueError("Choose a supported skill and a topic within that skill.")
            now = time.monotonic()
            self.sessions = {key: s for key, s in self.sessions.items() if now - s.touched < self.ttl_seconds}
            if len(self.sessions) >= self.max_sessions:
                raise JourneyConflict("The session limit was reached. Close a journey or try later.")
            sid = str(uuid.uuid4())
            store = self.learners if self.remember else LearnerStore(self.learners.root / "volatile" / sid)
            plan = store.plan(learner_id, skill)
            context = self._context(store, learner_id)
            mode, reason = "practice", "Start with an unaided attempt. The tutor will use verified feedback to choose what comes next."
            selected = topic or DEFAULT_TOPIC[skill]
            assisted = False
            if self.adaptive:
                if context["return_topic"] and context["return_topic"].startswith(skill + ".") and context["review_complete"]:
                    selected, mode, assisted = context["return_topic"], "return", True
                    reason = "Your prerequisite review is complete. Return to the original topic before a fresh unaided check."
                elif plan["action"] != "start":
                    selected, mode, reason = plan["topic"], plan["action"], plan["reason"]
            item = self._pick(store, learner_id, selected)
            session = Journey(sid, learner_id, skill, item, store, mode=mode, reason=reason, assisted_context=assisted)
            if mode == "prerequisite_review":
                context = self._context(store, learner_id)
                context["return_topic"], context["review_complete"] = plan.get("return_to"), False
                self._save_context(store, learner_id, context)
            self.sessions[sid] = session
            self._event(session, "session_started", reason=reason)
            return self._snapshot(session)

    def _get(self, sid, revision=None):
        session = self.sessions.get(sid)
        if session is None or time.monotonic() - session.touched >= self.ttl_seconds:
            self.sessions.pop(sid, None)
            raise KeyError("Journey expired or server restarted. Start another journey; verified learner evidence is retained.")
        if revision is not None and session.revision != revision:
            raise JourneyConflict("This journey changed. Reload its latest state before retrying.")
        if revision is not None and len(session.history) >= 200:
            raise JourneyConflict("Journey turn limit reached. Start another journey.")
        session.touched = time.monotonic()
        return session

    def get(self, sid):
        with self.lock:
            return self._snapshot(self._get(sid))

    def answer(self, sid, revision, answer, confidence=None):
        with self.lock:
            s = self._get(sid, revision)
            if s.solved:
                raise JourneyConflict("Already verified. Continue to a fresh problem before answering again.")
            verification, topic, label, _ = evaluate(s.item["skill"], s.item["spec"], answer)
            status = verification["status"]
            learning = s.store.record(s.learner_id, skill=s.item["skill"], topic=topic, key=s.key,
                                      label=label, status=status, mode=s.mode, confidence_before=confidence,
                                      hint_level=s.hint_level, assisted_context=s.assisted_context)
            s.verification = {k: verification[k] for k in ("status", "message", "verifier") if k in verification}
            if status in {"correct", "incorrect"}:
                s.attempts += 1
                s.solved = status == "correct"
            if s.solved:
                context = self._context(s.store, s.learner_id)
                if s.mode == "prerequisite_review":
                    context["review_complete"] = True
                elif context["return_topic"] == topic:
                    context["return_topic"], context["review_complete"] = None, False
                self._save_context(s.store, s.learner_id, context)
            s.revision += 1
            self._event(s, "answer_checked", answer=answer, status=status, learning=learning)
            return self._snapshot(s)

    def hint(self, sid, revision, reflection=None):
        with self.lock:
            s = self._get(sid, revision)
            if s.solved:
                raise JourneyConflict("The problem is solved. Continue to a fresh problem.")
            cap = self._cap(s)
            if s.attempts == 0:
                result = {"status": "attempt_first", "message": "Make an unaided attempt before asking for a hint."}
            elif s.hint_level >= cap:
                result = {"status": "unavailable", "message": "This is an unaided check or support is faded. No more hints are available."}
            elif s.hint_level and len((reflection or "").strip()) < 15:
                result = {"status": "reflection_required", "message": "Explain what you tried and where you are stuck before escalating the hint."}
            else:
                s.store.record_journey_hint(s.learner_id, s.key, s.hint_level + 1)
                s.hint_level += 1
                result = {"status": "hint", "level": s.hint_level,
                          "kind": ("conceptual", "strategic", "procedural")[s.hint_level - 1],
                          "text": s.item["hints"][s.hint_level - 1]}
            s.revision += 1
            self._event(s, "hint_requested", **result)
            return {**self._snapshot(s), "hint": result}

    def advance(self, sid, revision):
        with self.lock:
            s = self._get(sid, revision)
            if not s.solved and not (self.adaptive and s.attempts >= 2 and PREREQUISITES.get(s.item["topic"])):
                raise JourneyConflict("Verify an answer, or make two attempts on a topic with a prerequisite, before continuing.")
            topic, mode, reason = s.item["topic"], "practice", "Try another fresh problem."
            restoring = None
            if not s.solved:
                prerequisite = PREREQUISITES[topic][0]
                # Pick before mutating state: exhausted banks must leave the active item intact.
                item = self._pick(s.store, s.learner_id, prerequisite)
                s.stack.append({"item": s.item, "attempts": s.attempts, "hint_level": s.hint_level, "mode": s.mode})
                context = self._context(s.store, s.learner_id)
                context["return_topic"], context["review_complete"] = topic, False
                self._save_context(s.store, s.learner_id, context)
                mode, reason = "prerequisite_review", "Two attempts show this problem is still difficult. Practise a prerequisite, then return."
            elif self.adaptive and s.mode == "prerequisite_review":
                if s.stack:
                    restoring = s.stack[-1]
                    item = restoring["item"]
                    s.stack.pop()
                else:
                    target = self._context(s.store, s.learner_id)["return_topic"]
                    item = self._pick(s.store, s.learner_id, target or topic)
                mode, reason = "return", "Return to the original topic using your prerequisite review. This success will count as assisted."
                if restoring and restoring["mode"] == "prerequisite_review":
                    mode = "prerequisite_review"
                    reason = "Finish this prerequisite, then return to the original problem. Help from the simpler review remains assisted."
                if s.stack:
                    context = self._context(s.store, s.learner_id)
                    context["return_topic"], context["review_complete"] = s.stack[-1]["item"]["topic"], False
                    self._save_context(s.store, s.learner_id, context)
            else:
                stats = s.store.load(s.learner_id)["topics"].get(topic, {})
                if self.adaptive and stats.get("pending_unassisted_check"):
                    mode, reason = "unassisted_check", "Your previous success used help. Check a fresh problem without hints."
                item = self._pick(s.store, s.learner_id, topic)
            s.item, s.mode, s.reason = item, mode, reason
            s.attempts = restoring["attempts"] if restoring else 0
            s.hint_level = restoring["hint_level"] if restoring else 0
            s.solved, s.verification, s.assisted_context = False, None, restoring is not None or mode == "return"
            s.revision += 1
            self._event(s, "problem_transition", reason=reason)
            return self._snapshot(s)

    def _cap(self, s):
        if self.adaptive and s.mode == "unassisted_check":
            return 0
        stats = s.store.load(s.learner_id)["topics"].get(s.item["topic"], {})
        support = stats.get("support", "full") if self.adaptive else "full"
        if stats.get("last_verified") and memory._now() - datetime.fromisoformat(stats["last_verified"]) > memory.STALE_AFTER:
            support = "full"
        return min(MAX_HINTS[support], len(s.item["hints"]))

    def _event(self, s, event, **extra):
        s.history.append({"at": datetime.now(timezone.utc).isoformat(), "event": event,
                          "item_id": s.item["id"], "topic": s.item["topic"], "mode": s.mode, **extra})

    def _snapshot(self, s):
        remediate = self.adaptive and not s.solved and s.attempts >= 2 and bool(PREREQUISITES.get(s.item["topic"]))
        return deepcopy({"session_id": s.id, "learner_id": s.learner_id, "revision": s.revision,
                         "item": {k: v for k, v in s.item.items() if k != "hints"},
                         "mode": s.mode, "reason": s.reason, "attempts": s.attempts,
                         "hint_level": s.hint_level, "max_hints": self._cap(s), "solved": s.solved,
                         "can_next": s.solved or remediate,
                         "next_label": "Review prerequisite" if remediate else "Continue to next step",
                         "verification": s.verification, "history": s.history,
                         "profile": s.store.profile(s.learner_id)})
