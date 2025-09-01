"""Fetch current OpenAI GPT-4o pricing and estimate API cost.

This module tries to retrieve pricing information for the GPT-4o model from
OpenAI's pricing page. If the request fails (for example due to a network
restriction), it falls back to commonly reported May 2024 prices.  The
``estimate_cost`` helper can then compute the cost of a request given the
number of prompt and completion tokens.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import requests


# Fallback pricing in USD per token (May 2024 pricing: $0.005 /1K input,
# $0.015 /1K output)
FALLBACK_INPUT_PER_TOKEN = 0.005 / 1000
FALLBACK_OUTPUT_PER_TOKEN = 0.015 / 1000


@dataclass
class Pricing:
    """Simple container for model pricing."""

    input_per_token: float
    output_per_token: float


PRICING_URL = "https://openai.com/pricing"


def fetch_pricing(url: str = PRICING_URL) -> Pricing:
    """Fetch GPT-4o pricing from OpenAI.

    The pricing page is parsed using regular expressions. If anything goes
    wrong (network issues, unexpected format), ``Pricing`` constructed from the
    fallback constants is returned instead.
    """

    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        # Look for patterns like: "GPT-4o ... $0.005 / 1K tokens" etc.
        # Because the page is mostly static HTML, a regex search suffices.
        input_match = re.search(
            r"GPT-4o[^$]*\$([0-9.]+)\s*/\s*1K tokens\s*input", resp.text
        )
        output_match = re.search(
            r"GPT-4o[^$]*\$([0-9.]+)\s*/\s*1K tokens\s*output", resp.text
        )
        if input_match and output_match:
            input_per_token = float(input_match.group(1)) / 1000
            output_per_token = float(output_match.group(1)) / 1000
            return Pricing(input_per_token, output_per_token)
    except Exception:
        pass  # Fall back to defaults below

    return Pricing(FALLBACK_INPUT_PER_TOKEN, FALLBACK_OUTPUT_PER_TOKEN)


def estimate_cost(prompt_tokens: int, completion_tokens: int) -> tuple[float, Pricing]:
    """Estimate the cost of an API call.

    Returns a tuple of ``(cost, pricing)`` where ``cost`` is the total USD
    amount and ``pricing`` contains the per-token rates used.
    """

    pricing = fetch_pricing()
    cost = (
        prompt_tokens * pricing.input_per_token
        + completion_tokens * pricing.output_per_token
    )
    return cost, pricing


if __name__ == "__main__":
    # Example numbers from the earlier conversation
    prompt_tokens = 57
    completion_tokens = 99
    cost, pricing = estimate_cost(prompt_tokens, completion_tokens)
    print(
        f"Estimated cost: ${cost:.4f}\n"
        f"(Input: ${pricing.input_per_token * 1000:.3f}/1K tokens, "
        f"Output: ${pricing.output_per_token * 1000:.3f}/1K tokens)"
    )
