from __future__ import annotations

import sqlite3
from pathlib import Path

from app.core.config import DB_PATH


def get_connection() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_connection() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS games (
                game_id TEXT PRIMARY KEY,
                player_name TEXT NOT NULL,
                max_rounds INTEGER NOT NULL,
                current_round INTEGER NOT NULL,
                status TEXT NOT NULL,
                phase TEXT NOT NULL,
                winner TEXT,
                state_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS participants (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id TEXT NOT NULL,
                participant_id TEXT NOT NULL,
                name TEXT NOT NULL,
                is_human INTEGER NOT NULL,
                hidden_objective TEXT NOT NULL,
                traits_json TEXT NOT NULL,
                eliminated_round INTEGER,
                UNIQUE(game_id, participant_id)
            );

            CREATE TABLE IF NOT EXISTS round_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                game_id TEXT NOT NULL,
                round_number INTEGER NOT NULL,
                event TEXT NOT NULL,
                player_action_json TEXT NOT NULL,
                ai_actions_json TEXT NOT NULL,
                votes_json TEXT NOT NULL,
                eliminated_id TEXT,
                summary_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS analytics_snapshots (
                game_id TEXT PRIMARY KEY,
                analytics_json TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
