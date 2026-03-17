from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import types
from typing import Any, Optional

try:
    import openai as _openai
except ModuleNotFoundError:  # pragma: no cover
    _openai = types.SimpleNamespace(OpenAI=None)

from ._db import DbLogger
from ._errors import BudgetExceededError
from ._pricing import estimate_tokens_for_messages, price_for_model, usd

__all__ = ["OpenAI", "BudgetConfig", "BudgetExceededError"]


@dataclass(frozen=True)
class BudgetConfig:
    hard_limit_usd: Optional[float] = None
    warn_at_usd: Optional[float] = None
    log_to_db: bool = True


class OpenAI:
    """
    Drop-in wrapper for `openai.OpenAI` that intercepts `chat.completions.create`
    to estimate and log cost.
    """

    def __init__(self, *args: Any, budget: Optional[BudgetConfig] = None, **kwargs: Any):
        if getattr(_openai, "OpenAI", None) is None:  # pragma: no cover
            raise ModuleNotFoundError(
                "openai is required to use runcost.OpenAI. Install it with: pip install openai"
            )
        self._client = _openai.OpenAI(*args, **kwargs)
        self._budget = budget or BudgetConfig()
        self._db = DbLogger("runcost.db") if self._budget.log_to_db else None
        self._running_total_usd = 0.0

    @property
    def chat(self) -> "_ChatProxy":
        return _ChatProxy(self)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._client, name)

    def _current_total_usd(self) -> float:
        if self._db is not None:
            return self._db.total_spend_usd()
        return self._running_total_usd

    def _add_to_total(self, delta_usd: float) -> float:
        if self._db is None:
            self._running_total_usd += float(delta_usd)
            return self._running_total_usd
        return self._db.total_spend_usd()

    def _enforce_budget_pre_call(self, estimated_cost_usd: float) -> None:
        total = self._current_total_usd()
        projected = total + float(estimated_cost_usd)

        if self._budget.hard_limit_usd is not None and projected > self._budget.hard_limit_usd:
            raise BudgetExceededError(
                f"RunCost budget exceeded: projected ${projected:.6f} "
                f"would exceed hard limit ${self._budget.hard_limit_usd:.6f}."
            )

        if self._budget.warn_at_usd is not None and projected >= self._budget.warn_at_usd:
            print(
                f"runcost warning: projected total ${projected:.6f} "
                f"has reached warn_at ${self._budget.warn_at_usd:.6f}"
            )

    def _post_call_log_and_print(
        self,
        *,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost_usd: float,
    ) -> None:
        ts = datetime.now(timezone.utc).isoformat()

        if self._db is not None:
            self._db.insert_call(
                ts=ts,
                model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cost_usd=cost_usd,
            )

        total = self._add_to_total(cost_usd)
        total_tokens = int(prompt_tokens) + int(completion_tokens)

        print(
            "runcost "
            f"model={model} "
            f"tokens={prompt_tokens}+{completion_tokens}={total_tokens} "
            f"cost=${cost_usd:.6f} "
            f"total=${total:.6f}"
        )


class _ChatProxy:
    def __init__(self, outer: OpenAI):
        self._outer = outer

    @property
    def completions(self) -> "_ChatCompletionsProxy":
        return _ChatCompletionsProxy(self._outer)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._outer._client.chat, name)


class _ChatCompletionsProxy:
    def __init__(self, outer: OpenAI):
        self._outer = outer

    def create(self, *args: Any, **kwargs: Any) -> Any:
        model = kwargs.get("model")
        if model is None and args:
            model = args[0]
        model = str(model) if model is not None else "unknown"

        messages = kwargs.get("messages") or []
        max_tokens = kwargs.get("max_tokens")

        est_prompt = estimate_tokens_for_messages(messages)
        est_completion = int(max_tokens) if isinstance(max_tokens, int) and max_tokens > 0 else 0

        in_rate, out_rate = price_for_model(model)
        est_cost = usd(est_prompt, est_completion, in_rate, out_rate)

        self._outer._enforce_budget_pre_call(est_cost)

        resp = self._outer._client.chat.completions.create(*args, **kwargs)

        usage = getattr(resp, "usage", None)
        prompt_tokens = int(getattr(usage, "prompt_tokens", 0) or 0)
        completion_tokens = int(getattr(usage, "completion_tokens", 0) or 0)

        cost = usd(prompt_tokens, completion_tokens, in_rate, out_rate)
        self._outer._post_call_log_and_print(
            model=model,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_usd=cost,
        )

        return resp

    def __getattr__(self, name: str) -> Any:
        return getattr(self._outer._client.chat.completions, name)