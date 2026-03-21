"""
RunCost CLI
"""

import sqlite3
import os
import time
from datetime import datetime

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.text import Text
    from rich.columns import Columns
    from rich import box
    import click
    _deps = True
except ImportError:
    _deps = False


def get_db_path():
    return os.environ.get("RUNCOST_DB", "runcost.db")


def fetch_stats(db_path):
    if not os.path.exists(db_path):
        return None
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row

        totals = conn.execute("""
            SELECT
                COUNT(*) as total_calls,
                COALESCE(SUM(cost_usd), 0) as total_spend,
                COALESCE(SUM(CASE WHEN blocked=1 THEN 1 ELSE 0 END), 0) as blocked_calls,
                COALESCE(SUM(prompt_tokens), 0) as total_input,
                COALESCE(SUM(completion_tokens), 0) as total_output
            FROM calls
        """).fetchone()

        recent = conn.execute("""
            SELECT model, prompt_tokens, completion_tokens, cost_usd, ts
            FROM calls ORDER BY ts DESC LIMIT 8
        """).fetchall()

        by_model = conn.execute("""
            SELECT model, COUNT(*) as calls, SUM(cost_usd) as spend
            FROM calls WHERE blocked=0
            GROUP BY model ORDER BY spend DESC LIMIT 6
        """).fetchall()

        hourly = conn.execute("""
            SELECT strftime('%H:00', ts) as hour,
                   SUM(cost_usd) as spend,
                   COUNT(*) as calls
            FROM calls
            WHERE ts >= datetime('now', '-6 hours')
            GROUP BY hour ORDER BY hour
        """).fetchall()

        conn.close()
        return {
            "totals": dict(totals),
            "recent": [dict(r) for r in recent],
            "by_model": [dict(r) for r in by_model],
            "hourly": [dict(r) for r in hourly],
        }
    except Exception as e:
        return {"error": str(e)}


if _deps:
    @click.group()
    def cli():
        """RunCost — cost intelligence for AI agents. https://cost.run"""
        pass

    @cli.command()
    @click.option("--db", default=None, help="Path to runcost.db")
    @click.option("--live", is_flag=True, default=False, help="Auto-refresh every 2 seconds")
    def dashboard(db, live):
        """Show the RunCost terminal dashboard."""
        db_path = db or get_db_path()
        console = Console()

        def render():
            stats = fetch_stats(db_path)
            console.clear()

            console.print(Panel(
                Text("RunCost Dashboard", style="bold green", justify="center"),
                subtitle=f"[dim]{db_path}  •  {datetime.now().strftime('%H:%M:%S')}[/]",
                border_style="green",
            ))

            if stats is None:
                console.print(Panel(
                    Text("No runcost.db found.\nRun some agents first:\n\n  from runcost import OpenAI\n  client = OpenAI()",
                         style="dim", justify="center"),
                    border_style="dim",
                ))
                return

            t = stats["totals"]
            total_spend = float(t["total_spend"])
            total_calls = int(t["total_calls"])
            blocked = int(t["blocked_calls"])

            stats_table = Table.grid(expand=True, padding=(0, 1))
            stats_table.add_column(justify="center")
            stats_table.add_column(justify="center")
            stats_table.add_column(justify="center")
            stats_table.add_column(justify="center")
            stats_table.add_row(
                Panel(Text(f"[bold green]${total_spend:.4f}[/]\n[dim]total spend[/]", justify="center"), border_style="green"),
                Panel(Text(f"[bold cyan]{total_calls}[/]\n[dim]api calls[/]", justify="center"), border_style="cyan"),
                Panel(Text(f"[bold red]{blocked}[/]\n[dim]loops blocked[/]", justify="center"), border_style="red"),
                Panel(Text(f"[bold yellow]{int(t['total_input'])+int(t['total_output']):,}[/]\n[dim]tokens used[/]", justify="center"), border_style="yellow"),
            )
            console.print(stats_table)

            recent_table = Table(box=box.SIMPLE, title="Recent Calls", title_style="bold green", expand=True)
            recent_table.add_column("Model", style="cyan", max_width=22)
            recent_table.add_column("Tokens", justify="right", style="dim")
            recent_table.add_column("Cost", justify="right", style="yellow")
            for row in stats["recent"]:
                tokens = int(row["prompt_tokens"]) + int(row["completion_tokens"])
                recent_table.add_row(row["model"], str(tokens), f"${float(row['cost_usd']):.5f}")

            model_table = Table(box=box.SIMPLE, title="By Model", title_style="bold green", expand=True)
            model_table.add_column("Model", style="cyan", max_width=22)
            model_table.add_column("Calls", justify="right")
            model_table.add_column("Spend", justify="right", style="yellow")
            for row in stats["by_model"]:
                model_table.add_row(row["model"], str(row["calls"]), f"${float(row['spend']):.4f}")

            console.print(Columns([
                Panel(recent_table, border_style="dim"),
                Panel(model_table, border_style="dim"),
            ]))

            if stats["hourly"]:
                max_spend = max(float(r["spend"]) for r in stats["hourly"]) or 1
                lines = []
                for row in stats["hourly"]:
                    spend = float(row["spend"])
                    bar_len = int((spend / max_spend) * 25)
                    bar = "▓" * bar_len + "░" * (25 - bar_len)
                    lines.append(f"  [dim]{row['hour']}[/]  [green]{bar}[/]  [yellow]${spend:.4f}[/]")
                console.print(Panel("\n".join(lines), title="Spend Last 6 Hours", border_style="dim"))

            if live:
                console.print(Text("  Auto-refreshing every 2s — Ctrl+C to exit", style="dim"))

        if live:
            try:
                while True:
                    render()
                    time.sleep(2)
            except KeyboardInterrupt:
                console.print("\n[dim]Dashboard closed.[/]")
        else:
            render()

    @cli.command()
    def summary():
        """Quick spend summary."""
        db_path = get_db_path()
        console = Console()

        if not os.path.exists(db_path):
            console.print("[dim]No runcost.db found. Run some agents first.[/]")
            return

        stats = fetch_stats(db_path)
        t = stats["totals"]

        console.print(Panel(
            f"[bold green]${float(t['total_spend']):.4f}[/] spent  •  "
            f"[cyan]{t['total_calls']}[/] calls  •  "
            f"[red]{t['blocked_calls']}[/] blocked",
            title="[bold]RunCost Summary[/]",
            border_style="green",
        ))

        if stats["by_model"]:
            table = Table(box=box.SIMPLE, show_header=True)
            table.add_column("Model", style="cyan")
            table.add_column("Calls", justify="right")
            table.add_column("Spend", justify="right", style="yellow")
            for row in stats["by_model"]:
                table.add_row(row["model"], str(row["calls"]), f"${float(row['spend']):.4f}")
            console.print(table)

    @cli.command()
    def server():
        """Launch the RunCost web dashboard in your browser."""
        from runcost.server import main as server_main
        server_main()

    def main():
        cli()

else:
    def main():
        print("RunCost CLI requires: pip install click rich")
        print("Run: pip install runcost[full]")