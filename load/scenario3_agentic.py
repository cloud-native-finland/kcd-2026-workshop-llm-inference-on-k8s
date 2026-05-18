"""Scenario 3 — Agentic / tool-calling pattern.

Pedagogical goal: lots of *short, fast-turn* sequential requests, the way a
real agent loop hammers an LLM (reason → tool → observe → repeat). Each
"agent" runs N steps back-to-back; we run several agents in parallel so the
router has to multiplex them. Different from Scenario 2 in that requests
are short, latency-sensitive, and the load is sustained rather than burst.

Watch in Grafana:
  - request rate (req/s)                  high and steady
  - vllm:num_requests_running             stays ~ concurrency
  - vllm:num_requests_waiting             low under healthy capacity
  - p95 latency                           the metric attendees should care about most
"""

from __future__ import annotations

import asyncio
import random

import httpx

from common import Stats, build_arg_parser, chat

AGENT_SYSTEM = (
    "You are an agent that produces short JSON responses. Always reply with "
    'a JSON object of the form {"thought": "...", "next_tool": "..."} '
    "and nothing else."
)

TASKS = [
    "Find the largest pod by memory in the cluster.",
    "Check whether the deployment 'vllm' has any pending pods.",
    "List the prometheus targets that are currently down.",
    "Identify the node with the highest GPU utilisation.",
    "Look up the most recent CrashLoopBackOff event.",
]

TOOL_OBSERVATIONS = [
    "Tool returned: 3 pods, top one is vllm-router-7df at 412Mi.",
    "Tool returned: 0 pending pods.",
    "Tool returned: targets up: 14, down: 0.",
    "Tool returned: gke-gpu-pool-xyz at 78% utilisation.",
    "Tool returned: no CrashLoopBackOff events in last 1h.",
]


async def run_agent(
    client: httpx.AsyncClient,
    base: str,
    model: str,
    agent_id: int,
    steps: int,
    stats: Stats,
) -> None:
    task = random.choice(TASKS)
    history: list[dict] = [
        {"role": "system", "content": AGENT_SYSTEM},
        {"role": "user", "content": f"Task: {task}"},
    ]
    for step in range(steps):
        try:
            latency, tokens = await chat(client, base, model, history, max_tokens=48, temperature=0.0)
        except Exception as exc:
            stats.fail()
            print(f"  ! agent {agent_id} step {step}: {exc}")
            return
        stats.record(latency, tokens)
        # Feed a synthetic tool observation forward — the agent stays "in
        # character" without us needing real tool execution.
        history.append({"role": "assistant", "content": "(model reply elided)"})
        history.append({"role": "user", "content": random.choice(TOOL_OBSERVATIONS)})


async def main() -> None:
    parser = build_arg_parser(__doc__.splitlines()[0])
    parser.add_argument("--agents", type=int, default=10, help="Parallel agent loops")
    parser.add_argument("--steps", type=int, default=15, help="Steps per agent")
    args = parser.parse_args()

    stats = Stats()
    limits = httpx.Limits(max_connections=args.agents * 2)
    async with httpx.AsyncClient(limits=limits) as client:
        async def progress() -> None:
            while True:
                await asyncio.sleep(5)
                print(f"  … {stats.summary()}")

        prog_task = asyncio.create_task(progress())
        try:
            print(f"Running {args.agents} agents × {args.steps} steps each")
            await asyncio.gather(
                *(
                    run_agent(client, args.base, args.model, i, args.steps, stats)
                    for i in range(args.agents)
                )
            )
        finally:
            prog_task.cancel()
    print("\n" + stats.summary())


if __name__ == "__main__":
    asyncio.run(main())
