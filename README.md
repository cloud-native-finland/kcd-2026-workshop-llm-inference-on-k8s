# Running LLM Inference in Kubernetes

A hands-on, 2-hour workshop. Your group gets a namespace on a pre-provisioned
GKE cluster. You deploy the [vLLM Production
Stack](https://github.com/vllm-project/production-stack) into your namespace,
put it under three realistic loads — conversational, batch, and agentic —
and watch the system through Prometheus + Grafana. By the end you'll know
how to read a vLLM-on-Kubernetes setup the way an operator does.

## Before the workshop

You need on your laptop:

- `kubectl` and `helm` 3.x
- `python` 3.10+
- `jq` and `curl`
- A kubeconfig pointing at the workshop cluster (handed out at the start)
- Your assigned group namespace (e.g. `group-alpha`) — also handed out

The cluster already has GPU nodes, the NVIDIA driver, KEDA, and a shared
kube-prometheus-stack. You do not need a GCP account.

## Run order

```bash
export MY_NAMESPACE=group-XX     # what you were assigned
```

| Step | What | Command |
|---|---|---|
| 1 | Read the overview | [docs/00-overview.md](docs/00-overview.md) |
| 2 | Check your laptop has what you need | `./scripts/00-check-prereqs.sh` |
| 3 | Deploy your vLLM into your namespace | `./scripts/01-deploy.sh` |
| 4 | Open port-forwards (leave running) | `./scripts/02-port-forward.sh` |
| 5 | Smoke-test the endpoint | `./scripts/03-smoke-test.sh` |
| 6 | Tour the Grafana dashboard | [docs/02-observability.md](docs/02-observability.md) |
| 7 | Scenario 1 — chat / prefix-cache | [docs/03-chat.md](docs/03-chat.md) |
| 8 | Scenario 2 — batch burst / KEDA | [docs/04-batch.md](docs/04-batch.md) |
| 9 | Scenario 3 — agentic / queue depth | [docs/05-agentic.md](docs/05-agentic.md) |
| 10 | Where the ecosystem is going | [docs/06-whats-next.md](docs/06-whats-next.md) |
| 11 | Teardown your deployment | `./scripts/99-teardown.sh` |

## What gets deployed into your namespace

- **vLLM serving engine** running `Qwen/Qwen2.5-0.5B-Instruct` — small enough
  to load in seconds, so we spend our time on the *system*, not on weights.
- **Router** with prefix-aware routing — Scenario 1 actually exercises it.
- **KEDA ScaledObject** scaling on `vllm:num_requests_waiting` (queue depth).
- **PrometheusRule** with two alerts (`vLLMQueueDeep`, `vLLMEngineDown`) —
  auto-tenant-scoped to your namespace by the Prometheus operator.
- **PodDisruptionBudget** keeping at least one engine pod available across
  voluntary disruptions.
- **Grafana dashboard ConfigMaps** (chart-bundled) — the cluster's Grafana
  sidecar imports them on the fly.

The Grafana, Prometheus, and Alertmanager you use are **cluster-wide** —
every group sees the same Grafana, with their own dashboards and alerts
visible alongside everyone else's.

## Layout

```
docs/         workshop content, read in order
helm/         the values file and KEDA ScaledObject you install
scripts/      everything you run from the terminal
load/         the three load-test scripts
grafana/      a note on the bundled dashboards
```

## Further reading

- [vLLM Production Stack](https://github.com/vllm-project/production-stack)
- [llm-d](https://llm-d.ai/)
- [KubeAI](https://github.com/kubeai-project/kubeai)
- [Gateway API Inference Extension](https://github.com/kubernetes-sigs/gateway-api-inference-extension)
