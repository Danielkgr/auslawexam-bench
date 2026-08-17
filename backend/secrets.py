"""Local, gitignored secrets store for API keys.

Keys are held in-process for the lifetime of the server and persisted to a
gitignored file at ``~/.auslex-ui/keys.json``. They are never logged, never
returned to the client (masked indicators only), and never written into run
outputs.
"""

from __future__ import annotations

import json
import os
import stat
from pathlib import Path
from typing import Optional

SECRETS_DIR = Path.home() / ".auslex-ui"
SECRETS_FILE = SECRETS_DIR / "keys.json"


def _ensure_dir() -> None:
    SECRETS_DIR.mkdir(mode=0o700, exist_ok=True)


def load_secrets() -> dict[str, str]:
    """Return the secrets dict (may be empty)."""
    _ensure_dir()
    if not SECRETS_FILE.exists():
        return {}
    with open(SECRETS_FILE, "r", encoding="utf-8") as fh:
        return json.load(fh)


def save_secrets(secrets: dict[str, str]) -> None:
    """Persist secrets with restrictive permissions (0600)."""
    _ensure_dir()
    tmp = SECRETS_FILE.with_suffix(".tmp")
    data = json.dumps(secrets, sort_keys=True)
    with open(tmp, "w", encoding="utf-8") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, SECRETS_FILE)
    os.chmod(SECRETS_FILE, 0o600)


def get_key(provider: str) -> Optional[str]:
    """Retrieve a key by provider name ('openai', 'anthropic', 'google')."""
    env_var = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "google": "GOOGLE_API_KEY",
    }.get(provider)
    if env_var:
        val = os.environ.get(env_var)
        if val:
            return val
    return load_secrets().get(provider)


def set_key(provider: str, key: str) -> None:
    """Store a key for a provider."""
    secrets = load_secrets()
    secrets[provider] = key
    save_secrets(secrets)


def delete_key(provider: str) -> None:
    """Remove a stored key."""
    secrets = load_secrets()
    secrets.pop(provider, None)
    save_secrets(secrets)


def clear_all() -> None:
    """Remove all stored keys."""
    save_secrets({})
