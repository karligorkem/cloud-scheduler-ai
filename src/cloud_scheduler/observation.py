from dataclasses import dataclass

from cloud_scheduler.domain.cluster import Cluster
from cloud_scheduler.domain.job_queue import JobQueue


@dataclass(frozen=True)
class ServerObservation:
    """Bir sunucunun karar anındaki boş kaynakları."""

    server_id: str
    is_active: bool
    available_cpu: int
    available_memory_gb: float
    available_gpu_count: int


@dataclass(frozen=True)
class JobObservation:
    """Kuyruğun başındaki görevin karar için gerekli bilgileri."""

    job_id: str
    required_cpu: int
    required_memory_gb: float
    required_gpu_count: int
    waiting_steps: int


@dataclass(frozen=True)
class SchedulerObservation:
    """Zamanlayıcının karar verirken görebileceği sistem durumu."""

    current_step: int
    queue_length: int
    servers: tuple[ServerObservation, ...]
    next_job: JobObservation | None


def build_observation(
    cluster: Cluster,
    queue: JobQueue,
) -> SchedulerObservation:
    """Sistemi değiştirmeden mevcut durumun bir kaydını oluşturur."""

    server_observations: list[ServerObservation] = []

    for server in cluster.servers:
        server_observation = ServerObservation(
            server_id=server.server_id,
            is_active=server.is_active,
            available_cpu=server.available_cpu,
            available_memory_gb=server.available_memory_gb,
            available_gpu_count=server.available_gpu_count,
        )

        server_observations.append(server_observation)

    job = queue.peek()
    next_job = None

    if job is not None:
        next_job = JobObservation(
            job_id=job.job_id,
            required_cpu=job.required_cpu,
            required_memory_gb=job.required_memory_gb,
            required_gpu_count=job.required_gpu_count,
            waiting_steps=cluster.current_step - job.arrival_step,
        )

    return SchedulerObservation(
        current_step=cluster.current_step,
        queue_length=len(queue.jobs),
        servers=tuple(server_observations),
        next_job=next_job,
    )