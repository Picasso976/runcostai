from __future__ import annotations

import os
import sqlite3

import click
from rich.console import Console
from rich.table import Table


@click.group()
def main() -> None:
    pass


@main.command()
@click.option("--db", "db_path", default="runcost.db", show_default=True, help="Path to runcost SQLite db.")
def summary(db_path: str) -> None:
    console = Console()
    if not os.path.exists(db_path):
        console.print(f"[red]No database found at[/red] {db_path}")
        raise SystemExit(1)

    conn = sqlite3.connect(db_path)
    try:
        total_spend = float(conn.execute("SELECT COALESCE(SUM(cost_usd), 0.0) FROM calls").fetchone()[0])
        total_calls = int(conn.execute("SELECT COUNT(*) FROM calls").fetchone()[0])
        top5 = conn.execute(
            "SELECT ts, model, prompt_tokens, completion_tokens, cost_usd "
            "FROM calls ORDER BY cost_usd DESC, id DESC LIMIT 5"
        ).fetchall()
    finally:
        conn.close()

    console.print(f"Total spend: ${total_spend:.6f}")
    console.print(f"Total calls: {total_calls}")

    table = Table(title="Top 5 most expensive calls")
    table.add_column("ts")
    table.add_column("model")
    table.add_column("prompt")
    table.add_column("completion")
    table.add_column("cost (usd)", justify="right")

    for ts, model, pt, ct, cost in top5:
        table.add_row(str(ts), str(model), str(int(pt)), str(int(ct)), f"${float(cost):.6f}")

    console.print(table)


if __name__ == "__main__":
    main()

