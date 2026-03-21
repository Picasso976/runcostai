"""
RunCost v0.3.0 - Drop-in cost intelligence for AI agent frameworks.
Now with: auto-routing, loop detection, Slack/Discord alerts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from collections import defaultdict
import hashlib
import types
import urllib.request
import json
from typing import Any, Optional, List

try:
    import openai as _openai
except ModuleNotFoundError:
    _openai = types.SimpleNamespace(OpenAI=None)

from ._db import DbLogger
from ._errors import BudgetExceededError
from ._pricing import estimate_tokens_for_messages, price_for_model, usd

__all__ = ["OpenAI", "BudgetConfig", "BudgetExceededError"]
__version__ = "0.3.0"


# ── ROUTING CLASSIFIER ────────────────────────────────────────────────────────

# Models ranked cheapest to most capable
CHEAP_MODELS = [
    "llama-3.1-8b-instant",   # Groq - fastest and cheapest
    "llama3-8b-8192",         # Groq
    "llama-3.1-70b-versatile", # Groq - mid tier
    "mistral-7b-instruct",    # Mistral
    "mixtral-8x7b-32768",     # Mistral
    "gpt-4o-mini",            # OpenAI budget
    "gpt-4.1-nano",           # OpenAI nano
]

# Keywords that signal complex reasoning — keep on expensive model
COMPLEX_SIGNALS = [
    "reason", "analyze", "analyse", "explain", "compare", "evaluate",
    "critique", "synthesize", "infer", "deduce", "plan", "strategy",
    "code", "debug", "implement", "architecture", "design", "optimize",
    "proof", "theorem", "calculate", "derive", "hypothesis",
    "write a", "create a", "build a", "generate a",
]

# Keywords that signal simple tasks — safe to route cheap
SIMPLE_SIGNALS = [
    "summarize", "summary", "list", "format", "translate", "extract",
    "classify", "categorize", "label", "tag", "sort", "filter",
    "yes or no", "true or false", "what is", "define", "lookup",
    "convert", "reformat", "clean", "fix typos", "spell check",
]

def classify_complexity(messages: list, max_tokens: Optional[int] = None) -> str:
    """Returns 'simple', 'medium', or 'complex'."""
    if not messages:
        return "simple"

    # Long expected output = complex
    if max_tokens and max_tokens > 1000:
        return "complex"

    # Check content
    content = " ".join(
        m.get("content", "").lower()
        for m in messages
        if isinstance(m, dict)
    ).strip()

    if not content:
        return "simple"

    token_estimate = len(content) // 4

    # Very long input = complex
    if token_estimate > 3000:
        return "complex"

    # Check for complex signals
    complex_count = sum(1 for s in COMPLEX_SIGNALS if s in content)
    simple_count = sum(1 for s in SIMPLE_SIGNALS if s in content)

    if complex_count > simple_count:
        return "complex"
    if simple_count > 0 and complex_count == 0:
        return "simple"
    if token_estimate < 200:
        return "simple"
    if token_estimate < 800:
        return "medium"

    return "complex"


def get_routed_model(original_model: str, complexity: str,
                     cheap_model: str = "llama3-8b-8192") -> str:
    """Returns the model to actually use after routing."""
    # Never route away from already-cheap models
    orig_lower = original_model.lower()
    for m in CHEAP_MODELS:
        if m in orig_lower or orig_lower in m:
            return original_model

    if complexity == "simple":
        return cheap_model
    if complexity == "medium":
        return "mixtral-8x7b-32768"
    return original_model  # complex: keep original


# ── LOOP DETECTOR ─────────────────────────────────────────────────────────────

def _hash_messages(messages: list) -> str:
    """Create a fingerprint of messages for loop detection."""
    content = json.dumps(messages, sort_keys=True, default=str)
    return hashlib.md5(content.encode()).hexdigest()[:12]


# ── WEBHOOK ALERTS ────────────────────────────────────────────────────────────

def _send_webhook(url: str, payload: dict) -> bool:
    """Send a JSON payload to a Slack or Discord webhook URL."""
    try:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except Exception:
        return False


def send_slack_alert(webhook_url: str, message: str) -> bool:
    return _send_webhook(webhook_url, {"text": message})


def send_discord_alert(webhook_url: str, message: str) -> bool:
    return _send_webhook(webhook_url, {"content": message})


# ── CONFIG ────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class BudgetConfig:
    # Budget
    hard_limit_usd: Optional[float] = None
    warn_at_usd: Optional[float] = None
    log_to_db: bool = True

    # Auto-routing
    auto_route: bool = False
    cheap_model: str = "llama3-8b-8192"

    # Loop detection
    block_loops: bool = False
    loop_threshold: int = 5       # block after this many identical calls
    loop_window: int = 20         # look back this many calls

    # Alerts
    slack_webhook: Optional[str] = None
    discord_webhook: Optional[str] = None
    alert_on_block: bool = True   # alert when loop blocked
    alert_on_warn: bool = True    # alert when warn_at_usd hit
    alert_on_limit: bool = True   # alert when hard limit hit


# ── MAIN CLIENT ───────────────────────────────────────────────────────────────

class OpenAI:
    """
    Drop-in replacement for openai.OpenAI with cost tracking,
    auto-routing, loop detection, and spend alerts.

    from runcost import OpenAI, BudgetConfig
    client = OpenAI(budget=BudgetConfig(
        hard_limit_usd=5.00,
        auto_route=True,
        block_loops=True,
        slack_webhook="https://hooks.slack.com/...",
    ))
    """

    def __init__(self, *args: Any, budget: Optional[BudgetConfig] = None, **kwargs: Any):
        if getattr(_openai, "OpenAI", None) is None:
            raise ModuleNotFoundError(
                "openai is required. Run: pip install openai"
            )
        self._client = _openai.OpenAI(*args, **kwargs)
        self._budget = budget or BudgetConfig()
        self._db = DbLogger("runcost.db") if self._budget.log_to_db else None
        self._running_total_usd = 0.0
        self._call_hashes: List[str] = []  # for loop detection

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

    def _send_alert(self, message: str) -> None:
        """Send to Slack and/or Discord if configured."""
        cfg = self._budget
        if cfg.slack_webhook:
            send_slack_alert(cfg.slack_webhook, f"RunCost: {message}")
        if cfg.discord_webhook:
            send_discord_alert(cfg.discord_webhook, f"RunCost: {message}")

    def _check_loop(self, msg_hash: str) -> bool:
        """Returns True if this call looks like a loop."""
        cfg = self._budget
        if not cfg.block_loops:
            return False
        window = self._call_hashes[-cfg.loop_window:]
        count = window.count(msg_hash)
        return count >= cfg.loop_threshold

    def _enforce_budget_pre_call(self, estimated_cost_usd: float) -> None:
        cfg = self._budget
        total = self._current_total_usd()
        projected = total + float(estimated_cost_usd)

        if cfg.hard_limit_usd is not None and projected > cfg.hard_limit_usd:
            msg = (
                f"Budget limit ${cfg.hard_limit_usd:.2f} would be exceeded. "
                f"Current: ${total:.4f}. Call blocked."
            )
            if cfg.alert_on_limit:
                self._send_alert(f"HARD LIMIT HIT — {msg}")
            raise BudgetExceededError(f"RunCost: {msg}")

        if cfg.warn_at_usd is not None and projected >= cfg.warn_at_usd:
            msg = f"Spend ${projected:.4f} approaching limit ${cfg.warn_at_usd:.2f}"
            try:
                from rich.console import Console
                Console().print(f"[bold yellow]  RunCost WARNING[/] {msg}")
            except ImportError:
                print(f"  RunCost WARNING: {msg}")
            if cfg.alert_on_warn:
                self._send_alert(f"SPEND WARNING — {msg}")

    def _post_call_log_and_print(
        self, *, model: str, original_model: str,
        prompt_tokens: int, completion_tokens: int, cost_usd: float,
        routed: bool = False, blocked: bool = False,
    ) -> None:
        ts = datetime.now(timezone.utc).isoformat()
        if self._db is not None:
            self._db.insert_call(
                ts=ts, model=model,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cost_usd=cost_usd,
            )
        total = self._add_to_total(cost_usd)
        total_tokens = int(prompt_tokens) + int(completion_tokens)

        routed_note = f" [routed from {original_model}]" if routed else ""
        blocked_note = " [LOOP BLOCKED]" if blocked else ""

        try:
            from rich.console import Console
            from rich.text import Text
            console = Console()
            text = Text()
            if blocked:
                text.append("  RunCost ", style="bold red")
                text.append(f"BLOCKED{blocked_note}", style="red")
            else:
                text.append("  RunCost ", style="bold green")
                text.append(f"{model:<28}", style="cyan")
                if routed:
                    text.append(f"  ↩ {original_model}", style="dim")
                text.append(f"  ${cost_usd:.5f}", style="yellow")
                text.append(f"  [session: ${total:.5f}]", style="dim")
            console.print(text)
        except ImportError:
            print(
                f"  RunCost  {'BLOCKED' if blocked else model:<28}"
                f"  ${cost_usd:.5f}  [session: ${total:.5f}]{routed_note}{blocked_note}"
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
        cfg = self._outer._budget
        original_model = str(kwargs.get("model") or (args[0] if args else "unknown"))
        messages = kwargs.get("messages") or []
        max_tokens = kwargs.get("max_tokens")

        # ── Loop detection ────────────────────────────────────
        msg_hash = _hash_messages(messages)
        self._outer._call_hashes.append(msg_hash)
        if len(self._outer._call_hashes) > 100:
            self._outer._call_hashes = self._outer._call_hashes[-100:]

        if self._outer._check_loop(msg_hash):
            if cfg.alert_on_block:
                self._outer._send_alert(
                    f"LOOP BLOCKED — agent '{original_model}' repeated "
                    f"same call {cfg.loop_threshold}+ times. Blocking."
                )
            self._outer._post_call_log_and_print(
                model=original_model, original_model=original_model,
                prompt_tokens=0, completion_tokens=0,
                cost_usd=0.0, blocked=True,
            )
            from ._errors import BudgetExceededError
            raise BudgetExceededError(
                f"RunCost: Recursive loop detected for model '{original_model}'. "
                f"Same call repeated {cfg.loop_threshold}+ times. "
                f"Set block_loops=False to disable."
            )

        # ── Auto-routing ──────────────────────────────────────
        routed = False
        model = original_model
        if cfg.auto_route:
            complexity = classify_complexity(messages, max_tokens)
            routed_model = get_routed_model(original_model, complexity, cfg.cheap_model)
            if routed_model != original_model:
                model = routed_model
                kwargs = dict(kwargs)
                kwargs["model"] = model
                routed = True

        # ── Pre-flight cost estimate ──────────────────────────
        est_prompt = estimate_tokens_for_messages(messages)
        est_completion = int(max_tokens) if isinstance(max_tokens, int) and max_tokens > 0 else 200
        in_rate, out_rate = price_for_model(model)
        est_cost = usd(est_prompt, est_completion, in_rate, out_rate)
        self._outer._enforce_budget_pre_call(est_cost)

        # ── Real API call ─────────────────────────────────────
        resp = self._outer._client.chat.completions.create(*args, **kwargs)

        # ── Actual cost ───────────────────────────────────────
        usage = getattr(resp, "usage", None)
        prompt_tokens = int(getattr(usage, "prompt_tokens", est_prompt) or est_prompt)
        completion_tokens = int(getattr(usage, "completion_tokens", 200) or 200)
        cost = usd(prompt_tokens, completion_tokens, in_rate, out_rate)

        self._outer._post_call_log_and_print(
            model=model, original_model=original_model,
            prompt_tokens=prompt_tokens, completion_tokens=completion_tokens,
            cost_usd=cost, routed=routed,
        )
        return resp

    def __getattr__(self, name: str) -> Any:
        return getattr(self._outer._client.chat.completions, name)