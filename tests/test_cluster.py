import pytest
from cloud_scheduler.domain.job import Job, JobStatus

from cloud_scheduler.domain.cluster import Cluster
from cloud_scheduler.domain.server import Server


def test_cluster_adds_and_finds_server() -> None:
    cluster = Cluster()

    server = Server(
        server_id="server-1",
        total_cpu=8,
        total_memory_gb=16.0,
    )

    cluster.add_server(server)

    found_server = cluster.get_server("server-1")

    assert len(cluster.servers) == 1
    assert found_server is server


def test_cluster_rejects_duplicate_server_id() -> None:
    cluster = Cluster()

    first_server = Server(
        server_id="server-1",
        total_cpu=8,
        total_memory_gb=16.0,
    )

    second_server = Server(
        server_id="server-1",
        total_cpu=16,
        total_memory_gb=32.0,
    )

    cluster.add_server(first_server)

    with pytest.raises(ValueError, match="Server ID already exists"):
        cluster.add_server(second_server)

    assert len(cluster.servers) == 1
    assert cluster.get_server("server-1") is first_server


def test_cluster_rejects_unknown_server_id() -> None:
    cluster = Cluster()

    server = Server(
        server_id="server-1",
        total_cpu=8,
        total_memory_gb=16.0,
    )

    cluster.add_server(server)

    with pytest.raises(ValueError, match="Server not found"):
        cluster.get_server("server-99")

def test_cluster_advances_all_servers_by_one_step() -> None:
    cluster = Cluster()

    first_server = Server(
        server_id="server-1",
        total_cpu=8,
        total_memory_gb=16.0,
    )

    second_server = Server(
        server_id="server-2",
        total_cpu=8,
        total_memory_gb=16.0,
    )

    cluster.add_server(first_server)
    cluster.add_server(second_server)

    short_job = Job(
        job_id="short-job",
        required_cpu=2,
        required_memory_gb=4.0,
        duration_steps=1,
    )

    long_job = Job(
        job_id="long-job",
        required_cpu=2,
        required_memory_gb=4.0,
        duration_steps=2,
    )

    first_server.allocate(short_job)
    second_server.allocate(long_job)

    # İki sunucu olsa da zaman yalnızca bir adım ilerlemeli.
    first_completed_jobs = cluster.advance_time()

    assert cluster.current_step == 1

    # Bir adımlık görev tamamlanmalı.
    assert short_job.status == JobStatus.COMPLETED
    assert first_completed_jobs == [short_job]
    assert first_server.available_cpu == 8

    # İki adımlık görevin bir adımı kalmalı.
    assert long_job.status == JobStatus.RUNNING
    assert long_job.remaining_steps == 1
    assert second_server.available_cpu == 6

    # İkinci adımda uzun görev de tamamlanmalı.
    second_completed_jobs = cluster.advance_time()

    assert cluster.current_step == 2
    assert second_completed_jobs == [long_job]
    assert long_job.status == JobStatus.COMPLETED
    assert second_server.available_cpu == 8

    assert first_server.running_jobs == []
    assert second_server.running_jobs == []

def test_empty_cluster_can_advance_time() -> None:
    cluster = Cluster()

    completed_jobs = cluster.advance_time()

    assert cluster.current_step == 1
    assert completed_jobs == []