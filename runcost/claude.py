"""
RunCost Claude wrapper — drop-in cost tracking for Anthropic SDK.
Usage:
    from runcost.claude import Anthropic, BudgetConfig
    client = Anthropic(budget=BudgetConfig(hard_limit_usd=5.00))
    response = client.messages.create(...)
"""

from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional
import types

try:
    import anthropic as _anthropic
except ModuleNotFoundError:
    _anthropic = None

from ._db import DbLogger
from ._errors import BudgetExceededError
from ._pricing import usd

__all__ = ["Anthropic"]

# Anthropic pricing per token (March 2026)
ANTHROPIC_PRICING = {
    "claude-opus-4":        (0.000005,   0.000025),
    "claude-sonnet-4":      (0.000003,   0.000015),
    "claude-sonnet-4-5":    (0.000003,   0.000015),
    "claude-haiku-4":       (0.000001,   0.000005),
    "claude-haiku-4-5":     (0.000001,   0.000005),
    "claude-3-5-sonnet":    (0.000003,   0.000015),
    "claude-3-opus":        (0.000015,   0.000075),
    "claude-3-haiku":       (0.00000025, 0.00000125),
}
DEFAULT_ANTHROPIC = (0.000003, 0.000015)  # sonnet fallback

def _anthropic_price(model: str):
    m = model.lower()
    for key, pricing in ANTHROPIC_PRICING.items():
        if key in m:
            return pricing
    return DEFAULT_ANTHROPIC


class _MessagesProxy:
    def __init__(self, outer: "Anthropic"):
        self._outer = outer

    def create(self, *args: Any, **kwargs: Any) -> Any:
        cfg = self._outer._budget
        model = str(kwargs.get("model", "claude-sonnet-4"))
        max_tokens = kwargs.get("max_tokens", 1024)
        messages = kwargs.get("messages", [])

        in_rate, out_rate = _anthropic_price(model)

        # Estimate input tokens
        est_input = sum(len(str(m.get("content", ""))) // 4 for m in messages if isinstance(m, dict))
        est_cost = usd(est_input, max_tokens, in_rate, out_rate)

        # Budget check
        total = self._outer._current_total_usd()
        projected = total + est_cost
        if cfg.hard_limit_usd and projected > cfg.hard_limit_usd:
            raise BudgetExceededError(
                f"RunCost: Hard limit ${cfg.hard_limit_usd:.2f} would be exceeded. "
                f"Current: ${total:.4f}."
            )

        # Real call
        resp = self._outer._client.messages.create(*args, **kwargs)

        # Actual usage
        usage = getattr(resp, "usage", None)
        input_tokens = getattr(usage, "input_tokens", est_input) if usage else est_input
        output_tokens = getattr(usage, "output_tokens", 0) if usage else 0
        cost = usd(input_tokens, output_tokens, in_rate, out_rate)

        # Log
        if self._outer._db:
            self._outer._db.insert_call(
                ts=datetime.now(timezone.utc).isoformat(),
                model=model,
                prompt_tokens=input_tokens,
                completion_tokens=output_tokens,
                cost_usd=cost,
            )
        session_total = self._outer._add_to_total(cost)

        # Print
        try:
            from rich.console import Console
            from rich.text import Text
            text = Text()
            text.append("  RunCost[Claude] ", style="bold magenta")
            text.append(f"{model:<30}", style="cyan")
            text.append(f"  ${cost:.5f}", style="yellow")
            text.append(f"  [session: ${session_total:.5f}]", style="dim")
            Console().print(text)
        except ImportError:
            print(f"  RunCost[Claude]  {model:<30}  ${cost:.5f}  [session: ${session_total:.5f}]")

        return resp

    def __getattr__(self, name):
        return getattr(self._outer._client.messages, name)


class Anthropic:
    """
    Drop-in wrapper for anthropic.Anthropic with cost tracking.

    from runcost.claude import Anthropic, BudgetConfig
    client = Anthropic(budget=BudgetConfig(hard_limit_usd=5.00))
    response = client.messages.create(
        model="claude-sonnet-4-5-20251022",
        max_tokens=1024,
        messages=[{"role": "user", "content": "Hello"}]
    )
    """

    def __init__(self, *args, budget=None, **kwargs):
        if _anthropic is None:
            raise ModuleNotFoundError(
                "anthropic package required. Run: pip install anthropic"
            )
        from . import BudgetConfig as _BC
        self._budget = budget or _BC()
        self._client = _anthropic.Anthropic(*args, **kwargs)
        self._db = DbLogger("runcost.db") if self._budget.log_to_db else None
        self._running_total = 0.0

    @property
    def messages(self):
        return _MessagesProxy(self)

    def _current_total_usd(self):
        return self._db.total_spend_usd() if self._db else self._running_total

    def _add_to_total(self, delta):
        if self._db is None:
            self._running_total += delta
            return self._running_total
        return self._db.total_spend_usd()

    def __getattr__(self, name):
        return getattr(self._client, name)
