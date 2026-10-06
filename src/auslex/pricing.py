"""Model prices in USD per million tokens, input then output.

Only prices confirmed for this release are listed.  A model that is missing
reports no cost rather than a guessed one, and ``auslex estimate --price``
accepts a price for it.
"""

from __future__ import annotations

PRICES_PER_MTOK: dict[str, tuple[float, float]] = {
    # Anthropic first-party standard prices.
    "claude-opus-5-5": (4.0, 20.0),
    "claude-sonnet-5-5": (2.0, 10.0),
    "claude-haiku-4-5": (1.0, 5.0),
    "claude-fable-5-1": (10.0, 50.0),
    # Gemini API model page for gemini-3.1-flash-lite, October 2026.
    "gemini-3.1-flash-lite": (0.25, 1.50),
    # Groq model page for openai/gpt-oss-120b, October 2026.
    "openai/gpt-oss-120b": (0.15, 0.60),
}


def price_for(model: str) -> tuple[float, float] | None:
    """The (input, output) price per million tokens, or None when unconfirmed."""
    return PRICES_PER_MTOK.get(model)


def cost_usd(model: str, prompt_tokens: int, completion_tokens: int) -> float | None:
    price = price_for(model)
    if price is None:
        return None
    return round((prompt_tokens * price[0] + completion_tokens * price[1]) / 1_000_000, 6)
