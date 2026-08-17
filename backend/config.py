"""Backend configuration."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def get_config() -> dict[str, Any]:
    """Return backend configuration from environment."""
    return {
        "out_root": os.environ.get("AUSLEX_OUT_ROOT", str(Path(__file__).resolve().parents[2] / "runs")),
        "port": int(os.environ.get("AUSLEX_UI_PORT", "8000")),
        "questions_path": os.environ.get(
            "AUSLEX_QUESTIONS",
            str(Path(__file__).resolve().parents[2] / "data" / "questions" / "auslex.jsonl"),
        ),
    }
