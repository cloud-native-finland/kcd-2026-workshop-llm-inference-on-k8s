# 5 — Scenario 3: Agentic / tool-calling

## What we're doing

10 parallel "agents", each running 15 short sequential turns. Each turn is
a small completion (think: "decide which tool to call, given this latest
observation"). Unlike Scenario 2, the work is *sustained* rather than
bursty, and individual requests are *short*.

## Why it matters

This is the shape of modern agent traffic. A user fires off one prompt and
the agent runs dozens of short LLM calls under the hood. The things that
make this workload painful are:

- **Latency dominates user experience.** A 200ms vs 800ms median turn is
  the difference between an agent that feels alive and one that feels
  broken.
- **Concurrency stays high.** You don't get the queue-drain moments
  Scenario 2 gave you. Capacity has to keep up *continuously*.
- **Per-request work is small.** Prefix caching helps if the agent reuses
  any context (it usually does); batching helps because vLLM can pack many
  short decode steps into a single GPU step.

## Run it

```bash
load/.venv/bin/python load/scenario3_agentic.py --agents 10 --steps 15
```

## What to watch in Grafana

- `vllm:num_requests_running` should stabilise near your concurrency
  number (10) once the loop is warm.
- `vllm:num_requests_waiting` should stay **low** if you have enough
  capacity. If it sits non-zero, you are over-subscribed.
- p95 TTFT and p95 total latency tell you whether the agents are getting
  acceptable response times. The terminal output prints the same numbers.

## Try this

Crank concurrency to 30 (`--agents 30`). At some point a single 0.6B
replica on one time-shared GPU slot runs out of decode budget and waiting requests start
to pile up. Where is that point on *your* cluster? That's your effective
capacity for this workload shape.

Compare the Grafana request-rate panel between this scenario and
Scenario 2. Both push the engine, but the shapes are completely different
— one is a square wave, the other is a steady plateau. The same engine and
the same metrics tell the operator two very different stories.

Next: [06 — What's next](06-whats-next.md)
