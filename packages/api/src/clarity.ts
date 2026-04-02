/**
 * Clarity — Transparent decision types for TypeScript.
 *
 * `decision()` enforces non-empty explanation at runtime.
 * The WORM log is append-only — no delete, no modify.
 */

import type { Decision, AuditEntry } from "./types";

export function decision<T>(
  value: T,
  explain: string,
  confidence: number,
  agent: string,
): Decision<T> {
  if (!explain) throw new Error("clarity: decision without explanation");
  if (confidence < 0 || confidence > 1) throw new Error("clarity: confidence must be 0–1");
  const audit: AuditEntry = {
    ts: Date.now(),
    agent,
    action: String(value),
    explain,
    inputHash: "",
  };
  return { value, explain, confidence, audit };
}

/** Append-only audit log. No delete. No modify. */
export class WormLog {
  private entries: AuditEntry[] = [];

  append(entry: AuditEntry) {
    Object.freeze(entry);
    this.entries.push(entry);
  }

  all(): readonly AuditEntry[] {
    return this.entries;
  }

  get length() {
    return this.entries.length;
  }
}
