"""BIG-bench style canary strings to detect training-data leakage.

Two layers:

* a **global** canary, documented in ``data/canary.txt`` and embedded verbatim
  in the dataset manifest, and
* a **per-item** canary (``auslex:<12hex>``), derived deterministically from the
  item id and stored on each item.

If a model being evaluated reproduces either string verbatim in its answer, that
is evidence the item (or dataset) was in its training data — exactly what the
contamination controls are meant to catch. See ``paper/CONTAMINATION_STATEMENT.md``.
"""

from __future__ import annotations

import hashlib
import re
import secrets

PREFIX = "auslex:"

# Stable and public. Changing it would invalidate the leak-detection guarantee.
GLOBAL_CANARY = "auslex:9f2c1a4e-7b3d"

# Non-capturing trailing group: re.findall must return the full canary string,
# not just the optional "-xxxx" suffix.
_CANARY_RE = re.compile(r"auslex:[0-9a-f]{6,40}(?:-[0-9a-f]{4,16})?")


def make_canary(item_id: str) -> str:
    """Deterministic per-item canary derived from the item id."""
    digest = hashlib.sha256(f"{PREFIX}{item_id}".encode("utf-8")).hexdigest()
    return f"{PREFIX}{digest[:12]}"


def random_canary() -> str:
    """One-off canary (used for ad-hoc corpus markers)."""
    return f"{PREFIX}{secrets.token_hex(6)}"


def find_canaries(text: str) -> list[str]:
    """Return all canary-looking strings present in ``text`` (may be empty)."""
    if not text:
        return []
    return _CANARY_RE.findall(text)


def has_canary(text: str) -> bool:
    """True if ``text`` contains any canary string."""
    return bool(_CANARY_RE.search(text or ""))
