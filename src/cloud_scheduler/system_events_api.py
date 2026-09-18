import json
import subprocess
from datetime import datetime, timezone
from threading import Lock

from fastapi import APIRouter, HTTPException, Query

from cloud_scheduler.storage import connect_database


router = APIRouter(
    prefix="/api/system-events",
    tags=["System Events"],
)

collection_lock = Lock()


def initialize_system_events() -> None:
    with connect_database() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS system_events (
                identity TEXT PRIMARY KEY,
                log_name TEXT NOT NULL,
                record_id INTEGER NOT NULL,
                event_id INTEGER NOT NULL,
                provider TEXT NOT NULL,
                level TEXT NOT NULL,
                level_number INTEGER,
                time_created TEXT NOT NULL,
                message TEXT NOT NULL,
                collected_at TEXT NOT NULL
            )
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
                idx_system_events_time
            ON system_events(time_created DESC)
            """
        )

        connection.execute(
            """
            CREATE INDEX IF NOT EXISTS
                idx_system_events_event_id
            ON system_events(event_id)
            """
        )


def read_windows_events(limit: int) -> list[dict]:
    """Windows System ve Application günlüklerinden son olayları okur."""

    powershell_script = f"""
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

$events = Get-WinEvent `
    -FilterHashtable @{{LogName=@('System','Application')}} `
    -MaxEvents {limit} `
    -ErrorAction Stop |
    ForEach-Object {{
        [PSCustomObject]@{{
            log_name = $_.LogName
            record_id = $_.RecordId
            event_id = $_.Id
            provider = $_.ProviderName
            level = $_.LevelDisplayName
            level_number = $_.Level
            time_created = $_.TimeCreated.ToUniversalTime().ToString('o')
            message = $_.Message
        }}
    }}

ConvertTo-Json -InputObject @($events) -Depth 4 -Compress
"""

    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)

    try:
        result = subprocess.run(
            [
                "powershell.exe",
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                powershell_script,
            ],
            capture_output=True,
            check=False,
            timeout=30,
            creationflags=creation_flags,
        )
    except FileNotFoundError as exc:
        raise RuntimeError(
            "Windows PowerShell bulunamadi."
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(
            "Windows olaylarini okuma zaman asimina ugradi."
        ) from exc

    stdout = result.stdout.decode(
        "utf-8-sig",
        errors="replace",
    ).strip()

    stderr = result.stderr.decode(
        "utf-8-sig",
        errors="replace",
    ).strip()

    if result.returncode != 0:
        raise RuntimeError(
            stderr or "Windows olaylari okunamadi."
        )

    if not stdout:
        return []

    try:
        parsed = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "PowerShell olay verisi JSON bicimine donusturulemedi."
        ) from exc

    if isinstance(parsed, dict):
        parsed = [parsed]

    events = []

    for item in parsed:
        record_id = item.get("record_id")
        log_name = str(item.get("log_name") or "Unknown")

        if record_id is None:
            continue

        events.append(
            {
                "identity": f"{log_name}:{int(record_id)}",
                "log_name": log_name,
                "record_id": int(record_id),
                "event_id": int(item.get("event_id") or 0),
                "provider": str(
                    item.get("provider") or "Unknown"
                ),
                "level": str(
                    item.get("level") or "Bilgi"
                ),
                "level_number": (
                    int(item["level_number"])
                    if item.get("level_number") is not None
                    else None
                ),
                "time_created": str(
                    item.get("time_created") or ""
                ),
                "message": str(
                    item.get("message") or
                    "Bu olay için açıklama bulunmuyor."
                ),
            }
        )

    return events


def save_windows_events(events: list[dict]) -> int:
    collected_at = datetime.now(timezone.utc).isoformat()

    with connect_database() as connection:
        connection.executemany(
            """
            INSERT INTO system_events (
                identity,
                log_name,
                record_id,
                event_id,
                provider,
                level,
                level_number,
                time_created,
                message,
                collected_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(identity) DO UPDATE SET
                event_id = excluded.event_id,
                provider = excluded.provider,
                level = excluded.level,
                level_number = excluded.level_number,
                time_created = excluded.time_created,
                message = excluded.message,
                collected_at = excluded.collected_at
            """,
            [
                (
                    event["identity"],
                    event["log_name"],
                    event["record_id"],
                    event["event_id"],
                    event["provider"],
                    event["level"],
                    event["level_number"],
                    event["time_created"],
                    event["message"],
                    collected_at,
                )
                for event in events
            ],
        )

    return len(events)


def list_saved_events(
    limit: int,
    event_id: int | None,
) -> list[dict]:
    sql = """
        SELECT
            identity,
            log_name,
            record_id,
            event_id,
            provider,
            level,
            level_number,
            time_created,
            message,
            collected_at
        FROM system_events
    """

    parameters: list[int] = []

    if event_id is not None:
        sql += " WHERE event_id = ?"
        parameters.append(event_id)

    sql += " ORDER BY time_created DESC LIMIT ?"
    parameters.append(limit)

    with connect_database() as connection:
        rows = connection.execute(
            sql,
            parameters,
        ).fetchall()

    return [dict(row) for row in rows]


@router.post("/collect")
def collect_system_events(
    limit: int = Query(default=50, ge=1, le=200),
) -> dict:
    """Windows günlüklerini okur ve SQLite'a kaydeder."""

    with collection_lock:
        try:
            events = read_windows_events(limit)
            saved_count = save_windows_events(events)
        except RuntimeError as exc:
            raise HTTPException(
                status_code=500,
                detail=str(exc),
            ) from exc

    return {
        "collected_count": len(events),
        "saved_count": saved_count,
        "events": list_saved_events(limit, None),
    }


@router.get("")
def get_system_events(
    limit: int = Query(default=50, ge=1, le=200),
    event_id: int | None = Query(default=None, ge=0),
) -> dict:
    """Daha önce SQLite'a kaydedilmiş olayları döndürür."""

    events = list_saved_events(limit, event_id)

    return {
        "count": len(events),
        "event_id_filter": event_id,
        "events": events,
    }


initialize_system_events()