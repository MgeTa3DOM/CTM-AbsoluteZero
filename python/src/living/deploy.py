"""
Deployment config generator.

Generates:
- Dockerfile (multi-stage: Rust + Python + Bun)
- docker-compose.yml (all services + volumes)
- fly.toml / railway.json for cloud deploy
- n8n webhook config for Google Drive sync
- Cron config for auto-refinement cycles
"""

from __future__ import annotations
import json


def dockerfile() -> str:
    return '''# LIVING CODE — Multi-stage build
# Stage 1: Rust (Fibra + Clarity)
FROM rust:1.94-slim AS rust-build
WORKDIR /app
COPY Cargo.toml Cargo.lock ./
COPY crates/ crates/
RUN cargo build --release
RUN cargo test --release

# Stage 2: Python (Living Code agents)
FROM python:3.11-slim AS python-build
WORKDIR /app
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv
COPY python/ python/
WORKDIR /app/python
RUN uv sync
RUN uv run python -m pytest tests/ -v

# Stage 3: Bun (API + Dashboard + Stream)
FROM oven/bun:1.3 AS bun-build
WORKDIR /app
COPY packages/api/ packages/api/
WORKDIR /app/packages/api
RUN bun install
RUN bun test

# Stage 4: Runtime
FROM oven/bun:1.3-slim
WORKDIR /app

# Install FFmpeg for video streaming
RUN apt-get update -qq && apt-get install -y -qq ffmpeg && rm -rf /var/lib/apt/lists/*

# Copy Rust binaries
COPY --from=rust-build /app/target/release/ /app/bin/

# Copy Python
COPY --from=python-build /app/python/ /app/python/
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copy Bun API
COPY --from=bun-build /app/packages/api/ /app/packages/api/

# Dataset volume mount point (144GB Google Drive sync target)
VOLUME /data/dataset
ENV DATASET_PATH=/data/dataset
ENV GDRIVE_FOLDER_ID=""

EXPOSE 3000

CMD ["bun", "run", "/app/packages/api/src/server.ts"]
'''


def docker_compose() -> str:
    return '''version: "3.9"

services:
  api:
    build: .
    ports:
      - "3000:3000"
    environment:
      - PORT=3000
      - DATASET_PATH=/data/dataset
      - GDRIVE_FOLDER_ID=${GDRIVE_FOLDER_ID}
      - REFINEMENT_INTERVAL=3600
    volumes:
      - dataset:/data/dataset
      - worm:/data/worm
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 5s
      retries: 3

  # Auto-refinement cron (runs every hour)
  refiner:
    build: .
    entrypoint: ["uv", "run", "--project", "/app/python", "python", "-m", "living.refine_cron"]
    environment:
      - DATASET_PATH=/data/dataset
      - REFINEMENT_INTERVAL=3600
    volumes:
      - dataset:/data/dataset
      - worm:/data/worm
    restart: unless-stopped

  # Google Drive sync (picks up upload queue, syncs to Drive)
  gdrive-sync:
    image: rclone/rclone:latest
    entrypoint: >
      sh -c "while true; do
        rclone sync /data/dataset gdrive:living-code-dataset
          --config /config/rclone.conf
          --max-size 144G
          --log-level INFO;
        sleep 300;
      done"
    volumes:
      - dataset:/data/dataset
      - ./config/rclone.conf:/config/rclone.conf:ro
    restart: unless-stopped

volumes:
  dataset:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: ${DATASET_HOST_PATH:-./data/dataset}
  worm:
    driver: local
'''


def fly_toml() -> str:
    return '''app = "living-code"
primary_region = "cdg"

[build]
  dockerfile = "Dockerfile"

[http_service]
  internal_port = 3000
  force_https = true
  auto_stop_machines = false
  auto_start_machines = true
  min_machines_running = 1

[mounts]
  source = "dataset"
  destination = "/data/dataset"
  initial_size = "150"

[[vm]]
  size = "shared-cpu-2x"
  memory = "1024"
'''


def n8n_webhook_config() -> dict:
    """
    n8n workflow config for Google Drive sync.

    Import this into your n8n instance:
    1. Create a webhook trigger
    2. Connect to Google Drive node
    3. Point the API server to call this webhook after each dataset write
    """
    return {
        "name": "Living Code - Dataset Sync to Google Drive",
        "nodes": [
            {
                "name": "Webhook",
                "type": "n8n-nodes-base.webhook",
                "parameters": {
                    "path": "living-code-sync",
                    "httpMethod": "POST",
                    "responseMode": "onReceived",
                },
                "position": [250, 300],
            },
            {
                "name": "Google Drive Upload",
                "type": "n8n-nodes-base.googleDrive",
                "parameters": {
                    "operation": "upload",
                    "folderId": "={{ $json.folder_id }}",
                    "name": "={{ $json.path }}",
                    "binaryData": False,
                    "content": "={{ $json.data }}",
                },
                "position": [500, 300],
            },
            {
                "name": "Log to Sheet",
                "type": "n8n-nodes-base.googleSheets",
                "parameters": {
                    "operation": "append",
                    "sheetName": "Dataset Log",
                    "columns": "timestamp,agent,skill,version,correct,size_bytes",
                },
                "position": [750, 300],
            },
        ],
        "connections": {
            "Webhook": {"main": [[{"node": "Google Drive Upload", "type": "main", "index": 0}]]},
            "Google Drive Upload": {"main": [[{"node": "Log to Sheet", "type": "main", "index": 0}]]},
        },
    }


def generate_all(output_dir: str = ".") -> dict[str, str]:
    """Generate all deployment files."""
    from pathlib import Path
    out = Path(output_dir)

    files = {
        "Dockerfile": dockerfile(),
        "docker-compose.yml": docker_compose(),
        "fly.toml": fly_toml(),
        "config/n8n-workflow.json": json.dumps(n8n_webhook_config(), indent=2),
    }

    for name, content in files.items():
        path = out / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)

    return {name: str(out / name) for name in files}


if __name__ == "__main__":
    paths = generate_all()
    for name, path in paths.items():
        print(f"  {name} -> {path}")
