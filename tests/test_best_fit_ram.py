from cloud_scheduler.domain.cluster import Cluster
from cloud_scheduler.domain.job import Job
from cloud_scheduler.domain.server import Server
from cloud_scheduler.schedulers.best_fit_ram import BestFitRamScheduler


def test_cpu_tie_is_resolved_by_remaining_memory() -> None:
    cluster = Cluster()

    roomy_server = Server(
        server_id="roomy",
        total_cpu=4,
        total_memory_gb=12.0,
    )

    tight_server = Server(
        server_id="tight",
        total_cpu=4,
        total_memory_gb=8.0,
    )

    cluster.add_server(roomy_server)
    cluster.add_server(tight_server)

    job = Job(
        job_id="job-1",
        required_cpu=4,
        required_memory_gb=2.0,
        duration_steps=2,
    )

    scheduler = BestFitRamScheduler()

    selected = scheduler.select_server(cluster, job)

    # CPU eşit; daha az boş RAM bırakacak sunucu seçilmeli.
    assert selected is tight_server

    # Seçim yapmak kaynak ayırmamalı.
    assert tight_server.available_cpu == 4
    assert job.assigned_server_id is None


def test_cpu_score_has_priority_over_memory_score() -> None:
    cluster = Cluster()

    cpu_fit = Server(
        server_id="cpu-fit",
        total_cpu=4,
        total_memory_gb=16.0,
    )

    memory_fit = Server(
        server_id="memory-fit",
        total_cpu=8,
        total_memory_gb=2.0,
    )

    cluster.add_server(cpu_fit)
    cluster.add_server(memory_fit)

    job = Job(
        job_id="job-1",
        required_cpu=4,
        required_memory_gb=2.0,
        duration_steps=2,
    )

    scheduler = BestFitRamScheduler()

    selected = scheduler.select_server(cluster, job)

    # RAM'e yalnızca CPU değerleri eşit olduğunda bakılmalı.
    assert selected is cpu_fit