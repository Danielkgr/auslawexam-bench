"""Pydantic models for the auslex item schema.

One JSONL line == one ``QuestionItem``. The schema is the contract between
authoring, ingestion, running, scoring, and publishing — everything downstream
relies on these fields being present and well-formed.
"""

from __future__ import annotations

import datetime as _dt
import re
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Jurisdiction = Literal[
    "Cth", "VIC", "NSW", "QLD", "WA", "SA", "TAS", "NT", "ACT"
]
ItemKind = Literal["short_answer", "hypothetical", "essay", "mcq"]
Tier = Literal["A", "B", "C", "D"]
Difficulty = Literal["pass", "credit", "distinction", "high_distinction"]
AuthorityKind = Literal["statute", "case", "regulation", "other"]

# The Priestley 11 plus a statutory bucket for Cth/VIC-weighted topics.
PRIESTLEY_AREAS = frozenset(
    {
        "contract",
        "torts",
        "crime",
        "constitutional",
        "admin",
        "equity_trusts",
        "property",
        "corporations",
        "evidence",
        "civil_procedure",
        "ethics",
        "statutory",
    }
)

_ID_RE = r"^auslex-\d{4}-\d{4}$"
_SEMVER_RE = r"^\d+\.\d+\.\d+$"


def _is_iso_date(value: str) -> bool:
    try:
        _dt.date.fromisoformat(value)
        return True
    except ValueError:
        return False


class Authority(BaseModel):
    """A primary source the gold answer relies on."""

    kind: AuthorityKind
    cite: str
    point_in_time: Optional[str] = None

    @field_validator("point_in_time")
    @classmethod
    def _check_date(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not _is_iso_date(v):
            raise ValueError(f"point_in_time must be YYYY-MM-DD, got {v!r}")
        return v


class RubricCriterion(BaseModel):
    """One scored dimension of an item. ``max`` marks for the criterion."""

    criterion: str
    max: int = Field(gt=0)
    weight: Optional[float] = Field(default=None, gt=0)

    @field_validator("criterion")
    @classmethod
    def _nonempty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("criterion name cannot be empty")
        return v


class Provenance(BaseModel):
    tier: Tier
    author: str
    style_ref: Optional[str] = None
    # Sample items shipped with the prototype are provisional (not yet
    # lawyer-verified). Flipping this to False is part of the verification gate.
    provisional: bool = True


class Verification(BaseModel):
    verifier: Optional[str] = None
    verified_at: Optional[str] = None
    second_pass: bool = False
    hash: Optional[str] = None

    @field_validator("verified_at")
    @classmethod
    def _check_date(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not _is_iso_date(v):
            raise ValueError(f"verified_at must be YYYY-MM-DD, got {v!r}")
        return v


class QuestionItem(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: str
    version: str
    type: ItemKind
    jurisdiction: list[Jurisdiction]
    priestley_area: str
    topics: list[str]
    difficulty: Difficulty
    marks: int = Field(gt=0)
    question_text: str
    gold_answer: str
    key_issues: list[str]
    required_authorities: list[Authority]
    rubric: list[RubricCriterion]
    law_as_at: str
    provenance: Provenance
    verification: Verification
    canary: str

    # MCQ-only fields.
    mcq_options: Optional[list[str]] = None
    mcq_correct: Optional[int] = None

    @field_validator("id")
    @classmethod
    def _id(cls, v: str) -> str:
        if not re.match(_ID_RE, v):
            raise ValueError(f"id must match {_ID_RE!r}, got {v!r}")
        return v

    @field_validator("version")
    @classmethod
    def _version(cls, v: str) -> str:
        if not re.match(_SEMVER_RE, v):
            raise ValueError(f"version must be semver X.Y.Z, got {v!r}")
        return v

    @field_validator("law_as_at")
    @classmethod
    def _law_as_at(cls, v: str) -> str:
        if not _is_iso_date(v):
            raise ValueError(f"law_as_at must be YYYY-MM-DD, got {v!r}")
        return v

    @field_validator("jurisdiction")
    @classmethod
    def _juris(cls, v: list[Jurisdiction]) -> list[Jurisdiction]:
        if not v:
            raise ValueError("jurisdiction must be non-empty")
        return v

    @field_validator("priestley_area")
    @classmethod
    def _area(cls, v: str) -> str:
        if v not in PRIESTLEY_AREAS:
            raise ValueError(f"priestley_area must be one of {sorted(PRIESTLEY_AREAS)}, got {v!r}")
        return v

    @field_validator("canary")
    @classmethod
    def _canary(cls, v: str) -> str:
        if not v.startswith("auslex:"):
            raise ValueError(f"canary must start with 'auslex:', got {v!r}")
        return v

    @model_validator(mode="after")
    def _cross_checks(self) -> "QuestionItem":
        rubric_total = sum(c.max for c in self.rubric)
        if rubric_total != self.marks:
            raise ValueError(
                f"rubric maxes must sum to marks ({self.marks}); got {rubric_total}"
            )
        if self.type == "mcq":
            if not self.mcq_options or self.mcq_correct is None:
                raise ValueError("mcq items require mcq_options and mcq_correct")
            if not (0 <= self.mcq_correct < len(self.mcq_options)):
                raise ValueError("mcq_correct out of range for mcq_options")
        if not self.question_text.strip():
            raise ValueError("question_text cannot be empty")
        if not self.gold_answer.strip():
            raise ValueError("gold_answer cannot be empty")
        return self

    @property
    def rubric_total(self) -> int:
        return sum(c.max for c in self.rubric)

    def to_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


def validate_item(data: dict[str, Any]) -> QuestionItem:
    """Validate a raw dict into a ``QuestionItem`` with a clearer error on failure."""
    from pydantic import ValidationError

    try:
        return QuestionItem.model_validate(data)
    except ValidationError as exc:
        item_id = data.get("id", "<unknown>")
        lines = [f"schema error in item {item_id}:"]
        for err in exc.errors():
            loc = ".".join(str(part) for part in err.get("loc", []))
            lines.append(f"  - {loc}: {err.get('msg')}")
        raise ValueError("\n".join(lines)) from None
