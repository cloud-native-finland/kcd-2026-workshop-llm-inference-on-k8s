# 2 — Observability

Open Grafana at <http://localhost:3000> — login `admin` / `prom-operator`
(default kube-prom-stack password; the workshop cluster doesn't change it).

## Where the data comes from

Every vLLM pod — yours and every other group's — exposes a `/metrics`
endpoint on its own port. The cluster's Prometheus is configured with an
`additionalServiceMonitors` rule that auto-picks up any vLLM Helm release
in any namespace, so your engine and router start getting scraped the
moment they go Ready.

If you ever wonder "is Prometheus actually scraping my pods?" —
<http://localhost:9090/targets> and search for your namespace.

## What to look at at idle

In Grafana → Dashboards, look for the **vLLM** dashboards (auto-imported
from the production-stack chart's bundled ConfigMaps). The panels you'll
return to during the load scenarios:

| Panel | Metric | What it tells you |
|---|---|---|
| Time-to-First-Token (TTFT) | `vllm:time_to_first_token_seconds` | How long the user waits before any tokens appear. Queueing shows up here. |
| Generation throughput | `vllm:generation_tokens_total` (rate) | How fast tokens are produced across all your requests. |
| Running requests | `vllm:num_requests_running` | How many requests the engine is actively decoding. |
| Queue depth | `vllm:num_requests_waiting` | Requests that arrived but haven't started decoding. **KEDA scales on this.** |
| GPU KV cache usage | `vllm:gpu_cache_usage_perc` | How much of the engine's KV-cache memory is in use. |

At idle they should sit at zero. That's the baseline you'll compare the
next three scenarios against.

## A few useful Prometheus queries

Paste into <http://localhost:9090> or Grafana's Explore tab. Add a
`{namespace="$MY_NAMESPACE"}` filter to isolate your group's traffic from
everyone else's:

```promql
vllm:num_requests_waiting{namespace="group-XX"}
```

```promql
rate(vllm:generation_tokens_total{namespace="group-XX"}[1m])
```

```promql
histogram_quantile(
  0.95,
  sum(rate(vllm:time_to_first_token_seconds_bucket{namespace="group-XX"}[1m]))
    by (le)
)
```

Next: [03 — Scenario 1: Chat](03-chat.md)
