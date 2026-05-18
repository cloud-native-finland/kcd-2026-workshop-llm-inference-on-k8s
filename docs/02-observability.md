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

## Alerts in your namespace

`scripts/01-deploy.sh` also applies a `PrometheusRule` from
[`helm/prometheus-rule.yaml`](../helm/prometheus-rule.yaml) into your
namespace. It defines two alerts:

| Alert | Severity | Fires when |
|---|---|---|
| `vLLMQueueDeep`   | warning  | `vllm:num_requests_waiting > 5` sustained for 1 min |
| `vLLMEngineDown`  | critical | No vLLM engine replicas are Ready for 30 s |

These will sit silent at idle. The first one is interesting because it
fires on **exactly the same signal KEDA scales on** — so during Scenario 2
you'll see KEDA scale up *and* the alert fire (and then clear once a
second replica drains the queue, or stay firing if there's no GPU spare).

The cluster's Prometheus is configured with `enforcedNamespaceLabel`, so
the operator silently rewrites every expression in your rule to add
`{namespace="<your-ns>"}` — your alerts can only see your own group's
metrics, no matter what you write.

See firing alerts at <http://localhost:9093/#/alerts> (Alertmanager UI).

Next: [03 — Scenario 1: Chat](03-chat.md)
