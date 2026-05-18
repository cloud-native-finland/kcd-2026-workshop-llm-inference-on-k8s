"""Scenario 1 — Conversational / multi-turn chat with shared system prompts.

Pedagogical goal: show prefix-cache reuse climbing in Grafana.

Each "conversation" carries the SAME long system prompt and grows by one
user/assistant turn each request. Because the chart's router is configured
with routingLogic=prefixaware, requests sharing a prefix get pinned to the
same replica, and after the first turn the system prompt sits warm in the
KV cache. Watch:

  - vllm:gpu_cache_usage_perc        (climbs and stabilizes)
  - vllm:prefix_cache_hit_rate / queries_total vs hits_total
  - TTFT distribution                 (drops after first turn per conversation)
"""

from __future__ import annotations

import asyncio

import httpx

from common import Stats, build_arg_parser, chat

# A deliberately long system prompt so prefix caching has something meaningful
# to reuse. ~200 tokens.
SYSTEM_PROMPT = (
    "You are a careful technical assistant for an SRE team. Always answer "
    "in two short paragraphs. The first paragraph states the conclusion in "
    "one sentence. The second paragraph lists at most three bullet points "
    "of supporting reasoning. Never invent commands; if you do not know, "
    "say so. Prefer Linux/Kubernetes terminology. Assume the reader is a "
    "competent engineer who needs precision more than friendliness. "
    "Do not greet, apologize, or summarize at the end. Begin immediately "
    "with the conclusion sentence."
)

# Each conversation is a separate "user" and grows over multiple turns.
CONVERSATIONS = [
    [
        "Why does my Pod stay in Pending with FailedScheduling?",
        "How do I check which node has free GPU capacity?",
        "What event would the scheduler emit if no node tolerates the GPU taint?",
        "Show me the kubectl command to inspect node taints.",
    ],
    [
        "What does TTFT mean in LLM serving?",
        "How does PagedAttention affect TTFT under load?",
        "Which Prometheus metric tracks TTFT in vLLM?",
        "Is high TTFT usually a queueing problem or a compute problem?",
    ],
    [
        "Explain prefix caching in one paragraph.",
        "When is prefix caching most valuable for a chat workload?",
        "What kind of routing strategy maximises prefix-cache hits?",
        "What metric tells me prefix-cache reuse is actually happening?",
    ],
]


async def run_conversation(
    client: httpx.AsyncClient,
    base: str,
    model: str,
    turns: list[str],
    stats: Stats,
) -> None:
    """Walk one conversation turn-by-turn, carrying history forward."""
    history: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    for user_msg in turns:
        history.append({"role": "user", "content": user_msg})
        try:
            latency, tokens = await chat(client, base, model, history, max_tokens=96)
        except Exception as exc:
            stats.fail()
            print(f"  ! error: {exc}")
            continue
        stats.record(latency, tokens)
        # Synthetic assistant reply for the next turn — we don't need the real
        # content, we just need the history to keep growing so the prefix
        # stays long.
        history.append({"role": "assistant", "content": "(reply elided)"})
        print(f"  turn done in {latency*1000:.0f}ms, {tokens} tokens out")


async def main() -> None:
    parser = build_arg_parser(__doc__.splitlines()[0])
    parser.add_argument("--rounds", type=int, default=3, help="Repeat the full set N times")
    args = parser.parse_args()

    stats = Stats()
    async with httpx.AsyncClient() as client:
        for r in range(args.rounds):
            print(f"\n=== round {r + 1}/{args.rounds} ===")
            # Run conversations in parallel so the router sees real concurrency.
            await asyncio.gather(
                *(
                    run_conversation(client, args.base, args.model, conv, stats)
                    for conv in CONVERSATIONS
                )
            )
    print("\n" + stats.summary())


if __name__ == "__main__":
    asyncio.run(main())
