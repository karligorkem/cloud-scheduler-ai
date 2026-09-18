import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATABASE_PATH = PROJECT_ROOT / "data" / "scheduler.sqlite3"


def connect_database() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DATABASE_PATH, timeout=10)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database() -> None:
    with connect_database() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS experiments (
                id TEXT PRIMARY KEY,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                algorithm TEXT NOT NULL,
                seed INTEGER NOT NULL,
                current_step INTEGER NOT NULL,
                decision_count INTEGER NOT NULL,
                completed_count INTEGER NOT NULL,
                total_jobs INTEGER NOT NULL,
                terminated INTEGER NOT NULL,
                truncated INTEGER NOT NULL,
                state_json TEXT NOT NULL
            )
            """
        )


def save_experiment(experiment_id: str, state: dict) -> None:
    """Deneyin son durumunu, bütün geçmişiyle birlikte kaydeder."""
    now = datetime.now(timezone.utc).isoformat()

    state_json = json.dumps(
        state,
        ensure_ascii=False,
        allow_nan=False,
    )

    with connect_database() as connection:
        connection.execute(
            """
            INSERT INTO experiments (
                id,
                created_at,
                updated_at,
                algorithm,
                seed,
                current_step,
                decision_count,
                completed_count,
                total_jobs,
                terminated,
                truncated,
                state_json
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                updated_at = excluded.updated_at,
                algorithm = excluded.algorithm,
                seed = excluded.seed,
                current_step = excluded.current_step,
                decision_count = excluded.decision_count,
                completed_count = excluded.completed_count,
                total_jobs = excluded.total_jobs,
                terminated = excluded.terminated,
                truncated = excluded.truncated,
                state_json = excluded.state_json
            """,
            (
                experiment_id,
                now,
                now,
                state["algorithm"],
                state["seed"],
                state["current_step"],
                state["decision_count"],
                state["completed_count"],
                state["total_jobs"],
                int(state["terminated"]),
                int(state["truncated"]),
                state_json,
            ),
        )


def list_experiments(limit: int = 50) -> list[dict]:
    with connect_database() as connection:
        rows = connection.execute(
            """
            SELECT
                id,
                created_at,
                updated_at,
                algorithm,
                seed,
                current_step,
                decision_count,
                completed_count,
                total_jobs,
                terminated,
                truncated
            FROM experiments
            ORDER BY created_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    experiments = []

    for row in rows:
        experiment = dict(row)
        experiment["terminated"] = bool(experiment["terminated"])
        experiment["truncated"] = bool(experiment["truncated"])
        experiments.append(experiment)

    return experiments


def get_experiment(experiment_id: str) -> dict | None:
    with connect_database() as connection:
        row = connection.execute(
            """
            SELECT id, created_at, updated_at, state_json
            FROM experiments
            WHERE id = ?
            """,
            (experiment_id,),
        ).fetchone()

    if row is None:
        return None

    return {
        "id": row["id"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "state": json.loads(row["state_json"]),
    }