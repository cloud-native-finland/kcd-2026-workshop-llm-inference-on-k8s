"""Scenario 2 — Batch document summarization burst.

Pedagogical goal: 50+ requests dumped on the router at once should pile up
in the vLLM queue, push vllm:num_requests_waiting above the KEDA threshold
of 5, and trigger a scale-out from 1 → 2 replicas (assuming spare GPU
capacity). On a single-GPU test cluster the second replica will stay
Pending — that is itself a useful teaching moment.

Watch in Grafana:
  - vllm:num_requests_waiting          (spikes, then drains)
  - kube_deployment_status_replicas    (1 → 2)
  - keda_scaler_active                 (1 while burst is hot)
  - throughput (tokens/s) per replica  (drops per-replica as load shares)
"""

from __future__ import annotations

import asyncio

import httpx

from common import Stats, build_arg_parser, chat

# A pile of mock "documents" to summarise. Keep them short-ish so the run
# completes in a few minutes on a 0.5B model.
DOCUMENT = (
    "An incident occurred at 14:32 UTC affecting the inference cluster in "
    "us-central1. The first symptom was a sustained increase in p95 TTFT "
    "across all model replicas, climbing from 180ms to over 4 seconds within "
    "two minutes. Investigation revealed that the request queue depth had "
    "grown to 240 while only one of three replicas was Ready. The second "
    "replica was stuck in CrashLoopBackOff because of an OOMKilled event "
    "during model load; the third was Pending because the GPU node pool had "
    "been scaled down by a manual operator action three hours earlier. The "
    "on-call engineer restored the node pool to its baseline size, the two "
    "remaining replicas became Ready within four minutes, queue depth "
    "dropped, and p95 TTFT recovered to baseline by 14:51 UTC. Action items "
    "include adding a guardrail to prevent operator-initiated scale-downs "
    "below a configured floor, alerting on Pending replicas, and reviewing "
    "the resource requests of the model serving container."
)


async def summarise(client: httpx.AsyncClient, base: str, model: str, idx: int, stats: Stats) -> None:
    messages = [
        {"role": "system", "content": "You summarise incident reports in one terse sentence."},
        {"role": "user", "content": f"Document {idx}:\n{DOCUMENT}\n\nSummary:"},
    ]
    try:
        latency, tokens = await chat(client, base, model, messages, max_tokens=64, temperature=0.0)
    except Exception as exc:
        stats.fail()
        print(f"  ! req {idx}: {exc}")
        return
    stats.record(latency, tokens)


async def main() -> None:
    parser = build_arg_parser(__doc__.splitlines()[0])
    parser.add_argument("--count", type=int, default=60, help="How many docs to summarise")
    parser.add_argument("--concurrency", type=int, default=20, help="Max in-flight requests")
    args = parser.parse_args()

    sem = asyncio.Semaphore(args.concurrency)
    stats = Stats()

    async def bounded(idx: int, client: httpx.AsyncClient) -> None:
        async with sem:
            await summarise(client, args.base, args.model, idx, stats)

    limits = httpx.Limits(max_connections=args.concurrency * 2)
    async with httpx.AsyncClient(limits=limits) as client:
        # Periodic progress printer so attendees see the burst in real time.
        async def progress() -> None:
            while True:
                await asyncio.sleep(5)
                print(f"  … {stats.summary()}")

        prog_task = asyncio.create_task(progress())
        try:
            print(f"Submitting {args.count} requests, concurrency={args.concurrency}")
            await asyncio.gather(*(bounded(i, client) for i in range(args.count)))
        finally:
            prog_task.cancel()
    print("\n" + stats.summary())


if __name__ == "__main__":
    asyncio.run(main())
