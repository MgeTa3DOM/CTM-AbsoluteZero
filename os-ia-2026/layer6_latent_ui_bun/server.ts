import { serve } from "bun";

console.log("Starting AI-OS Latent Space UI (Firecracker Sandbox Livestream)...");
console.log("Listening on http://localhost:3000");

// Simulated logs from the "LIVING CODE" agentic system
const actionVerbs = ["Analyzing", "Compiling", "Orchestrating", "Checking WORM integrity on", "Optimizing latent", "Re-routing neural paths via"];
const subjects = ["context tensors", "Golden Angle scheduler", "EvoLLM weights", "Swarm Consensus", "Firecracker micro-VM", "LSM Capabilities"];

function generateMockData() {
    const isAlert = Math.random() > 0.9;
    const logText = isAlert
        ? `ANOMALY DETECTED: HILT Escalation requested in ${subjects[Math.floor(Math.random() * subjects.length)]}`
        : `${actionVerbs[Math.floor(Math.random() * actionVerbs.length)]} ${subjects[Math.floor(Math.random() * subjects.length)]}`;

    return {
        log: logText,
        alert: isAlert,
        metrics: {
            context: Math.random(),
            attention: Math.random() * 2,
            entropy: Math.random() * 0.8 + 0.2
        }
    };
}

serve({
    port: 3000,
    async fetch(req) {
        const url = new URL(req.url);

        // Serve the HTML UI
        if (url.pathname === "/") {
            return new Response(Bun.file("index.html"), {
                headers: { "Content-Type": "text/html" }
            });
        }

        // Serve the SSE (Server-Sent Events) Stream for real-time 6D sensor metrics
        if (url.pathname === "/stream") {
            const stream = new ReadableStream({
                start(controller) {
                    const timer = setInterval(() => {
                        const data = JSON.stringify(generateMockData());
                        // SSE format requires "data: <payload>\n\n"
                        controller.enqueue(`data: ${data}\n\n`);
                    }, 500); // Send an update every 500ms

                    req.signal.addEventListener("abort", () => {
                        clearInterval(timer);
                        controller.close();
                    });
                }
            });

            return new Response(stream, {
                headers: {
                    "Content-Type": "text/event-stream",
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive"
                }
            });
        }

        return new Response("Not Found", { status: 404 });
    }
});
