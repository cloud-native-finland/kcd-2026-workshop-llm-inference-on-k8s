# 3 — Scenario 1: Conversational chat

## What we're doing

Three "conversations" running in parallel, each with the **same long system
prompt** and growing user/assistant history. We run multiple rounds.

## Why it matters

A real chat product looks exactly like this: a system prompt that doesn't
change, plus a tail of user turns. If your router blindly load-balances,
every request has to re-process the system prompt from scratch on whichever
replica it lands on. With **prefix-aware routing** the router notices the
shared prefix and pins matching requests to the same replica, where vLLM's
prefix caching keeps the prefix's KV state warm — so the second request in
a conversation skips most of the prefill cost.

Our router is configured with `routingLogic: prefixaware`, so this should
just work.

## Run it

Install the load deps once (in a venv so they don't leak into your system python):

```bash
python3 -m venv load/.venv
load/.venv/bin/pip install -r load/requirements.txt
```

Then:

```bash
load/.venv/bin/python load/scenario1_chat.py --rounds 3
```

## What to watch in Grafana

Open the vLLM dashboard and the **Prefix cache** panels (search the
dashboard for "prefix"). Specifically:

- `vllm:prefix_cache_queries_total` should climb — every request is asking
  about cache state.
- `vllm:prefix_cache_hits_total` should climb in lockstep on the second
  round onward. Their ratio is your cache hit rate.
- **TTFT** should be high for the first turn of each conversation (cold
  prefix) and noticeably lower for follow-up turns.

## Try this

Re-run with `--rounds 1` after a fresh start — what do you expect TTFT to
look like? Re-run with `--rounds 5`; do hit rate and TTFT keep improving,
or do they plateau?

Edit `scenario1_chat.py` and shorten `SYSTEM_PROMPT` to a single sentence.
Re-run. The prefix is now too small to matter — does the cache panel
flatten out? This is a good intuition for *when* prefix caching pays.

Next: [04 — Scenario 2: Batch](04-batch.md)
