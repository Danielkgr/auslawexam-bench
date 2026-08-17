"""Offline HuggingFace dataset export.

Writes a folder laid out so it can be pushed to the HuggingFace Hub as-is: a
JSONL of items, a ``README.md`` carrying the Hub metadata block (task, language,
size, license, tags, config), and a ``dataset_info.json``. No network access is
performed here; publishing is a separate, explicit step (``huggingface-cli
upload``) so the harness stays safe to run offline.

If the optional ``datasets`` extra is installed, ``load_with_hf`` is available
to sanity-check that the folder loads as a HF Dataset.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

DEFAULT_LICENSE = "cc-by-4.0"
LICENSES = ["cc-by-4.0"]


@dataclass
class HfExport:
    path: str
    files: list[str] = field(default_factory=list)
    n_items: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {"path": self.path, "files": self.files, "n_items": self.n_items}


def _hf_readme(
    name: str,
    *,
    version: str,
    n_items: int,
    license_: str,
    tags: list[str],
    provisional: bool,
) -> str:
    tag_block = "\n".join(f"- {t}" for t in tags)
    provisional_note = (
        "> **Provisional.** These items are realistic exam-style questions "
        "authored for prototyping and **require verification by a qualified "
        "Australian lawyer** before any external use.\n"
        if provisional
        else ""
    )
    return f"""---
language:
- en
license: {license_}
size_categories:
- 10<n<100
task_categories:
- question-answering
- text-generation
tags:
{tag_block}
pretty_name: {name}
---

# {name}

{provisional_note}

A benchmark of **Australian legal reasoning**: exam-style law questions with
lawyer-verified gold answers, required authorities, and grading rubrics.
Each row is one question.

- **version:** {version}
- **items:** {n_items}
- **license:** {license_}
- **jurisdiction:** Australia (Commonwealth + all States/Territories)

## Fields

| column | type | description |
|---|---|---|
| `id` | string | stable item id (`auslex-YYYY-NNNN`) |
| `type` | string | mcq / short_answer / essay / fact_pattern |
| `jurisdiction` | list | AU jurisdictions in scope |
| `priestley_area` | string | one of the Priestley 11 core subjects |
| `topics` | list | fine-grained topic tags |
| `difficulty` | string | easy / medium / hard |
| `marks` | int | marks available |
| `question_text` | string | the question stem |
| `gold_answer` | string | lawyer-verified model answer |
| `key_issues` | list | issues a strong answer addresses |
| `required_authorities` | list | case/statute cites the answer must use |
| `rubric` | list | grading criteria with max marks |
| `law_as_at` | string | date the law is stated as at |
| `canary` | string | contamination canary string |
"""


def build_hf_export(
    dataset_dir: str | Path,
    items: list[dict[str, Any]],
    *,
    name: str = "auslex",
    version: str = "0.1.0",
    license_: str = DEFAULT_LICENSE,
    provisional: bool = True,
    tags: Optional[list[str]] = None,
) -> HfExport:
    """Write the Hub-ready dataset folder and return the file manifest."""
    d = Path(dataset_dir)
    d.mkdir(parents=True, exist_ok=True)
    tags = tags or ["law", "australia", "legal-reasoning", "benchmark",
                    "exam", "contamination-canary"]
    if provisional:
        tags = tags + ["provisional"]

    questions = d / "questions.jsonl"
    with open(questions, "w", encoding="utf-8") as fh:
        for it in items:
            # Export a flattened, HF-friendly row (drop run-only internals).
            row = {k: v for k, v in it.items() if k not in ("verification",)}
            row["verification"] = {
                "provisional": (it.get("provenance") or {}).get("provisional", True),
                "verified": bool((it.get("verification") or {}).get("verified_at")),
            }
            fh.write(json.dumps(row, sort_keys=True, default=str) + "\n")

    readme = d / "README.md"
    readme.write_text(
        _hf_readme(name, version=version, n_items=len(items),
                   license_=license_, tags=tags, provisional=provisional),
        encoding="utf-8",
    )

    info = d / "dataset_info.json"
    info.write_text(
        json.dumps(
            {
                "config": name,
                "version": version,
                "license": license_,
                "num_items": len(items),
                "jurisdiction": "Australia",
            },
            indent=2, sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )

    return HfExport(path=str(d), files=[str(questions), str(readme), str(info)],
                    n_items=len(items))


def load_with_hf(dataset_dir: str | Path) -> Any:
    """Sanity-check that the folder loads as a HF Dataset (requires the
    optional ``datasets`` extra). Raises a helpful error if it's missing."""
    try:
        from datasets import load_dataset  # type: ignore
    except ImportError as e:  # pragma: no cover - optional dep
        raise RuntimeError(
            "the 'datasets' package is not installed. Install with "
            "`pip install 'auslex[hf]'`."
        ) from e
    return load_dataset("json", data_files=str(Path(dataset_dir) / "questions.jsonl"))
