import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFAULT_DB_PATH = Path(__file__).resolve().parent / ".data" / "event_plans.sqlite3"


@dataclass(frozen=True)
class EventPlan:
    id: int
    name: str
    data: dict[str, Any]
    updated_at: str


class EventPlanStore:
    def __init__(self, database_path: str | Path = DEFAULT_DB_PATH) -> None:
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path)
        connection.row_factory = sqlite3.Row
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS event_plans (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    data TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def list_plans(self) -> tuple[EventPlan, ...]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT id, name, data, updated_at FROM event_plans "
                "ORDER BY updated_at DESC, name ASC"
            ).fetchall()
        return tuple(
            EventPlan(
                id=row["id"],
                name=row["name"],
                data=json.loads(row["data"]),
                updated_at=row["updated_at"],
            )
            for row in rows
        )

    def save(self, name: str, data: dict[str, Any]) -> int:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Enter an event name before saving.")
        payload = json.dumps(data, ensure_ascii=False)
        with self._connect() as connection:
            existing = connection.execute(
                "SELECT id FROM event_plans WHERE name = ?",
                (clean_name,),
            ).fetchone()
            if existing:
                plan_id = int(existing["id"])
                connection.execute(
                    "UPDATE event_plans SET data = ?, updated_at = datetime('now') "
                    "WHERE id = ?",
                    (payload, plan_id),
                )
            else:
                cursor = connection.execute(
                    "INSERT INTO event_plans (name, data, updated_at) "
                    "VALUES (?, ?, datetime('now'))",
                    (clean_name, payload),
                )
                plan_id = int(cursor.lastrowid)
        return plan_id

    def get(self, plan_id: int) -> EventPlan:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id, name, data, updated_at FROM event_plans WHERE id = ?",
                (plan_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"Event plan {plan_id} does not exist.")
        return EventPlan(
            id=row["id"],
            name=row["name"],
            data=json.loads(row["data"]),
            updated_at=row["updated_at"],
        )

    def delete(self, plan_id: int) -> None:
        with self._connect() as connection:
            connection.execute("DELETE FROM event_plans WHERE id = ?", (plan_id,))


def plan_checklist_progress(plan: EventPlan) -> tuple[int, int]:
    checklist = plan.data.get("checklist", {})
    if not isinstance(checklist, dict):
        return 0, 0
    total = len(checklist)
    completed = sum(bool(value) for value in checklist.values())
    return completed, total


def plan_handover_status(plan: EventPlan) -> str:
    owner = str(plan.data.get("safety_owner", "")).strip()
    next_check = str(plan.data.get("next_check", "")).strip()
    note = str(plan.data.get("handover_note", "")).strip()
    if owner and next_check:
        return "Handover ready"
    if owner or next_check or note:
        return "Needs handover details"
    return "Not handed over"
