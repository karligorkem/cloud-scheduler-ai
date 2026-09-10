from cloud_scheduler.domain.cluster import Cluster
from cloud_scheduler.domain.job import Job
from cloud_scheduler.domain.job_queue import JobQueue
from cloud_scheduler.domain.server import Server
from cloud_scheduler.observation import build_observation
from cloud_scheduler.reward import calculate_reward


def test_wait_penalty_matches_number_of_queued_jobs() -> None:
    cluster = Cluster()

    cluster.add_server(
        Server(
            server_id="server-1",
            total_cpu=4,
            total_memory_gb=8.0,
        )
    )

    queue = JobQueue()

    for index in range(3):
        queue.add(
            Job(
                job_id=f"job-{index + 1}",
                required_cpu=1,
                required_memory_gb=1.0,
                duration_steps=2,
            )
        )

    observation = build_observation(cluster, queue)

    # Bir sunucu var: 0 atama, 1 bekleme.
    assert calculate_reward(observation, action=1) == -3.0

    # Atama zamanı ilerletmediği için bekleme maliyeti oluşturmaz.
    assert calculate_reward(observation, action=0) == 0.0


def test_wait_with_empty_queue_has_no_waiting_penalty() -> None:
    cluster = Cluster()
    queue = JobQueue()

    observation = build_observation(cluster, queue)

    # Sunucu yok: tek eylem olan beklemenin indeksi 0.
    assert calculate_reward(observation, action=0) == 0.0