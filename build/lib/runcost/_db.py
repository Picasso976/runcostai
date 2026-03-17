from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from typing import List, Optional, Tuple


@dataclass(frozen=True)
class CallRow:
    id: int
    ts: str
    model: str
    prompt_tokens: int
    completion_tokens: int
    cost_usd: float


class DbLogger:
    def __init__(self, path: str):
        self._path = path
        self._init()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._path)

    def _init(self) -> None:
        conn = self._connect()
        try:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS calls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts TEXT NOT NULL,
                    model TEXT NOT NULL,
                    prompt_tokens INTEGER NOT NULL,
                    completion_tokens INTEGER NOT NULL,
                    cost_usd REAL NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_calls_cost ON calls(cost_usd DESC);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_calls_ts ON calls(ts);")
            conn.commit()
        finally:
            conn.close()

    def insert_call(
        self,
        *,
        ts: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        cost_usd: float,
    ) -> None:
        conn = self._connect()
        try:
            conn.execute(
                "INSERT INTO calls(ts, model, prompt_tokens, completion_tokens, cost_usd) VALUES(?,?,?,?,?)",
                (ts, model, int(prompt_tokens), int(completion_tokens), float(cost_usd)),
            )
            conn.commit()
        finally:
            conn.close()

    def total_spend_usd(self) -> float:
        conn = self._connect()
        try:
            row = conn.execute("SELECT COALESCE(SUM(cost_usd), 0.0) FROM calls").fetchone()
            return float(row[0] if row else 0.0)
        finally:
            conn.close()

    def total_calls(self) -> int:
        conn = self._connect()
        try:
            row = conn.execute("SELECT COUNT(*) FROM calls").fetchone()
            return int(row[0] if row else 0)
        finally:
            conn.close()

    def top_expensive(self, limit: int = 5) -> List[CallRow]:
        conn = self._connect()
        try:
            rows = conn.execute(
                "SELECT id, ts, model, prompt_tokens, completion_tokens, cost_usd "
                "FROM calls ORDER BY cost_usd DESC, id DESC LIMIT ?",
                (int(limit),),
            ).fetchall()
        finally:
            conn.close()
        return [
            CallRow(
                id=int(r[0]),
                ts=str(r[1]),
                model=str(r[2]),
                prompt_tokens=int(r[3]),
                completion_tokens=int(r[4]),
                cost_usd=float(r[5]),
            )
            for r in rows
        ]

