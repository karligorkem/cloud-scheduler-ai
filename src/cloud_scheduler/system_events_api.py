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

def select_workload_events(limit: int) -> list[dict]:
    """Farklı önem seviyelerinden dengeli olaylar seçer."""

    candidate_limit = max(200, limit * 20)
    candidates = list_saved_events(candidate_limit, None)

    buckets: dict[int, list[dict]] = {
        1: [],
        2: [],
        3: [],
        4: [],
    }

    for event in candidates:
        level_number = event.get("level_number")

        if level_number in (1, 2, 3):
            bucket = int(level_number)
        else:
            bucket = 4

        buckets[bucket].append(event)

    selected: list[dict] = []

    while len(selected) < limit:
        event_added = False

        # Critical, Error, Warning ve Information sırasıyla seçilir.
        for level_number in (1, 2, 3, 4):
            if len(selected) >= limit:
                break

            if buckets[level_number]:
                selected.append(
                    buckets[level_number].pop(0)
                )
                event_added = True

        if not event_added:
            break

    # Simülasyona en eski seçilen olay önce girsin.
    selected.sort(
        key=lambda event: str(event.get("time_created") or "")
    )

    return selected


def calculate_job_requirements(
    event: dict,
) -> tuple[int, float, int]:
    """
    Windows olayını sentetik kaynak ihtiyacına dönüştürür.

    Bunlar gerçek işlem CPU/RAM ölçümleri değildir. Event ID, kayıt
    numarası ve önem seviyesi kullanılarak tekrarlanabilir bir
    simülasyon yükü oluşturulur.
    """

    event_id = int(event.get("event_id") or 0)
    record_id = int(event.get("record_id") or 0)
    level_number = event.get("level_number")

    signature = abs(
        (event_id * 31) + (record_id * 17)
    )

    if level_number == 1:
        # Critical: large-server kapasitesinin tamamına yakın yük.
        required_cpu = 8
        required_memory_gb = 16.0
        duration_steps = 8 + (signature % 3)

    elif level_number == 2:
        # Error: yüksek kaynak ihtiyacı.
        load_band = signature % 3

        required_cpu = 4 + load_band
        required_memory_gb = float(8 + (load_band * 2))
        duration_steps = 6 + (signature % 4)

    elif level_number == 3:
        # Warning: orta düzey kaynak ihtiyacı.
        load_band = signature % 3

        required_cpu = 2 + load_band
        required_memory_gb = float(4 + (load_band * 2))
        duration_steps = 4 + (signature % 4)

    else:
        # Information: aynı seviyedeki olaylar da birbirinden farklı olsun.
        load_band = signature % 4

        required_cpu = 1 + load_band
        required_memory_gb = float(2 + (load_band * 2))
        duration_steps = 3 + (signature % 5)

    return (
        required_cpu,
        required_memory_gb,
        duration_steps,
    )


@router.get("/workload")
def create_workload_from_events(
    limit: int = Query(default=20, ge=1, le=100),
) -> dict:
    """Windows olaylarından simülasyon iş yükü oluşturur."""

    selected_events = select_workload_events(limit)

    if not selected_events:
        raise HTTPException(
            status_code=404,
            detail=(
                "Kaydedilmis Windows olayi bulunamadi. "
                "Once olaylari toplayin."
            ),
        )

    jobs = []

    for index, event in enumerate(selected_events):
        (
            required_cpu,
            required_memory_gb,
            duration_steps,
        ) = calculate_job_requirements(event)

        log_prefix = (
            str(event["log_name"])
            .lower()
            .replace(" ", "-")
        )

        jobs.append(
            {
                "job_id": (
                    f"{log_prefix}-"
                    f"event-{event['event_id']}-"
                    f"{event['record_id']}"
                ),
                "required_cpu": required_cpu,
                "required_memory_gb": required_memory_gb,
                "duration_steps": duration_steps,
                "required_gpu_count": 0,

                # Her adımda dört göreve kadar geliş sağlayarak
                # kaynak rekabeti ve bekleme kuyruğu oluştur.
                "arrival_step": index // 4,

                "source_event": {
                    "identity": event["identity"],
                    "event_id": event["event_id"],
                    "record_id": event["record_id"],
                    "provider": event["provider"],
                    "level": event["level"],
                    "level_number": event["level_number"],
                    "log_name": event["log_name"],
                    "time_created": event["time_created"],
                },
            }
        )

    level_distribution: dict[str, int] = {
        "critical": 0,
        "error": 0,
        "warning": 0,
        "information": 0,
    }

    for event in selected_events:
        level_number = event.get("level_number")

        if level_number == 1:
            level_distribution["critical"] += 1
        elif level_number == 2:
            level_distribution["error"] += 1
        elif level_number == 3:
            level_distribution["warning"] += 1
        else:
            level_distribution["information"] += 1

    return {
        "source": "windows_event_log",
        "event_count": len(selected_events),
        "job_count": len(jobs),
        "selection": "balanced_by_event_level",
        "level_distribution": level_distribution,
        "mapping_notice": (
            "CPU, RAM ve sure degerleri Event ID ve olay "
            "seviyesinden uretilen simulasyon degerleridir; "
            "gercek Windows kaynak olcumleri degildir."
        ),
        "jobs": jobs,
    }

initialize_system_events()
