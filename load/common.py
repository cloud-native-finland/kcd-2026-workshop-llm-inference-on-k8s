"""Shared helpers for the three workshop scenarios.

All three call the router's OpenAI-compatible API. The router is reached via
the port-forward set up by scripts/02-port-forward.sh (localhost:30080).
"""

from __future__ import annotations

import argparse
import os
import time
from dataclasses import dataclass, field

import httpx

DEFAULT_BASE = os.environ.get("VLLM_BASE", "http://localhost:30080")
DEFAULT_MODEL = os.environ.get("VLLM_MODEL", "Qwen/Qwen3-0.6B")


@dataclass
class Stats:
    """Aggregate latency / throughput stats across a run."""

    started_at: float = field(default_factory=time.monotonic)
    requests: int = 0
    errors: int = 0
    total_latency: float = 0.0
    total_output_tokens: int = 0
    latencies: list[float] = field(default_factory=list)

    def record(self, latency: float, output_tokens: int) -> None:
        self.requests += 1
        self.total_latency += latency
        self.total_output_tokens += output_tokens
        self.latencies.append(latency)

    def fail(self) -> None:
        self.errors += 1

    def summary(self) -> str:
        elapsed = max(time.monotonic() - self.started_at, 1e-6)
        if not self.latencies:
            return f"{self.requests} requests, {self.errors} errors, {elapsed:.1f}s elapsed"
        sorted_lat = sorted(self.latencies)
        p50 = sorted_lat[len(sorted_lat) // 2]
        p95 = sorted_lat[min(len(sorted_lat) - 1, int(0.95 * len(sorted_lat)))]
        return (
            f"{self.requests} requests in {elapsed:.1f}s "
            f"({self.requests / elapsed:.1f} req/s, "
            f"{self.total_output_tokens / elapsed:.0f} tok/s)  "
            f"p50={p50 * 1000:.0f}ms p95={p95 * 1000:.0f}ms "
            f"errors={self.errors}"
        )


def build_arg_parser(description: str) -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=description)
    p.add_argument("--base", default=DEFAULT_BASE, help="vLLM router base URL")
    p.add_argument("--model", default=DEFAULT_MODEL, help="Model ID served by vLLM")
    return p


async def chat(
    client: httpx.AsyncClient,
    base: str,
    model: str,
    messages: list[dict],
    max_tokens: int = 64,
    temperature: float = 0.7,
) -> tuple[float, int]:
    """Send one chat request. Returns (latency_seconds, output_tokens)."""
    start = time.monotonic()
    r = await client.post(
        f"{base}/v1/chat/completions",
        json={
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        },
        timeout=120.0,
    )
    r.raise_for_status()
    data = r.json()
    latency = time.monotonic() - start
    usage = data.get("usage") or {}
    return latency, int(usage.get("completion_tokens", 0))
