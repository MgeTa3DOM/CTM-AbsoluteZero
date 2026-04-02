import { describe, test, expect } from "bun:test";
import { Scheduler, FibCache, GOLDEN_ANGLE } from "./fibra";
import { decision, WormLog } from "./clarity";

describe("Fibra Scheduler", () => {
  test("no angle collision in 64 tasks", () => {
    const s = new Scheduler(64);
    const angles: number[] = [];
    for (let i = 0; i < 64; i++) {
      const t = s.schedule()!;
      for (const a of angles) {
        expect(Math.abs(t.angle - a)).toBeGreaterThan(0.01);
      }
      angles.push(t.angle);
    }
  });

  test("capacity limit", () => {
    const s = new Scheduler(4);
    for (let i = 0; i < 4; i++) expect(s.schedule()).not.toBeNull();
    expect(s.schedule()).toBeNull();
  });

  test("complete frees slot", () => {
    const s = new Scheduler(2);
    const t1 = s.schedule()!;
    s.schedule();
    expect(s.schedule()).toBeNull();
    s.complete(t1.id);
    expect(s.schedule()).not.toBeNull();
  });

  test("retry escalates timeout level", () => {
    const s = new Scheduler(8);
    const t = s.schedule()!;
    expect(t.timeoutLevel).toBe(0);
    const t2 = s.retry(t.id)!;
    expect(t2.timeoutLevel).toBe(1);
    const t3 = s.retry(t.id)!;
    expect(t3.timeoutLevel).toBe(2);
  });

  test("uniform distribution", () => {
    const s = new Scheduler(256);
    const counts = new Array(256).fill(0);
    for (let i = 0; i < 256; i++) {
      const t = s.schedule()!;
      counts[t.slot]++;
    }
    const max = Math.max(...counts);
    expect(max).toBeLessThanOrEqual(3);
  });
});

describe("FibCache", () => {
  test("put and get", () => {
    const c = new FibCache<string, number>();
    c.put("a", 1);
    expect(c.get("a")).toBe(1);
  });

  test("eviction cascade (max 55 entries)", () => {
    const c = new FibCache<number, number>();
    for (let i = 0; i < 60; i++) c.put(i, i * 10);
    expect(c.size).toBeLessThanOrEqual(55);
  });

  test("recent items accessible", () => {
    const c = new FibCache<number, number>();
    for (let i = 0; i < 30; i++) c.put(i, i);
    expect(c.get(29)).toBe(29);
  });
});

describe("Clarity", () => {
  test("decision requires explanation", () => {
    const d = decision("high", "score 0.9 > threshold 0.8", 0.9, "agent1");
    expect(d.value).toBe("high");
    expect(d.explain).toBeTruthy();
    expect(d.confidence).toBe(0.9);
  });

  test("empty explain throws", () => {
    expect(() => decision("x", "", 0.5, "a")).toThrow("without explanation");
  });

  test("bad confidence throws", () => {
    expect(() => decision("x", "reason", 1.5, "a")).toThrow("confidence");
  });

  test("WORM log is append-only", () => {
    const log = new WormLog();
    const d = decision("ok", "reason", 0.8, "test");
    log.append(d.audit);
    log.append(d.audit);
    expect(log.length).toBe(2);
    expect(log.all().length).toBe(2);
    // No delete or modify methods exist
    expect((log as any).delete).toBeUndefined();
    expect((log as any).modify).toBeUndefined();
  });

  test("audit entries are frozen", () => {
    const log = new WormLog();
    const d = decision("ok", "reason", 0.8, "test");
    log.append(d.audit);
    expect(() => { (log.all()[0] as any).agent = "hacked"; }).toThrow();
  });
});
