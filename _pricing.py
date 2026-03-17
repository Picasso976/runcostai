from __future__ import annotations

from typing import Any, Iterable, Tuple


def price_for_model(model: str) -> Tuple[float, float]:
    m = (model or "").lower()
    if "gpt-4o" in m:
        return 0.005 / 1000.0, 0.015 / 1000.0
    if "gpt-3.5-turbo" in m:
        r = 0.0005 / 1000.0
        return r, r
    if "llama" in m:
        r = 0.0001 / 1000.0
        return r, r
    return 0.0, 0.0


def estimate_tokens_for_messages(messages: Any) -> int:
    """
    Lightweight heuristic token estimator (no tiktoken dependency).
    Assumes ~4 characters per token plus small per-message overhead.
    """
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


def usd(prompt_tokens: int, completion_tokens: int, in_rate: float, out_rate: float) -> float:
    return float(prompt_tokens) * float(in_rate) + float(completion_tokens) * float(out_rate)

