export type Subject = "algebra" | "inequalities" | "statistics";
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
  exact?: string;
  values?: number[];
  metrics?: Record<string, number | null>;
  hint?: string;
  rounding_note?: string;
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
