# 0 — Overview

## What is vLLM, and why does this need to be a stack?

A single vLLM process is already a serious piece of engineering. It uses
**PagedAttention** to manage the KV cache in fixed-size blocks the same way
an OS pages physical memory — which means it can hold many concurrent
conversations in GPU memory without fragmenting it, and it can serve dozens
of requests per replica without falling over. It exposes an
OpenAI-compatible API out of the box, so any client that already talks to
OpenAI can swap the base URL and keep going.

What vLLM does *not* do on its own:

- **Route across replicas.** One vLLM process is one GPU. To use more, you
  need something in front of it that knows which replica to send a given
  request to — ideally one that's aware of prefix-cache state, so chat
  workloads land on the replica that's already warm.
- **Scale up and down.** vLLM has no opinion about replica count. Something
  outside has to watch the queue and add or remove pods.
- **Tell you what's going on.** vLLM exposes Prometheus metrics, but
  somebody has to scrape and visualise them.

## The Kubernetes deployment landscape

| Project | What it is | When to reach for it |
|---|---|---|
| **vLLM Production Stack** | The vLLM project's own reference deployment — Helm chart bundling engine + router + observability + KEDA hooks. | You want vLLM-on-Kubernetes done well, with one chart and sensible defaults. **This is what we're using today.** |
| **llm-d** | A full platform for disaggregated, large-scale inference. Uses Gateway API Inference Extension, LeaderWorkerSet for multi-node models, prefill/decode split. CNCF Sandbox. | You're running production-scale, multi-node, latency-critical inference and the Helm chart is no longer enough. |
| **KubeAI** | An "inference operator" — declares models as CRs, manages backend lifecycles. | You want a higher-level abstraction across multiple model engines (vLLM, llama.cpp, …). |

## Production Stack architecture (the parts we'll see)

```
            ┌──────────────────────┐
            │  vllm-router-service │   OpenAI-compatible API
            │  (routing logic)     │   prefixaware in our config
            └──────────┬───────────┘
                       │
            ┌──────────┼──────────┐
            ▼          ▼          ▼
       ┌────────┐  ┌────────┐  ┌────────┐
       │ vLLM-0 │  │ vLLM-1 │  │  ...   │   Deployment of engine replicas,
       │  GPU   │  │  GPU   │  │        │   one GPU each, scaled by KEDA
       └────┬───┘  └────┬───┘  └────────┘
            │           │
            ▼           ▼
        ┌────────────────────┐
        │  Prometheus        │   scrapes /metrics from every replica
        │  Grafana           │   the workshop dashboard reads from here
        │  KEDA (queue → HPA)│   makes the replica count follow load
        └────────────────────┘
```

Three things to keep in mind as we go:

1. **The router is the only thing your application talks to.** It's a
   single OpenAI-compatible endpoint. Scaling the engine doesn't change the
   API surface.
2. **The router's routing logic matters.** `roundrobin` is fine for
   throughput; `prefixaware` and `kvaware` are what turn a chat workload
   from "every request pays the prefill cost" into "every replica becomes
   warm for the prompts it sees most".
3. **KEDA is just an HPA in disguise** — it reads a Prometheus query and
   adjusts the deployment's replica count. The interesting question is
   *which metric*. We'll use `vllm:num_requests_waiting` (queue depth);
   alternatives include KV-cache utilisation.

Next: [01 — Deploy the stack](01-deploy.md)
