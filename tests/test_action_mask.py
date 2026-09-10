from cloud_scheduler.action_mask import build_action_mask
from cloud_scheduler.domain.cluster import Cluster
from cloud_scheduler.domain.job import Job
from cloud_scheduler.domain.job_queue import JobQueue
from cloud_scheduler.domain.server import Server


def test_mask_rejects_insufficient_and_inactive_servers() -> None:
    cluster = Cluster()

    suitable_server = Server(
        server_id="suitable",
        total_cpu=4,
        total_memory_gb=8.0,
    )

    insufficient_server = Server(
        server_id="insufficient",
        total_cpu=1,
        total_memory_gb=8.0,
    )

    inactive_server = Server(
        server_id="inactive",
        total_cpu=4,
        total_memory_gb=8.0,
    )

    inactive_server.is_active = False

    cluster.add_server(suitable_server)
    cluster.add_server(insufficient_server)
    cluster.add_server(inactive_server)

    job = Job(
        job_id="job-1",
        required_cpu=2,
        required_memory_gb=4.0,
        duration_steps=3,
    )

    queue = JobQueue()
    queue.add(job)

    mask = build_action_mask(cluster, queue)

    # Uygun sunucu, yetersiz sunucu, kapalı sunucu, bekleme.
    assert mask == (True, False, False, True)

    # Maske oluşturmak görevi başlatmamalı.
    assert suitable_server.available_cpu == 4
    assert queue.peek() is job
    assert job.assigned_server_id is None


def test_empty_queue_allows_only_waiting() -> None:
    cluster = Cluster()

    cluster.add_server(
        Server(
            server_id="server-1",
            total_cpu=4,
            total_memory_gb=8.0,
        )
    )

    queue = JobQueue()

    mask = build_action_mask(cluster, queue)

    # Görev yoksa sunucuya atama yapılamaz; beklenebilir.
    assert mask == (False, True)