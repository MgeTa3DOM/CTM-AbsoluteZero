/**
 * FFmpeg Live Stream Pipeline
 *
 * Captures the latent-space visualization frames and encodes them
 * into a live video stream (MJPEG over HTTP or raw H.264 chunks).
 *
 * Flow:
 *   LatentEmitter → JSON frames → Canvas render (browser)
 *                                       ↓
 *                               FFmpeg stdin (raw RGB)
 *                                       ↓
 *                               H.264/MJPEG stream
 *                                       ↓
 *                               HTTP chunked response
 *
 * For the server-side path (headless rendering), we generate
 * raw PPM frames and pipe them into FFmpeg.
 */

import { spawn, type Subprocess } from "bun";
import type { LatentFrame } from "./latent";

export interface StreamConfig {
  width: number;
  height: number;
  fps: number;
  format: "mjpeg" | "h264" | "rawvideo";
  /** FFmpeg output: "pipe" for HTTP streaming, or a file path */
  output: "pipe" | string;
}

const DEFAULT_CONFIG: StreamConfig = {
  width: 640,
  height: 480,
  fps: 15,
  format: "mjpeg",
  output: "pipe",
};

/**
 * Render a LatentFrame as a raw PPM image (P6 binary).
 * Simple but real — each agent is a dot, connections are lines,
 * background color reflects collective IQ.
 */
export function renderFrameToPPM(frame: LatentFrame, w: number, h: number): Buffer {
  const pixels = Buffer.alloc(w * h * 3);

  // Background: dark, tinted by collective IQ
  const bgR = Math.floor(10 + frame.global.collectiveIQ * 15);
  const bgG = Math.floor(10 + frame.global.compressionRatio * 5);
  const bgB = Math.floor(20 + frame.global.fibraAngle * 0.1);
  for (let i = 0; i < w * h; i++) {
    pixels[i * 3] = bgR;
    pixels[i * 3 + 1] = bgG;
    pixels[i * 3 + 2] = bgB;
  }

  // Draw attention lines between agents
  for (const agent of frame.agents) {
    const ax = Math.floor((agent.pos[0] + 1) * 0.5 * (w - 1));
    const ay = Math.floor((agent.pos[1] + 1) * 0.5 * (h - 1));

    for (const [otherId, weight] of Object.entries(agent.attention)) {
      if (weight < 0.3) continue;
      const other = frame.agents.find(a => a.id === otherId);
      if (!other) continue;
      const bx = Math.floor((other.pos[0] + 1) * 0.5 * (w - 1));
      const by = Math.floor((other.pos[1] + 1) * 0.5 * (h - 1));

      // Bresenham line
      drawLine(pixels, w, h, ax, ay, bx, by,
        Math.floor(weight * 80), Math.floor(weight * 120), Math.floor(weight * 200));
    }
  }

  // Draw agents as circles
  for (const agent of frame.agents) {
    const cx = Math.floor((agent.pos[0] + 1) * 0.5 * (w - 1));
    const cy = Math.floor((agent.pos[1] + 1) * 0.5 * (h - 1));
    const radius = 6 + Math.floor(agent.confidence * 8);

    // Color by state
    let r = 100, g = 200, b = 100;
    if (agent.state === "executing") { r = 50; g = 200; b = 255; }
    else if (agent.state === "error") { r = 255; g = 60; b = 60; }
    else if (agent.state === "evolving") { r = 255; g = 200; b = 50; }
    else if (agent.state === "thinking") { r = 150; g = 100; b = 255; }

    drawCircle(pixels, w, h, cx, cy, radius, r, g, b);

    // Embedding sparkline (small bar under agent)
    for (let i = 0; i < Math.min(16, agent.embedding.length); i++) {
      const ex = cx - 8 + i;
      const ey = cy + radius + 4;
      const val = Math.floor((agent.embedding[i] + 1) * 0.5 * 255);
      setPixel(pixels, w, h, ex, ey, val, val * 0.7, 50);
    }
  }

  // PPM header
  const header = Buffer.from(`P6\n${w} ${h}\n255\n`);
  return Buffer.concat([header, pixels]);
}

function setPixel(buf: Buffer, w: number, h: number, x: number, y: number, r: number, g: number, b: number) {
  if (x < 0 || x >= w || y < 0 || y >= h) return;
  const i = (y * w + x) * 3;
  buf[i] = Math.floor(Math.min(255, r));
  buf[i + 1] = Math.floor(Math.min(255, g));
  buf[i + 2] = Math.floor(Math.min(255, b));
}

function drawCircle(buf: Buffer, w: number, h: number, cx: number, cy: number, r: number, cr: number, cg: number, cb: number) {
  for (let dy = -r; dy <= r; dy++) {
    for (let dx = -r; dx <= r; dx++) {
      if (dx * dx + dy * dy <= r * r) {
        setPixel(buf, w, h, cx + dx, cy + dy, cr, cg, cb);
      }
    }
  }
}

function drawLine(buf: Buffer, w: number, h: number, x0: number, y0: number, x1: number, y1: number, r: number, g: number, b: number) {
  const dx = Math.abs(x1 - x0), dy = Math.abs(y1 - y0);
  const sx = x0 < x1 ? 1 : -1, sy = y0 < y1 ? 1 : -1;
  let err = dx - dy;
  let steps = 0;
  const maxSteps = dx + dy + 1;
  while (steps++ < maxSteps) {
    setPixel(buf, w, h, x0, y0, r, g, b);
    if (x0 === x1 && y0 === y1) break;
    const e2 = 2 * err;
    if (e2 > -dy) { err -= dy; x0 += sx; }
    if (e2 < dx) { err += dx; y0 += sy; }
  }
}

/**
 * Spawn an FFmpeg process that accepts raw PPM frames on stdin
 * and outputs encoded video on stdout.
 */
export function spawnFFmpeg(config: Partial<StreamConfig> = {}): Subprocess {
  const c = { ...DEFAULT_CONFIG, ...config };

  const args = [
    "ffmpeg",
    "-y",
    "-f", "ppm_pipe",
    "-framerate", String(c.fps),
    "-i", "pipe:0",
    ...(c.format === "mjpeg" ? [
      "-c:v", "mjpeg",
      "-q:v", "5",
      "-f", "mjpeg",
    ] : c.format === "h264" ? [
      "-c:v", "libx264",
      "-preset", "ultrafast",
      "-tune", "zerolatency",
      "-f", "h264",
    ] : [
      "-c:v", "rawvideo",
      "-pix_fmt", "rgb24",
      "-f", "rawvideo",
    ]),
    c.output === "pipe" ? "pipe:1" : c.output,
  ];

  return spawn({
    cmd: args,
    stdin: "pipe",
    stdout: "pipe",
    stderr: "ignore",
  });
}

export { DEFAULT_CONFIG };
