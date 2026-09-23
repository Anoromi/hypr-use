from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Task:
    id: str
    tier: str
    app: str
    seed: str
    prompt: str
    max_steps: int
    budget_usd: float
    grader: dict[str, Any]
    oracle: list[dict[str, Any]]
    distractors: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    requires: tuple[str, ...] = ()
    setup_apps: tuple[str, ...] = ()

    @property
    def oracle_steps(self) -> int:
        return len(self.oracle)


def load_tasks(path: Path | None = None) -> list[Task]:
    raw = json.loads((path or ROOT / "tasks.json").read_text())
    return [Task(**{**row, "distractors": tuple(row.get("distractors", ())), "tags": tuple(row.get("tags", ())), "requires": tuple(row.get("requires", ())), "setup_apps": tuple(row.get("setup_apps", ()))}) for row in raw]


def dump_tasks(tasks: list[Task], path: Path) -> None:
    path.write_text(json.dumps([asdict(task) for task in tasks], indent=2) + "\n")


def select(tasks: list[Task], tiers: set[str] | None, ids: set[str] | None) -> list[Task]:
    return [t for t in tasks if (not tiers or t.tier in tiers) and (not ids or t.id in ids)]
