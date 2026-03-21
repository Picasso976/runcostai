"""
RunCost Demo Script
Simulates a multi-agent research pipeline and writes to runcost.db
Run this to see the dashboard with realistic data.

Usage: py demo.py
Then:  runcost dashboard
"""

import sqlite3
import random
import time
from datetime import datetime, timezone, timedelta

DB_PATH = "runcost.db"

# Simulated agents and their typical models
AGENTS = [
    ("researcher_01", "llama3-8b-8192",          0.00000005, 0.00000008),
    ("researcher_02", "llama3-8b-8192",          0.00000005, 0.00000008),
    ("researcher_03", "llama3-8b-8192",          0.00000005, 0.00000008),
    ("analyst_01",    "gpt-4o",                  0.0000025,  0.000010),
    ("analyst_02",    "gpt-4o",                  0.0000025,  0.000010),
    ("critic_01",     "mixtral-8x7b-32768",      0.00000024, 0.00000024),
    ("writer_01",     "mixtral-8x7b-32768",      0.00000024, 0.00000024),
    ("summarizer_01", "llama3-8b-8192",          0.00000005, 0.00000008),
    ("coordinator",   "gpt-4o",                  0.0000025,  0.000010),
    ("crawler_01",    "llama3-8b-8192",          0.00000005, 0.00000008),
]

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS calls (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            ts                TEXT NOT NULL,
            model             TEXT NOT NULL,
            prompt_tokens     INTEGER NOT NULL,
            completion_tokens INTEGER NOT NULL,
            cost_usd          REAL NOT NULL,
            blocked           INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    return conn

def simulate_call(conn, agent_name, model, in_rate, out_rate, hours_ago=0, blocked=False):
    prompt_tokens = random.randint(200, 3000)
    completion_tokens = random.randint(50, 800) if not blocked else 0
    cost = prompt_tokens * in_rate + completion_tokens * out_rate

    ts = (datetime.now(timezone.utc) - timedelta(hours=hours_ago)).isoformat()

    conn.execute("""
        INSERT INTO calls (ts, model, prompt_tokens, completion_tokens, cost_usd, blocked)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (ts, model, prompt_tokens, completion_tokens, round(cost, 8), int(blocked)))

    return cost, model, prompt_tokens, completion_tokens

def run_demo():
    print("\n  RunCost Demo")
    print("  ─────────────────────────────────────")
    print("  Simulating a 500-agent research pipeline...")
    print()

    try:
        from rich.console import Console
        from rich.text import Text
        console = Console()
        use_rich = True
    except ImportError:
        use_rich = False

    conn = init_db()
    total_cost = 0.0
    total_calls = 0
    blocked_count = 0

    # Simulate calls over last 6 hours
    print("  Phase 1: Historical data (last 6 hours)...")
    for hour in range(6, 0, -1):
        calls_this_hour = random.randint(40, 120)
        for _ in range(calls_this_hour):
            agent_name, model, in_rate, out_rate = random.choice(AGENTS)
            cost, model, pt, ct = simulate_call(
                conn, agent_name, model, in_rate, out_rate,
                hours_ago=hour + random.random()
            )
            total_cost += cost
            total_calls += 1
    conn.commit()
    print(f"  ✓ {total_calls} historical calls written")

    # Simulate a loop that gets blocked
    print("\n  Phase 2: Simulating blocked loops...")
    crawler_in = 0.00000005
    crawler_out = 0.00000008
    for i in range(5):
        simulate_call(conn, "crawler_01", "llama3-8b-8192",
                     crawler_in, crawler_out, hours_ago=0.1, blocked=True)
        blocked_count += 1
    conn.commit()
    print(f"  ✓ {blocked_count} loops blocked ($0.000 wasted)")

    # Simulate recent live calls
    print("\n  Phase 3: Recent calls (last few minutes)...")
    recent_agents = [
        ("researcher_01", "llama3-8b-8192",     0.00000005, 0.00000008),
        ("analyst_01",    "gpt-4o",             0.0000025,  0.000010),
        ("critic_01",     "mixtral-8x7b-32768", 0.00000024, 0.00000024),
        ("writer_01",     "mixtral-8x7b-32768", 0.00000024, 0.00000024),
        ("researcher_02", "llama3-8b-8192",     0.00000005, 0.00000008),
        ("coordinator",   "gpt-4o",             0.0000025,  0.000010),
        ("summarizer_01", "llama3-8b-8192",     0.00000005, 0.00000008),
        ("analyst_02",    "gpt-4o",             0.0000025,  0.000010),
    ]

    for i, (agent_name, model, in_rate, out_rate) in enumerate(recent_agents):
        cost, model, pt, ct = simulate_call(
            conn, agent_name, model, in_rate, out_rate,
            hours_ago=random.uniform(0, 0.05)
        )
        total_cost += cost
        total_calls += 1

        if use_rich:
            text = Text()
            text.append("  RunCost ", style="bold green")
            text.append(f"{model:<28}", style="cyan")
            text.append(f"  ${cost:.5f}", style="yellow")
            text.append(f"  [session: ${total_cost:.5f}]", style="dim")
            console.print(text)
        else:
            print(f"  RunCost  {model:<28}  ${cost:.5f}  [session: ${total_cost:.5f}]")

        time.sleep(0.1)

    conn.commit()
    conn.close()

    print()
    print("  ─────────────────────────────────────")
    print(f"  Total calls:    {total_calls + blocked_count}")
    print(f"  Total spend:    ${total_cost:.4f}")
    print(f"  Loops blocked:  {blocked_count}")
    print()
    print("  Now run: runcost dashboard")
    print("  Or:      runcost dashboard --live")
    print()

if __name__ == "__main__":
    run_demo()
