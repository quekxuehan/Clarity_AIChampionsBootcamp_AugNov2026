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
    owner_id: str | None = None


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
            columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(event_plans)").fetchall()
            }
            if "owner_id" not in columns:
                connection.execute("ALTER TABLE event_plans ADD COLUMN owner_id TEXT")
            connection.execute(
                "CREATE INDEX IF NOT EXISTS idx_event_plans_owner "
                "ON event_plans(owner_id)"
            )

    def list_plans(self, owner_id: str | None = None) -> tuple[EventPlan, ...]:
        with self._connect() as connection:
            if owner_id is None:
                rows = connection.execute(
                    "SELECT id, name, data, updated_at, owner_id FROM event_plans "
                    "ORDER BY updated_at DESC, name ASC"
                ).fetchall()
            else:
                rows = connection.execute(
                    "SELECT id, name, data, updated_at, owner_id FROM event_plans "
                    "WHERE owner_id = ? "
                    "ORDER BY updated_at DESC, name ASC",
                    (owner_id,),
                ).fetchall()
        return tuple(
            EventPlan(
                id=row["id"],
                name=row["name"],
                data=json.loads(row["data"]),
                updated_at=row["updated_at"],
                owner_id=row["owner_id"],
            )
            for row in rows
        )

    def save(self, name: str, data: dict[str, Any], owner_id: str | None = None) -> int:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Enter an event name before saving.")
        payload = json.dumps(data, ensure_ascii=False)
        with self._connect() as connection:
            if owner_id is None:
                existing = connection.execute(
                    "SELECT id FROM event_plans "
                    "WHERE name = ? AND owner_id IS NULL",
                    (clean_name,),
                ).fetchone()
            else:
                existing = connection.execute(
                    "SELECT id FROM event_plans WHERE name = ? AND owner_id = ?",
                    (clean_name, owner_id),
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
                    "INSERT INTO event_plans (name, data, updated_at, owner_id) "
                    "VALUES (?, ?, datetime('now'), ?)",
                    (clean_name, payload, owner_id),
                )
                plan_id = int(cursor.lastrowid)
        return plan_id

    def get(self, plan_id: int) -> EventPlan:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT id, name, data, updated_at, owner_id "
                "FROM event_plans WHERE id = ?",
                (plan_id,),
            ).fetchone()
        if row is None:
            raise KeyError(f"Event plan {plan_id} does not exist.")
        return EventPlan(
            id=row["id"],
            name=row["name"],
            data=json.loads(row["data"]),
            updated_at=row["updated_at"],
            owner_id=row["owner_id"],
        )

    def delete(self, plan_id: int, owner_id: str | None = None) -> None:
        with self._connect() as connection:
            if owner_id is None:
                connection.execute("DELETE FROM event_plans WHERE id = ?", (plan_id,))
            else:
                connection.execute(
                    "DELETE FROM event_plans WHERE id = ? AND owner_id = ?",
                    (plan_id, owner_id),
                )


def plan_checklist_progress(plan: EventPlan) -> tuple[int, int]:
    checklist_items = plan.data.get("checklist_items")
    if isinstance(checklist_items, list):
        total = len(checklist_items)
        completed = sum(
            bool(item.get("completed"))
            for item in checklist_items
            if isinstance(item, dict)
        )
        return completed, total
    checklist = plan.data.get("checklist", {})
    if not isinstance(checklist, dict):
        return 0, 0
    total = len(checklist)
    completed = sum(bool(value) for value in checklist.values())
    return completed, total


def plan_followup_status(plan: EventPlan) -> str:
    note = str(plan.data.get("handover_note", "")).strip()
    return "Notes added" if note else "No notes"
