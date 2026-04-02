/**
 * Latent Space Stream — Real-time agent thought visualization.
 *
 * Generates a continuous stream of latent-space snapshots:
 * - Agent activation vectors (simulated embeddings)
 * - Attention heatmap per agent
 * - Decision confidence trajectories
 * - Soul thought events
 *
 * Each frame is a JSON payload pushed via WebSocket.
 * The dashboard renders it as a live canvas animation.
 */

export interface LatentFrame {
  ts: number;
  frame: number;
  agents: AgentLatent[];
  global: GlobalState;
}

export interface AgentLatent {
  id: string;
  /** 2D projection of latent vector (for visualization) */
  pos: [number, number];
  /** Raw embedding slice (first 16 dims) */
  embedding: number[];
  /** Attention weights to other agents */
  attention: Record<string, number>;
  /** Current confidence level */
  confidence: number;
  /** Active skill + version */
  skill: string;
  skillVersion: number;
  /** Latest thought */
  thought: string;
  /** State: thinking | executing | idle | error | evolving */
  state: AgentState;
}

export type AgentState = "thinking" | "executing" | "idle" | "error" | "evolving";

export interface GlobalState {
  collectiveIQ: number;
  compressionRatio: number;
  networkMessages: number;
  activeAgents: number;
  evolutionCycle: number;
  wormEntries: number;
  fibraAngle: number;
  fibraActiveSlots: number;
}

const GOLDEN_ANGLE = 137.50776405003785;

/**
 * Latent space emitter.  In production, this reads from the actual
 * model's hidden states.  Here we simulate realistic dynamics:
 * - Agents drift in 2D space based on golden-angle rotation
 * - Confidence oscillates with task execution
 * - Attention weights shift during collaboration
 */
export class LatentEmitter {
  private frame = 0;
  private angle = 0;
  private agents: Map<string, AgentLatentState> = new Map();
  private msgCount = 0;
  private wormCount = 0;
  private evolutionCycle = 0;

  constructor(agentIds: string[]) {
    for (const id of agentIds) {
      this.agents.set(id, {
        id,
        x: Math.random() * 2 - 1,
        y: Math.random() * 2 - 1,
        vx: 0,
        vy: 0,
        confidence: 0.5 + Math.random() * 0.3,
        embedding: Array.from({ length: 16 }, () => Math.random() * 2 - 1),
        skill: "classify",
        skillVersion: 0,
        state: "idle" as AgentState,
        thought: "initializing",
      });
    }
  }

  addAgent(id: string) {
    this.agents.set(id, {
      id, x: Math.random() * 2 - 1, y: Math.random() * 2 - 1,
      vx: 0, vy: 0, confidence: 0.5,
      embedding: Array.from({ length: 16 }, () => Math.random() * 2 - 1),
      skill: "unknown", skillVersion: 0, state: "idle", thought: "joined",
    });
  }

  /** Inject an event (from actual agent execution) */
  pushEvent(agentId: string, event: {
    state?: AgentState;
    thought?: string;
    confidence?: number;
    skill?: string;
    skillVersion?: number;
  }) {
    const a = this.agents.get(agentId);
    if (!a) return;
    if (event.state) a.state = event.state;
    if (event.thought) a.thought = event.thought;
    if (event.confidence !== undefined) a.confidence = event.confidence;
    if (event.skill) a.skill = event.skill;
    if (event.skillVersion !== undefined) a.skillVersion = event.skillVersion;
    this.msgCount++;
  }

  pushWormEntry() {
    this.wormCount++;
  }

  pushEvolution() {
    this.evolutionCycle++;
  }

  /** Generate next frame */
  tick(): LatentFrame {
    this.frame++;
    this.angle = (this.angle + GOLDEN_ANGLE) % 360;
    const angleRad = (this.angle * Math.PI) / 180;

    const agentLatents: AgentLatent[] = [];
    const ids = [...this.agents.keys()];

    for (const [id, a] of this.agents) {
      // Drift position (golden-angle influenced)
      const drift = 0.02;
      a.vx = a.vx * 0.9 + Math.cos(angleRad + ids.indexOf(id)) * drift;
      a.vy = a.vy * 0.9 + Math.sin(angleRad + ids.indexOf(id)) * drift;
      a.x = Math.max(-1, Math.min(1, a.x + a.vx));
      a.y = Math.max(-1, Math.min(1, a.y + a.vy));

      // Evolve embedding (small perturbation)
      for (let i = 0; i < a.embedding.length; i++) {
        a.embedding[i] += (Math.random() - 0.5) * 0.05;
        a.embedding[i] = Math.max(-1, Math.min(1, a.embedding[i]));
      }

      // Confidence oscillation
      if (a.state === "executing") {
        a.confidence = Math.min(1, a.confidence + 0.01);
      } else if (a.state === "error") {
        a.confidence = Math.max(0, a.confidence - 0.05);
      }

      // Attention to other agents
      const attention: Record<string, number> = {};
      for (const otherId of ids) {
        if (otherId !== id) {
          const other = this.agents.get(otherId)!;
          const dist = Math.hypot(a.x - other.x, a.y - other.y);
          attention[otherId] = Math.max(0, 1 - dist);
        }
      }

      agentLatents.push({
        id,
        pos: [a.x, a.y],
        embedding: [...a.embedding],
        attention,
        confidence: a.confidence,
        skill: a.skill,
        skillVersion: a.skillVersion,
        thought: a.thought,
        state: a.state,
      });
    }

    const avgConf = agentLatents.reduce((s, a) => s + a.confidence, 0) / agentLatents.length;

    return {
      ts: Date.now(),
      frame: this.frame,
      agents: agentLatents,
      global: {
        collectiveIQ: avgConf * 1.5,
        compressionRatio: 2.5 + Math.sin(this.frame * 0.01) * 0.5,
        networkMessages: this.msgCount,
        activeAgents: this.agents.size,
        evolutionCycle: this.evolutionCycle,
        wormEntries: this.wormCount,
        fibraAngle: this.angle,
        fibraActiveSlots: this.agents.size,
      },
    };
  }
}

interface AgentLatentState {
  id: string;
  x: number; y: number;
  vx: number; vy: number;
  confidence: number;
  embedding: number[];
  skill: string;
  skillVersion: number;
  state: AgentState;
  thought: string;
}
