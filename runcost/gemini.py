"""
RunCost Gemini wrapper — drop-in cost tracking for Google Generative AI SDK.
Usage:
    from runcost.gemini import GenerativeModel, BudgetConfig
    model = GenerativeModel("gemini-1.5-pro", budget=BudgetConfig(hard_limit_usd=5.00))
    response = model.generate_content("Hello")
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Any, Optional

try:
    import google.generativeai as _genai
except ModuleNotFoundError:
    _genai = None

from ._db import DbLogger
from ._errors import BudgetExceededError
from ._pricing import usd

__all__ = ["GenerativeModel", "configure"]

# Gemini pricing per token (March 2026)
GEMINI_PRICING = {
    "gemini-2.0-flash":        (0.0000001,  0.0000004),
    "gemini-2.0-flash-lite":   (0.000000075,0.0000003),
    "gemini-1.5-pro":          (0.00000125, 0.000005),
    "gemini-1.5-flash":        (0.000000075,0.0000003),
    "gemini-1.5-flash-8b":     (0.0000000375,0.00000015),
    "gemini-1.0-pro":          (0.0000005,  0.0000015),
}
DEFAULT_GEMINI = (0.00000125, 0.000005)  # 1.5-pro fallback


def configure(api_key: str):
    """Configure the Gemini API key."""
    if _genai is None:
        raise ModuleNotFoundError("google-generativeai required. Run: pip install google-generativeai")
    _genai.configure(api_key=api_key)


def _gemini_price(model: str):
    m = model.lower()
    for key, pricing in GEMINI_PRICING.items():
        if key in m:
            return pricing
    return DEFAULT_GEMINI


def _count_tokens_approx(content) -> int:
    if isinstance(content, str):
        return len(content) // 4
    if isinstance(content, list):
        return sum(_count_tokens_approx(c) for c in content)
    return len(str(content)) // 4


class GenerativeModel:
    """
    Drop-in wrapper for google.generativeai.GenerativeModel with cost tracking.

    from runcost.gemini import GenerativeModel, configure
    configure(api_key="your-gemini-key")
    model = GenerativeModel("gemini-1.5-pro", budget=BudgetConfig(hard_limit_usd=5.00))
    response = model.generate_content("Explain quantum computing")
    """

    def __init__(self, model_name: str, *args, budget=None, **kwargs):
        if _genai is None:
            raise ModuleNotFoundError(
                "google-generativeai required. Run: pip install google-generativeai"
            )
        from . import BudgetConfig as _BC
        self._budget = budget or _BC()
        self._model_name = model_name
        self._model = _genai.GenerativeModel(model_name, *args, **kwargs)
        self._db = DbLogger("runcost.db") if self._budget.log_to_db else None
        self._running_total = 0.0

    def generate_content(self, contents, **kwargs) -> Any:
        cfg = self._budget
        in_rate, out_rate = _gemini_price(self._model_name)

        est_input = _count_tokens_approx(contents)
        est_cost = usd(est_input, 500, in_rate, out_rate)

        # Budget check
        total = self._current_total_usd()
        projected = total + est_cost
        if cfg.hard_limit_usd and projected > cfg.hard_limit_usd:
            raise BudgetExceededError(
                f"RunCost: Hard limit ${cfg.hard_limit_usd:.2f} would be exceeded. "
                f"Current: ${total:.4f}."
            )

        # Real call
        resp = self._model.generate_content(contents, **kwargs)

        # Token counts from response
        usage = getattr(resp, "usage_metadata", None)
        input_tokens = getattr(usage, "prompt_token_count", est_input) if usage else est_input
        output_tokens = getattr(usage, "candidates_token_count", 0) if usage else 0
        cost = usd(input_tokens, output_tokens, in_rate, out_rate)

        # Log
        if self._db:
            self._db.insert_call(
                ts=datetime.now(timezone.utc).isoformat(),
                model=self._model_name,
                prompt_tokens=input_tokens,
                completion_tokens=output_tokens,
                cost_usd=cost,
            )
        session_total = self._add_to_total(cost)

        # Print
        try:
            from rich.console import Console
            from rich.text import Text
            text = Text()
            text.append("  RunCost[Gemini] ", style="bold blue")
            text.append(f"{self._model_name:<30}", style="cyan")
            text.append(f"  ${cost:.5f}", style="yellow")
            text.append(f"  [session: ${session_total:.5f}]", style="dim")
            Console().print(text)
        except ImportError:
            print(f"  RunCost[Gemini]  {self._model_name:<30}  ${cost:.5f}  [session: ${session_total:.5f}]")

        return resp

    def _current_total_usd(self):
        return self._db.total_spend_usd() if self._db else self._running_total

    def _add_to_total(self, delta):
        if self._db is None:
            self._running_total += delta
            return self._running_total
        return self._db.total_spend_usd()

    def __getattr__(self, name):
        return getattr(self._model, name)
