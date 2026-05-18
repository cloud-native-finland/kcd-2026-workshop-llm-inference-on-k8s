# 2 — Observability

Open Grafana at <http://localhost:3000> — login `admin` / `prom-operator`
(the workshop cluster's default; doesn't get rotated for a 2-hour run).

## Where the data comes from

Every vLLM pod — yours and every other group's — exposes a `/metrics`
endpoint on its own port. The cluster runs **GKE Managed Prometheus
(GMP)** with auto-app-monitoring at cluster scope, so GMP detects each
vLLM Deployment as it comes up and starts scraping automatically. No
per-group `ServiceMonitor` or `PodMonitoring` to apply.

Metrics live in Cloud Monitoring under the hood. Grafana queries them
through the in-cluster **GMP query frontend** (`gmp-frontend.monitoring.svc`),
which speaks the standard Prometheus query API. From Grafana's
perspective, it's talking to "a Prometheus" — same panels and queries
work the same way.

If you ever wonder "is GMP actually scraping my pods?" — port-forward
the GMP frontend (`localhost:9090`) and visit `/api/v1/targets`, or just
run a `vllm:num_requests_running` query in Grafana's Explore tab.

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

Paste into <http://localhost:9090> (the GMP frontend, port-forwarded) or
Grafana's Explore tab. Add a `{namespace="$MY_NAMESPACE"}` filter to
isolate your group's traffic from everyone else's:

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

`scripts/01-deploy.sh` also applies a GMP `Rules` resource from
[`helm/gmp-rules.yaml`](../helm/gmp-rules.yaml) into your namespace. It
defines two alerts:

| Alert | Severity | Fires when |
|---|---|---|
| `VLLMQueueDeep` | warning  | `vllm:num_requests_waiting > 5` sustained for 1 min |
| `VLLMEngineDown` | critical | No vLLM engine replicas are Ready for 30 s |

These will sit silent at idle. The first one is interesting because it
fires on **exactly the same signal KEDA scales on** — so during
Scenario 2 you'll see KEDA scale up *and* the alert fire (and then clear
once a second replica drains the queue, or stay firing if there's no GPU
slot spare).

GMP namespace-scoped `Rules` are auto-scoped by the GMP operator — your
alerts can only see your own group's metrics regardless of what the
query says.

Check rule status with:

```bash
kubectl -n "$MY_NAMESPACE" get rules.monitoring.googleapis.com -o yaml
```

Or surface firing alerts in the Google Cloud Console under
**Monitoring → Alerting** if you have GCP IAM for the project.

Next: [03 — Scenario 1: Chat](03-chat.md)
