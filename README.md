# RunCost

> **Run a 1,000-agent simulation for $2 instead of $200.**
> Drop-in cost intelligence for Python AI agent frameworks.

[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![PyPI version](https://img.shields.io/pypi/v/runcost)](https://pypi.org/project/runcost/)
[![GitHub Stars](https://img.shields.io/github/stars/Picasso976/runcostai?style=social)](https://github.com/Picasso976/runcostai)

---

## The Problem

You are building with CrewAI, LangGraph, AutoGen, MiroFish, or the OpenAI Agents SDK. The framework is powerful. The demos are impressive.

Then you run it at scale and see the bill.

A 500-agent simulation costs **$40-$80 per run**. A recursive loop that nobody catches costs **$200 before you notice**. An overnight batch job costs **$600 by morning**.

None of these frameworks warn you. None of them stop it. You find out when you get an email from your API provider.

**Every major agent framework has the same blind spot: zero native cost controls.**

RunCost is that missing layer.

---

## The Fix: One Line

```python
# Before RunCost
from openai import OpenAI
client = OpenAI()

# After RunCost -- nothing else changes
from runcost import OpenAI
client = OpenAI()
```

Drop it in. That is it. Your existing code works exactly as before -- except now every API call is intercepted, measured, and intelligently routed before it costs you money.

Works with any OpenAI-compatible framework: CrewAI, LangGraph, AutoGen, MiroFish, LangChain.

---

## What Happens When You Run It

```
RunCost  //  Live Agent Cost Monitor          cost.run
------------------------------------------------------
  OK  researcher_01  ->  llama-3-8b   $0.001    11ms
  OK  analyst_04     ->  gpt-4o       $0.047   780ms
  OK  writer_02      ->  mistral-7b   $0.002    43ms
  XX  crawler_07     ->  BLOCKED      $0.000  loop@13
  OK  researcher_14  ->  llama-3-8b   $0.001     9ms
------------------------------------------------------
  Spent:    $1.82 / $5.00   [====      ]  36%
  Saved:   $41.30            Efficiency: 95.7%
  Blocked:  3 loops          Calls:       847
------------------------------------------------------
```

**RunCost intercepts every LLM call and:**

- Estimates the cost before spending a dollar
- Routes simple tasks to cheap models (Groq, Llama 3, Mistral) automatically
- Routes reasoning-heavy tasks to GPT-4o or Claude only when needed
- Detects recursive loops and kills them before they drain your account
- Enforces hard spending limits -- when you hit your cap, everything stops
- Logs every call to a local SQLite database
- Shows a live terminal dashboard of spend vs. savings in real time

---

## The Numbers

> Same simulation. Same output quality. 10x cheaper.

| Workload | Without RunCost | With RunCost | Saved |
|---|---|---|---|
| 1,000-agent simulation (GPT-4o) | ~$180-$200 | **~$2-$4** | ~98% |
| 500-agent CrewAI workflow | ~$40-$80 | **~$4-$8** | ~90% |
| AutoGen research pipeline | ~$15-$20 | **~$1-$2** | ~90% |
| Recursive loop (caught) | $200+ | **$0.00** | 100% |

> Savings vary based on task complexity and model mix. RunCost routes simple tasks to Groq/Llama-3 (~$0.001/call) and reserves GPT-4o for reasoning-heavy steps only.

---

## Install

```bash
pip install runcost
```

**Supported frameworks:** OpenAI SDK - CrewAI - LangGraph - AutoGen - LangChain - MiroFish - any OpenAI-compatible client

---

## Quick Start

```python
from runcost import OpenAI, BudgetConfig

config = BudgetConfig(
    hard_limit_usd=5.00,     # Hard stop -- never exceed this per run
    warn_at_usd=2.00,        # Alert when approaching limit
    auto_route=True,          # Auto-route cheap tasks to Llama/Groq
    block_loops=True,         # Kill recursive agent loops instantly
    log_to_db=True            # Save full history to runcost.db
)

client = OpenAI(budget=config)

# Use exactly as normal -- RunCost works silently underneath
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": "Analyze these 500 documents"}]
)
```

---

## How Routing Works

RunCost classifies each call by complexity before sending it:

| Complexity | Model Used | Typical Cost |
|---|---|---|
| Simple: formatting, lookup, summarization | Groq Llama-3 8B | ~$0.001 |
| Medium: research, extraction, classification | Mistral 7B | ~$0.002 |
| Complex: reasoning, code, multi-step logic | GPT-4o / Claude | ~$0.04-0.09 |
| Detected loop / budget exceeded | BLOCKED | $0.000 |

You can override routing per agent, per task type, or per model preference.

---

## The Dashboard

```bash
runcost dashboard
```

Opens a live terminal view showing real-time spend, savings, active agents, blocked loops, and full call history. Dark mode. No browser required.

A web dashboard is coming in v0.3.

---

## Why Open Source?

Because every developer deserves to see exactly what their agents are spending -- before it is too late.

The core engine is **AGPL-3.0**. Run it yourself, audit it, fork it, build on it.

**RunCost Pro** (coming soon): team dashboards - multi-project tracking - SSO - compliance exports - Slack/Discord alerts - SLA support

---

## Roadmap

| Status | Feature |
|--------|---------|
| ✅ | OpenAI SDK wrapper |
| ✅ | Groq / Llama-3 auto-routing |
| ✅ | Recursive loop detection |
| ✅ | Hard budget limits |
| ✅ | SQLite call logging |
| ✅ | Live terminal dashboard |
| 🔜 | Web dashboard (v0.3) |
| 🔜 | CrewAI native plugin |
| 🔜 | LangGraph native plugin |
| 🔜 | MiroFish native plugin |
| 🔜 | Pre-flight cost estimator |
| 🔜 | Slack / Discord spend alerts |
| 🔜 | Team spend analytics |
| 🔜 | AgentLedger plugin -- audit trail for every agent action |

---

## Why I built this?

Multi-agent AI frameworks are powerful. But none of them ship with cost controls. RunCost is the layer that should have existed from day one -- built in public, open source, free to use.

---

## License

**AGPL-3.0** -- free for individuals and open source projects.

Commercial license available for enterprise deployments.

---
