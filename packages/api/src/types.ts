/** Clarity — Decision type: every AI output must carry an explanation. */
export interface Decision<T = unknown> {
  value: T;
  explain: string;
  confidence: number;
  audit: AuditEntry;
}

export interface AuditEntry {
  ts: number;
  agent: string;
  action: string;
  explain: string;
  inputHash: string;
}

/** Fibra — Task slot in the golden-angle scheduler. */
export interface FibraTask {
  id: number;
  angle: number;
  slot: number;
  timeoutLevel: number;
  createdAt: number;
}

/** Soul — A single thought in the execution trace. */
export interface Thought {
  ts: number;
  fn: string;
  event: "enter" | "exit" | "error" | "check" | "correction";
  msg: string;
  confidence: number;
  data?: Record<string, unknown>;
}

/** Skill version history entry. */
export interface SkillVersion {
  v: number;
  source: string;
  reason: string;
  author: "human" | "self" | "peer";
  ts: number;
  metrics: Record<string, number>;
  parent: number | null;
}

/** Network message on the shared memory bus. */
export interface Msg {
  sender: string;
  topic: string;
  data: unknown;
  ts: number;
}

/** Agent status. */
export interface AgentStatus {
  name: string;
  skills: Record<string, SkillStatus>;
  soul: SoulSummary;
}

export interface SkillStatus {
  name: string;
  version: number;
  totalVersions: number;
  calls: number;
  errorRate: number;
  tests: number;
}

export interface SoulSummary {
  thoughts: number;
  errors: number;
  corrections: number;
  fns: string[];
}

/** Growth snapshot. */
export interface GrowthSnapshot {
  ts: number;
  raw: number;
  compressed: number;
  ratio: number;
  patterns: number;
  errorRate: number;
  evolutions: number;
  score: number;
}

/** Collective status. */
export interface CollectiveStatus {
  agents: AgentStatus[];
  networkMessages: number;
}
