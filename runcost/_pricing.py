from __future__ import annotations
from typing import Any, Iterable, Tuple


# Pricing per TOKEN (not per 1K) — March 2026
MODEL_PRICING: dict[str, Tuple[float, float]] = {
    # OpenAI
    "gpt-4o":                  (0.0000025,  0.000010),
    "gpt-4o-mini":             (0.00000015, 0.0000006),
    "gpt-4-turbo":             (0.000010,   0.000030),
    "gpt-4":                   (0.000030,   0.000060),
    "gpt-4.1":                 (0.000002,   0.000008),
    "gpt-4.1-nano":            (0.0000001,  0.0000004),
    "gpt-3.5-turbo":           (0.0000005,  0.0000015),
    "gpt-5":                   (0.00000125, 0.000010),
    # Anthropic
    "claude-sonnet-4":         (0.000003,   0.000015),
    "claude-3-5-sonnet":       (0.000003,   0.000015),
    "claude-opus-4":           (0.000005,   0.000025),
    "claude-haiku-4":          (0.000001,   0.000005),
    "claude-3-haiku":          (0.00000025, 0.00000125),
    # Groq / Llama
    "llama-3.1-8b-instant":    (0.00000005, 0.00000008),
    "llama-3.1-70b-versatile": (0.00000059, 0.00000079),
    "llama3-8b-8192":          (0.00000005, 0.00000008),
    "llama3-70b-8192":         (0.00000059, 0.00000079),
    "llama":                   (0.00000005, 0.00000008),
    # Mistral
    "mixtral-8x7b-32768":      (0.00000024, 0.00000024),
    "mistral-7b-instruct":     (0.00000025, 0.00000025),
    "mistral-small":           (0.000001,   0.000003),
}

DEFAULT_PRICING: Tuple[float, float] = (0.0000025, 0.000010)  # fallback: gpt-4o


def price_for_model(model: str) -> Tuple[float, float]:
    """Returns (input_price_per_token, output_price_per_token)."""
    m = (model or "").lower()
    for key, pricing in MODEL_PRICING.items():
        if key in m:
            return pricing
    return DEFAULT_PRICING


def estimate_tokens_for_messages(messages: Any) -> int:
    """Lightweight heuristic: ~4 chars per token."""
    if not messages:
        return 0
    total_chars = 0
    overhead = 0
    if isinstance(messages, dict):
        messages = [messages]
    if isinstance(messages, Iterable) and not isinstance(messages, (str, bytes)):
        for msg in messages:
            if isinstance(msg, dict):
                overhead += 6
                content = msg.get("content", "")
                if isinstance(content, str):
                    total_chars += len(content)
                elif isinstance(content, list):
                    for part in content:
                        if isinstance(part, dict):
                            text = part.get("text")
                            if isinstance(text, str):
                                total_chars += len(text)
            elif isinstance(msg, str):
                overhead += 3
                total_chars += len(msg)
    elif isinstance(messages, str):
        total_chars = len(messages)
    return max(0, int(total_chars / 4) + overhead)


def usd(prompt_tokens: int, completion_tokens: int,
        in_rate: float, out_rate: float) -> float:
    """Calculate cost in USD given token counts and per-token rates."""
    return float(prompt_tokens) * float(in_rate) + float(completion_tokens) * float(out_rate)