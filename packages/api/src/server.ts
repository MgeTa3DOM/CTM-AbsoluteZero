/**
 * LIVING CODE — Bun server with WebSocket streaming,
 * FFmpeg video pipeline, and Firecracker sandbox tracking.
 *
 * GET  /                  → Dashboard UI
 * GET  /health            → System status
 * GET  /stream/video      → MJPEG live stream (FFmpeg encoded)
 * WS   /stream/ws         → WebSocket latent-space frames
 *
 * POST /fibra/schedule    → Schedule a Fibra task
 * POST /fibra/complete    → Complete a task
 * GET  /fibra/status      → Scheduler status
 * POST /clarity/decide    → Make a decision (requires explain)
 * GET  /clarity/audit     → WORM audit log
 * GET  /sandbox/list      → List all microVMs
 * POST /sandbox/create    → Create a sandboxed agent
 * POST /sandbox/kill      → Kill a VM
 */

import { Scheduler, FibCache } from "./fibra";
import { decision, WormLog } from "./clarity";
import { LatentEmitter } from "./stream/latent";
import { renderFrameToPPM, spawnFFmpeg } from "./stream/ffmpeg";
import { SandboxManager, generateVMConfig } from "./sandbox/firecracker";
import type { ServerWebSocket } from "bun";

const dashboardHtml = await Bun.file(new URL("./dashboard.html", import.meta.url).pathname).text();

// --- State ---

const scheduler = new Scheduler(64);
const wormLog = new WormLog();
const cache = new FibCache<string, string>();
const latent = new LatentEmitter(["alice", "bob", "carol"]);
const sandbox = new SandboxManager();

// Track connected WebSocket clients
const wsClients = new Set<ServerWebSocket<unknown>>();

// --- Latent stream tick (30fps) ---

let tickInterval: ReturnType<typeof setInterval>;

function startLatentStream() {
  tickInterval = setInterval(() => {
    const frame = latent.tick();
    const payload = JSON.stringify(frame);
    for (const ws of wsClients) {
      ws.send(payload);
    }
  }, 33); // ~30fps
}

startLatentStream();

// --- Server ---

const server = Bun.serve({
  port: Number(process.env.PORT) || 3000,

  async fetch(req, server) {
    const url = new URL(req.url);

    // --- Dashboard ---
    if (url.pathname === "/") {
      return new Response(dashboardHtml, {
        headers: { "content-type": "text/html; charset=utf-8" },
      });
    }

    // --- WebSocket upgrade ---
    if (url.pathname === "/stream/ws") {
      const ok = server.upgrade(req);
      if (ok) return undefined as any;
      return json({ error: "WebSocket upgrade failed" }, 400);
    }

    // --- MJPEG video stream ---
    if (url.pathname === "/stream/video") {
      return new Response(
        new ReadableStream({
          start(controller) {
            const w = 640, h = 480;
            const iv = setInterval(() => {
              try {
                const frame = latent.tick();
                const ppm = renderFrameToPPM(frame, w, h);
                // MJPEG: each frame is a JPEG-like boundary
                const boundary = "--frame\r\nContent-Type: image/x-portable-pixmap\r\n\r\n";
                controller.enqueue(Buffer.from(boundary));
                controller.enqueue(ppm);
                controller.enqueue(Buffer.from("\r\n"));
              } catch {
                clearInterval(iv);
                controller.close();
              }
            }, 66); // 15fps for video stream
          },
        }),
        {
          headers: {
            "content-type": "multipart/x-mixed-replace; boundary=--frame",
            "cache-control": "no-cache",
          },
        },
      );
    }

    // --- Fibra ---
    if (url.pathname === "/fibra/schedule" && req.method === "POST") {
      const task = scheduler.schedule();
      if (!task) return json({ error: "scheduler full" }, 429);
      latent.pushEvent("system", { thought: `scheduled task #${task.id}` });
      return json(task);
    }

    if (url.pathname === "/fibra/complete" && req.method === "POST") {
      try {
        const { id } = await req.json() as { id: number };
        const task = scheduler.complete(id);
        if (!task) return json({ error: "not found" }, 404);
        return json(task);
      } catch {
        return json({ error: "invalid json" }, 400);
      }
    }

    if (url.pathname === "/fibra/status") {
      return json({ active: scheduler.activeCount, slots: scheduler.slots });
    }

    // --- Clarity ---
    if (url.pathname === "/clarity/decide" && req.method === "POST") {
      try {
        const body = await req.json() as {
          value: string; explain: string; confidence: number; agent: string;
        };
        const d = decision(body.value, body.explain, body.confidence, body.agent);
        wormLog.append(d.audit);
        latent.pushWormEntry();
        latent.pushEvent(body.agent, {
          state: "executing",
          thought: `decided: ${body.value}`,
          confidence: body.confidence,
        });
        return json(d);
      } catch (e: any) {
        return json({ error: e.message }, 400);
      }
    }

    if (url.pathname === "/clarity/audit") {
      return json({ entries: wormLog.all(), count: wormLog.length });
    }

    // --- Sandbox ---
    if (url.pathname === "/sandbox/list") {
      return json({ vms: sandbox.list(), stats: sandbox.stats() });
    }

    if (url.pathname === "/sandbox/create" && req.method === "POST") {
      try {
        const body = await req.json() as { agentId: string; memMb?: number; vcpus?: number };
        const vmId = `vm-${body.agentId}-${Date.now()}`;
        const config = {
          vmId,
          agentId: body.agentId,
          memMb: body.memMb || 128,
          vcpus: body.vcpus || 1,
          timeoutSec: 21, // Fibonacci max
          rootfsPath: "/var/lib/firecracker/rootfs.ext4",
          kernelPath: "/var/lib/firecracker/vmlinux",
          tapDevice: `tap-${body.agentId}`,
          wormMount: "/var/lib/firecracker/worm.img",
          capabilities: ["read_file", "classify"],
          denied: ["write_file", "network"],
        };
        const vmConfig = generateVMConfig(config);
        const status = sandbox.create(config);
        latent.addAgent(body.agentId);
        latent.pushEvent(body.agentId, { state: "executing", thought: "VM booted" });
        return json({ status, config: vmConfig });
      } catch {
        return json({ error: "invalid json" }, 400);
      }
    }

    if (url.pathname === "/sandbox/kill" && req.method === "POST") {
      try {
        const { vmId } = await req.json() as { vmId: string };
        const ok = sandbox.kill(vmId);
        return json({ killed: ok });
      } catch {
        return json({ error: "invalid json" }, 400);
      }
    }

    // --- Health ---
    if (url.pathname === "/health") {
      return json({
        status: "ok",
        stack: "rust+uv+bun+ffmpeg+firecracker",
        scheduler: { active: scheduler.activeCount, slots: scheduler.slots },
        audit: { entries: wormLog.length },
        sandbox: sandbox.stats(),
        stream: { clients: wsClients.size, fps: 30 },
      });
    }

    return json({ error: "not found" }, 404);
  },

  websocket: {
    open(ws) {
      wsClients.add(ws);
      ws.send(JSON.stringify({ type: "connected", agents: ["alice", "bob", "carol"] }));
    },
    close(ws) {
      wsClients.delete(ws);
    },
    message(ws, msg) {
      // Client can inject events: { agent: "alice", state: "thinking", thought: "..." }
      try {
        const event = JSON.parse(String(msg));
        if (event.agent) {
          latent.pushEvent(event.agent, event);
        }
      } catch { /* ignore bad messages */ }
    },
  },
});

function json(data: unknown, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "content-type": "application/json" },
  });
}

console.log(`LIVING CODE server on http://localhost:${server.port}`);
console.log(`  Dashboard:  http://localhost:${server.port}/`);
console.log(`  WebSocket:  ws://localhost:${server.port}/stream/ws`);
console.log(`  Video:      http://localhost:${server.port}/stream/video`);
console.log(`  Health:     http://localhost:${server.port}/health`);
