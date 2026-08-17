"""The single prompt template shared by every model in the benchmark.

Mirrors the Allens benchmark primer ("You are an experienced Australian
lawyer..."). Using ONE template for every model is a core reproducibility
requirement — no per-model prompt engineering, no leading.
"""

from __future__ import annotations

from typing import Any

# Bump whenever the template text below changes; recorded in every run's meta so
# two runs are comparable only if the template version matches.
TEMPLATE_VERSION = "1.0.0"

SYSTEM_PROMPT = (
    "You are an experienced Australian lawyer. Answer the question below as if "
    "sitting a final-year law examination. Apply only Australian law as it stood "
    "on the stated date. Identify the issues, state the governing rules with "
    "pinpoint authority (statutory provisions and cases), apply the law to the "
    "facts, and reach a clear conclusion. Cite real Australian primary sources "
    "only; do not invent cases or provisions."
)

USER_TEMPLATE = """Law as at: {law_as_at}
Jurisdiction(s): {jurisdictions}
Marks: {marks}

Question:
{question_text}

Instructions:
- Structure your answer to the mark allocation.
- For every proposition, give pinpoint authority (e.g. 'Competition and Consumer Act 2010 (Cth) s 18' or 'Waltons Stores (Interstate) Ltd v Maher (1988) 164 CLR 387').
- Distinguish the strongest competing arguments where they exist.
- Finish with a concise conclusion."""


def build_prompt(item: dict[str, Any]) -> tuple[str, str]:
    """Return ``(system, user)`` for an item dict."""
    user = USER_TEMPLATE.format(
        law_as_at=item.get("law_as_at", "n/a"),
        jurisdictions=", ".join(item.get("jurisdiction", [])) or "n/a",
        marks=item.get("marks", ""),
        question_text=item.get("question_text", ""),
    )
    return SYSTEM_PROMPT, user


def messages(item: dict[str, Any]) -> list[dict[str, str]]:
    """OpenAI-style message list for an item (works for local + OpenAI-compat)."""
    system, user = build_prompt(item)
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def prompt_hash(item: dict[str, Any]) -> str:
    """Content hash of the exact prompt sent to the model (for run addressing)."""
    from .io import sha256_of

    return sha256_of(messages(item))
