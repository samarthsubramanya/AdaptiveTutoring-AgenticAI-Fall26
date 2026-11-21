export type Subject = "algebra" | "inequalities" | "statistics" | "geometry";
export type View = "overview" | "practice" | "research" | "history";
export type Entry = {
  id: string;
  topic: Subject;
  problem: string;
  answer: string;
  status: string;
  date: string;
};
export type Skill = {
  id: Subject;
  title: string;
  description: string;
  kind: string;
  topics: string[];
};
export type Verification = {
  status: string;
  message: string;
  solution?: string;
  segments?: Segment[];
  value?: number;
  values?: number[];
  metrics?: Record<string, number | null>;
  hint?: string;
  rounding_note?: string;
  exact?: string;
  prompt?: string;
};
export type Segment = {
  low: number | null;
  high: number | null;
  left_open: boolean;
  right_open: boolean;
};
export type Session = {
  session_id: string;
  revision: number;
  problem: { id: string; equation: string; topic: string };
  solved: boolean;
  finished: boolean;
  feedback: string;
  hint_level: number;
  attempts: number;
  completed_problem_ids: string[];
  verification: Verification | null;
  can_hint: boolean;
  can_advance: boolean;
};
export type RequestRecord = {
  request_id: string;
  query: string;
  status: string;
  result: { content?: string } | null;
  error: string | null;
};
export type Activity = {
  activity: string;
  completed_tasks: number;
  task_count: number;
  tasks: { task_id: string; task: string; status: string }[];
};
export type PlanAction =
  | "start"
  | "practice"
  | "retrieve"
  | "unassisted_check"
  | "prerequisite_review";
export type Plan = {
  action: PlanAction;
  topic: string | null;
  topic_label: string | null;
  skill: Subject | "linear_systems" | null;
  teaching_skill: string | null;
  reason: string;
  support: "full" | "light" | "none";
  max_hints: number;
  return_to?: string;
  suggested?: (string | Record<string, unknown>)[];
};
export type Learning = {
  event_id: string;
  independent: boolean;
  assisted: boolean;
  support: "full" | "light" | "none";
  max_hints: number;
  transition: string | null;
  ask_confidence_after: boolean;
} | null;
export type LearnerCheck = {
  verification: Verification;
  topic: string;
  learning: Learning;
  plan: Plan;
};
export type HintResult = {
  status: "hint" | "attempt_first" | "reflection_required" | "unavailable";
  message?: string;
  level?: number;
  max_level?: number;
  kind?: "conceptual" | "strategic" | "procedural";
  text?: string;
};
export type TopicRow = {
  topic: string;
  label: string;
  attempts: number;
  correct: number;
  independent_correct: number;
  assisted_correct: number;
  hints_used: number;
  support: "full" | "light" | "none";
  recent: string;
  last_verified: string | null;
  prerequisites: string[];
};
export type Profile = {
  learner_id: string;
  exists: boolean;
  updated: string | null;
  topics: TopicRow[];
  calibration: {
    samples: number;
    summary: string;
    accuracy?: number;
    confidence_before?: number;
  };
  file: string;
};
export type GeometryProblem = {
  id: string;
  kind: string;
  params: Record<string, string>;
  topic: string;
  prompt: string;
};
