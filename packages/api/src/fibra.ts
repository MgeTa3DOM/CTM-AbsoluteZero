/**
 * Fibra — Golden-angle task scheduler (TypeScript port).
 *
 * Same algorithm as the Rust crate, usable from Bun/Node.
 */

import type { FibraTask } from "./types";

export const GOLDEN_ANGLE = 137.50776405003785;
const FIB_MS = [1000, 1000, 2000, 3000, 5000, 8000, 13000, 21000] as const;

export class Scheduler {
  private angle = 0;
  private nextId = 1;
  private active = new Map<number, FibraTask>();
  readonly slots: number;

  constructor(slots: number) {
    if (slots < 1 || slots > 256) throw new Error("slots must be 1–256");
    this.slots = slots;
  }

  schedule(): FibraTask | null {
    if (this.active.size >= this.slots) return null;
    const id = this.nextId++;
    this.angle = (this.angle + GOLDEN_ANGLE) % 360;
    const slot = Math.floor((this.angle / 360) * this.slots) % this.slots;
    const task: FibraTask = {
      id,
      angle: this.angle,
      slot,
      timeoutLevel: 0,
      createdAt: Date.now(),
    };
    this.active.set(id, task);
    return task;
  }

  complete(id: number): FibraTask | undefined {
    const t = this.active.get(id);
    this.active.delete(id);
    return t;
  }

  retry(id: number): FibraTask | undefined {
    const t = this.active.get(id);
    if (!t) return undefined;
    t.timeoutLevel++;
    t.createdAt = Date.now();
    this.angle = (this.angle + GOLDEN_ANGLE) % 360;
    t.angle = this.angle;
    t.slot = Math.floor((this.angle / 360) * this.slots) % this.slots;
    return t;
  }

  reap(): FibraTask[] {
    const now = Date.now();
    const expired: FibraTask[] = [];
    for (const [id, t] of this.active) {
      const timeout = FIB_MS[Math.min(t.timeoutLevel, FIB_MS.length - 1)];
      if (now - t.createdAt > timeout) {
        expired.push(t);
        this.active.delete(id);
      }
    }
    return expired;
  }

  get activeCount() {
    return this.active.size;
  }
}

/** Fibonacci-shaped cache. Capacities: 1 1 2 3 5 8 13 21 = 55 entries. */
export class FibCache<K, V> {
  private levels: [K, V][][];
  private caps = [1, 1, 2, 3, 5, 8, 13, 21];

  constructor() {
    this.levels = this.caps.map(() => []);
  }

  get(key: K): V | undefined {
    for (let lvl = 0; lvl < this.levels.length; lvl++) {
      const idx = this.levels[lvl].findIndex(([k]) => k === key);
      if (idx !== -1) {
        const [, v] = this.levels[lvl].splice(idx, 1)[0];
        this.putAt(0, key, v);
        return v;
      }
    }
    return undefined;
  }

  put(key: K, val: V) {
    this.putAt(0, key, val);
  }

  private putAt(lvl: number, key: K, val: V) {
    if (lvl >= this.levels.length) return;
    this.levels[lvl].unshift([key, val]);
    if (this.levels[lvl].length > this.caps[lvl]) {
      const evicted = this.levels[lvl].pop()!;
      this.putAt(lvl + 1, evicted[0], evicted[1]);
    }
  }

  get size() {
    return this.levels.reduce((sum, lvl) => sum + lvl.length, 0);
  }
}
