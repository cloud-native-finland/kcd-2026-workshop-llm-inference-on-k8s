# 4 — Scenario 2: Batch processing burst

## What we're doing

Slam the router with ~60 summarization requests over a short window. They
arrive faster than one replica can drain them, so they stack up in the vLLM
queue. KEDA notices and scales the deployment from 1 → 2.

## Why it matters

Batch / offline workloads are bursty. Provisioning for peak wastes GPUs at
idle; provisioning for average means burst jobs queue forever. Autoscaling
on *queue depth* (rather than CPU or RPS) directly tracks the thing that
actually matters for LLM inference: are requests waiting?

Our `ScaledObject` says: when `vllm:num_requests_waiting > 5`, scale up.
Max replicas is 2 (workshop default).

## Before you run

Open a second terminal and watch the autoscaler do its thing:

```bash
kubectl -n $MY_NAMESPACE get hpa -w
```

You'll see the KEDA-managed HPA: `keda-hpa-vllm-qwen3`. The `TARGETS`
column shows current queue depth / threshold.

In another pane, watch the pods:

```bash
kubectl -n $MY_NAMESPACE get pods -w
```

## Run it

```bash
load/.venv/bin/python load/scenario2_batch.py --count 60 --concurrency 20
```

> **A note on workshop sizing.** Qwen3-0.6B on an L4 is *fast* — at the
> defaults above the burst can drain in 2-3 seconds and queue depth may
> never cross the KEDA threshold. If you don't see the autoscaler kick in,
> bump `--count 200 --concurrency 40` (or even higher) until the engine
> actually backs up. The point of the scenario is the *shape* of the
> behavior, not the specific numbers.

The script prints progress every 5s.

## What you should see

1. Queue depth climbs above 5 → HPA flips, deployment scales from 1 to 2.
2. **If your cluster has spare GPUs**, the second replica becomes Ready
   within a couple of minutes. Throughput approximately doubles, queue
   drains, latencies recover.
3. **If the cluster's GPU is already busy** (other groups also running
   Scenario 2 simultaneously), your second replica may stay `Pending` with
   `FailedScheduling: 0/N nodes are available: 1 Insufficient
   nvidia.com/gpu`. This is real — and informative: KEDA can ask for more
   capacity, but it can't manifest GPUs out of thin air. In a production
   cluster you'd pair this with **cluster autoscaling** that adds GPU
   nodes when pods stay Pending.

## And the alert

The `VLLMQueueDeep` alert you applied during deploy fires on the same
`vllm:num_requests_waiting > 5` signal that KEDA scales on, with the
same 1-minute window. So during the burst you should see, in order:

1. KEDA's HPA flip and request a second replica.
2. The rule's state move from `Pending` → `Firing` (visible via
   `kubectl -n $MY_NAMESPACE get rules.monitoring.googleapis.com vllm-qwen3-rules -o yaml`,
   in the per-rule `state` and `firingAlerts` fields).
3. *Either* the queue drains (second replica got a time-shared GPU slot)
   and the alert clears, *or* the second replica is stuck Pending and
   the alert stays firing — telling you the workload exceeds available
   capacity.

That sequence is the whole story of "metric-driven autoscaling has a
ceiling, and your alerts should know about it."

## Try this

Open Grafana → vLLM dashboard. Compare what the per-replica throughput
graph looked like during the burst vs. now (idle). You should see a clear
ramp + plateau + drain shape.

Re-run with `--count 200` and a higher concurrency. Does the queue stay
high for longer? Does the HPA's "scaling event" history show repeated
considerations?

```bash
kubectl -n $MY_NAMESPACE describe hpa keda-hpa-vllm-qwen3 | tail -30
```

Next: [05 — Scenario 3: Agentic](05-agentic.md)
