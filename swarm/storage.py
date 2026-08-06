"""SQLite persistence for swarm runs, so every investigation is queryable later."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .models import SwarmRun

DEFAULT_DB_PATH = Path.home() / ".research_swarm" / "runs.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    topic TEXT NOT NULL,
    created_at REAL NOT NULL,
    total_elapsed_s REAL NOT NULL,
    payload_json TEXT NOT NULL
);
"""


class Storage:
    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.execute(SCHEMA)
        self._conn.commit()

    def save(self, run: SwarmRun) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO runs (run_id, topic, created_at, total_elapsed_s, payload_json) "
            "VALUES (?, ?, ?, ?, ?)",
            (
                run.run_id,
                run.topic,
                run.created_at,
                run.total_elapsed_s,
                run.model_dump_json(),
            ),
        )
        self._conn.commit()

    def get(self, run_id: str) -> SwarmRun | None:
        row = self._conn.execute(
            "SELECT payload_json FROM runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        if not row:
            return None
        return SwarmRun.model_validate(json.loads(row[0]))

    def list_runs(self, limit: int = 20) -> list[dict]:
        rows = self._conn.execute(
            "SELECT run_id, topic, created_at, total_elapsed_s FROM runs "
            "ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [
            {"run_id": r[0], "topic": r[1], "created_at": r[2], "total_elapsed_s": r[3]}
            for r in rows
        ]

    def close(self) -> None:
        self._conn.close()
