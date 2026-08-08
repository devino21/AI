# llama-live dashboard

`llama-live.html` is a read-only monitoring dashboard for a Linux inference host running **llama-swap and llama.cpp**. It combines model-fleet state, live inference performance, GPU telemetry, host health, and per-model token history in one browser view.

## Does it need llama-swap?

**This version does.** It is not currently a standalone llama.cpp dashboard.

llama.cpp provides the actual inference telemetry:

- `/metrics`
- `/slots`
- `/props`

The dashboard also depends on llama-swap for:

- `/v1/models`, including each model's `loaded`, `loading`, or `unloaded` state
- `/running`, including the active child address and exact llama-server command
- Fleet aliases and model descriptions
- Model-load transitions and load-time measurement
- Host metrics as a lower-resolution fallback
- Finding the correct llama-server child when llama-swap assigns a dynamic port

A plain llama-server `/v1/models` response does not contain the llama-swap status information this page uses to select the active model. Without that state, the current JavaScript treats the model as `unknown`, does not select it as active, and therefore does not poll its slots or metrics.

Supporting plain llama.cpp would require a separate single-server mode that:

1. Treats the single model returned by llama-server as loaded.
2. Stops requesting llama-swap's `/running` endpoint.
3. Reads `/props`, `/slots`, and `/metrics` directly from the configured llama-server.
4. Disables or replaces llama-swap-based fleet and token-history logic.

That mode is **not implemented in this file**.

## Components

The complete deployment has four pieces:

| Component | Default port | Required? | Purpose |
| --- | ---: | --- | --- |
| llama-swap | `8080` | Yes | Fleet state, aliases, `/running`, orchestration, and host-metric fallback |
| llama-server | Dynamic child ports | Yes | Inference plus `/props`, `/slots`, and `/metrics` |
| Read-only model monitor | `8081` | Yes for live llama.cpp panels | Safely forwards telemetry only to a child that llama-swap says is already running |
| llama-host-agent | `8082` | Recommended | Serves the page, adds CORS, GPU/host telemetry, and persistent token history |

The working topology is:

```text
Browser
  |
  +-- :8082 llama-host-agent
  |      +-- serves llama-live.html
  |      +-- /host  (CPU, RAM, swap, disk, network, processes)
  |      +-- /gpu   (nvidia-smi)
  |      +-- /history
  |      `-- CORS proxy -> llama-swap :8080
  |
  +-- :8081 read-only model monitor
         +-- asks llama-swap :8080/running
         `-- forwards /props, /slots, /metrics
             to the already-running llama-server child

llama-swap :8080
  `-- starts/stops llama-server children on dynamic localhost ports
```

## Repository status

At present, this directory contains only:

```text
llame-dash/
├── README.md
└── llama-live.html
```

The HTML refers to two companion programs that are not yet included here:

- `llama-host-agent.py`
- `llama-readonly-monitor.py`, the read-only port-8081 model monitor

For a reproducible standalone repository, copy the two helper programs into this project and document/version their service units alongside them.

## What the dashboard monitors

### llama.cpp inference

- Active model and quantization
- Context size and occupancy
- K/V cache type
- Tensor split and GPU count
- Batch and microbatch sizes
- Speculative/MTP configuration
- Live decode throughput
- Per-request prefill and decode throughput
- Prefill time used as a TTFT estimate
- Mean inter-token latency
- Prompt-cache reuse
- Requests processing and deferred
- Tokens per decode as a speculative-decoding efficiency indicator
- Prompt/output token totals
- Model-local p50 and p95 performance

### llama-swap fleet

- Loaded, loading, and unloaded models
- Model switches
- Exact running llama-server command
- Model-load duration
- Per-model session aggregates
- 24-hour prompt/output token totals when the host agent is running

### GPU

When `llama-host-agent.py`, DCGM Exporter, or another supported GPU endpoint is available:

- Utilization
- VRAM used and total
- Temperature
- Power draw and power limit
- SM and memory clocks
- Fan speed
- PCIe generation and width
- Power or thermal throttling
- GPU-owning processes and per-process VRAM
- Tokens per second per watt
- Estimated Wh per 1,000 output tokens

### Linux host

With the host agent:

- Per-core and aggregate CPU utilization
- CPU package temperature, when exposed by `/sys/class/hwmon`
- RAM used and available
- Page cache and dirty pages
- Swap use
- 1, 5, and 15-minute load average
- Network receive/transmit rate
- Disk read/write throughput
- Inference-process RSS and thread count
- Host uptime

Page-cache and disk measurements are particularly useful for mmap-loaded GGUF models: an apparently loaded model may still have a slow first request if its file-backed pages were evicted.

## Accuracy caveats

- The dashboard's TTFT value is derived from llama.cpp prompt-processing time. It is not client-observed end-to-end TTFT and excludes some queue, HTTP, and network latency.
- Its end-to-end request value is prompt-processing time plus decode time, not browser-to-server wall time.
- A completed request is inferred from llama.cpp counter deltas.
- Historical metrics survive browser closure only when `llama-host-agent.py` is running with a writable state file.
- VRAM, power, thermals, throttling, disk rates, and process ownership cannot be inferred from llama.cpp alone.

## Host requirements

Required:

- Linux
- Python 3 using only the standard library for the host agent
- llama-swap
- llama.cpp `llama-server`
- llama-server started with `--metrics`
- Browser access to the selected ports

For full GPU telemetry:

- NVIDIA driver
- `nvidia-smi` on the inference host

The agent reads `/proc`, `/sys`, and `nvidia-smi`. Its only persistent write is the token-history JSON file.

## Recommended deployment

Serve the dashboard from the inference machine rather than opening it through `file://`. This gives the page a stable HTTP origin and allows the port-8082 agent to supply CORS-safe access to llama-swap.

The account and paths below are examples, not requirements. Create a dedicated
unprivileged service account named `llama-agent`, or replace `User`, `Group`,
`ExecStart`, `--root`, and `--state` with values appropriate for your system.
Ensure that account can run `nvidia-smi`; some distributions require membership
in a GPU-access group such as `video` or `render`.

An example systemd service is:

```ini
[Unit]
Description=llama-host-agent - read-only host & GPU telemetry for llama.cpp
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=llama-agent
Group=llama-agent
ExecStart=/usr/bin/python3 /opt/llama-agent/llama-host-agent.py \
  --port 8082 --upstream http://localhost:8080 \
  --root /opt/llama-agent/web --index llama-live.html \
  --state /var/lib/llama-agent/token-history.json
Restart=always
RestartSec=3
StateDirectory=llama-agent
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=read-only
ProtectControlGroups=true
ProtectKernelModules=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

The port-8081 read-only monitor is a separate service. It must be able to:

1. Read `http://127.0.0.1:8080/running`.
2. Match the requested model ID to a child in the `ready` state.
3. Forward only GET requests for `props`, `slots`, and `metrics` to that child's localhost proxy.
4. Refuse requests for models that are not already running.

This protection matters: polling an unloaded llama-swap model through its normal inference route could trigger a model load. The monitor avoids that side effect.

After installing or updating a service unit:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now llama-host-agent.service
```

Then open:

```text
http://LLAMA_HOST:8082/
```

## Dashboard connection options

The server box in the page changes the llama-swap address. It is also saved in browser `localStorage`.

URL query parameters can override individual endpoints:

| Parameter | Example | Meaning |
| --- | --- | --- |
| `host` | `?host=llama-host:8080` | llama-swap base URL |
| `monitorPort` | `?monitorPort=8081` | Read-only child-monitor port |
| `agent` | `?agent=http://llama-host:8082` | Host-agent base URL |
| `proxy` | `?proxy=http://llama-host:8082` | CORS proxy for llama-swap endpoints |
| `gpu` | `?gpu=http://llama-host:8082/gpu` | Explicit GPU JSON or Prometheus endpoint |

The GPU panel can also consume selected metrics from:

- NVIDIA DCGM Exporter, normally port `9400`
- `nvidia_gpu_exporter`, commonly port `9835`
- A compatible JSON `nvidia-smi` shim

## Health checks

From another machine on the permitted network:

```bash
curl -fsS http://LLAMA_HOST:8082/health
curl -fsS http://LLAMA_HOST:8082/host
curl -fsS http://LLAMA_HOST:8082/gpu
curl -fsS 'http://LLAMA_HOST:8082/history?hours=24'

curl -fsS http://LLAMA_HOST:8080/v1/models
curl -fsS http://LLAMA_HOST:8080/running
curl -fsS http://LLAMA_HOST:8080/metrics
```

When a model is already loaded, test the model monitor with its URL-encoded model ID:

```bash
curl -fsS http://LLAMA_HOST:8081/model/MODEL_ID/props
curl -fsS http://LLAMA_HOST:8081/model/MODEL_ID/slots
curl -fsS http://LLAMA_HOST:8081/model/MODEL_ID/metrics
```

If the model ID contains spaces or reserved URL characters, URL-encode it first.

## Troubleshooting

### Fleet loads, but host metrics do not

The browser can reach `/v1/models`, but llama-swap may not send CORS headers on `/metrics` or `/running`. Serve the page through `llama-host-agent.py` on port 8082 or set `?proxy=` to a compatible CORS proxy.

### llama source is red or unavailable

Check that:

- A model is already loaded.
- The read-only monitor is listening on port 8081.
- The client IP is allowed by the monitor.
- The active llama-server was started with `--metrics`.
- `/slots` and `/props` are available in the installed llama.cpp build.

### GPU panel is empty

Run:

```bash
nvidia-smi
curl -fsS http://127.0.0.1:8082/gpu
```

If `nvidia-smi` works but `/gpu` does not, inspect the host-agent service log:

```bash
journalctl -u llama-host-agent.service -n 100 --no-pager
```

### History remains empty

History starts with a counter baseline and records later deltas. Confirm:

- llama-swap `/running` lists the active model.
- The child exposes `/metrics`.
- The state directory is writable by the service.
- At least one request completed after the history sampler started.

## Security

The dashboard and helper agent are designed to be read-only, but the reference host agent:

- Binds to `0.0.0.0` by default.
- Sends `Access-Control-Allow-Origin: *`.
- Has no built-in authentication or TLS.
- Exposes process, hardware, and model-fleet information.

Keep ports 8080–8082 on a trusted LAN, restrict them with a firewall, or place them behind an authenticated TLS reverse proxy. Do not expose the reference deployment directly to the public internet.

Clicking a loaded model in the fleet table only changes which already-running model the page watches. Unloaded rows are deliberately inert.
