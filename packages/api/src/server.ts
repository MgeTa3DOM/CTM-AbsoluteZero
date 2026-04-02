/**
 * LIVING CODE API — Bun HTTP server.
 *
 * Exposes the Fibra scheduler, Clarity decisions, and agent
 * collective over a JSON API.  Runs on Bun for speed.
 */

import { Scheduler, FibCache } from "./fibra";
import { decision, WormLog } from "./clarity";
import type { CollectiveStatus } from "./types";

const scheduler = new Scheduler(64);
const wormLog = new WormLog();
const cache = new FibCache<string, string>();

const server = Bun.serve({
  port: Number(process.env.PORT) || 3000,

  async fetch(req) {
    const url = new URL(req.url);

    // --- Fibra ---
    if (url.pathname === "/fibra/schedule" && req.method === "POST") {
      const task = scheduler.schedule();
      if (!task) return json({ error: "scheduler full" }, 429);
      return json(task);
    }

    if (url.pathname === "/fibra/complete" && req.method === "POST") {
      const { id } = await req.json() as { id: number };
      const task = scheduler.complete(id);
      if (!task) return json({ error: "not found" }, 404);
      return json(task);
    }

    if (url.pathname === "/fibra/status") {
      return json({ active: scheduler.activeCount, slots: scheduler.slots });
    }

    // --- Clarity ---
    if (url.pathname === "/clarity/decide" && req.method === "POST") {
      const { value, explain, confidence, agent } = await req.json() as {
        value: string; explain: string; confidence: number; agent: string;
      };
      try {
        const d = decision(value, explain, confidence, agent);
        wormLog.append(d.audit);
        return json(d);
      } catch (e: any) {
        return json({ error: e.message }, 400);
      }
    }

    if (url.pathname === "/clarity/audit") {
      return json({ entries: wormLog.all(), count: wormLog.length });
    }

    // --- Health ---
    if (url.pathname === "/health") {
      return json({
        status: "ok",
        stack: "rust+uv+bun",
        scheduler: { active: scheduler.activeCount },
        audit: { entries: wormLog.length },
      });
    }

    return json({ error: "not found" }, 404);
  },
});

function json(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "content-type": "application/json" },
  });
}

console.log(`LIVING CODE API on http://localhost:${server.port}`);
