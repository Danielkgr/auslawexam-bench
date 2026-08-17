"""Shared issue/report types for the ingestion + validation pipeline."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class Issue:
    """One finding from a lint/filter/validation pass."""

    level: str  # "error" | "warning" | "info"
    code: str
    message: str
    item_id: Optional[str] = None

    def render(self) -> str:
        where = f"[{self.item_id}] " if self.item_id else ""
        return f"{where}{self.level.upper():7s} {self.code}: {self.message}"


@dataclass
class Report:
    """Aggregated issues plus a convenience ``ok`` flag (no errors)."""

    issues: list[Issue] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)

    def add(self, issue: Issue) -> None:
        self.issues.append(issue)

    @property
    def errors(self) -> list[Issue]:
        return [i for i in self.issues if i.level == "error"]

    @property
    def warnings(self) -> list[Issue]:
        return [i for i in self.issues if i.level == "warning"]

    @property
    def ok(self) -> bool:
        return not self.errors

    def as_list(self) -> list[dict[str, Any]]:
        return [i.__dict__ for i in self.issues]
