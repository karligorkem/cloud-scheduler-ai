from dataclasses import dataclass
from typing import Sequence

from cloud_scheduler.domain.cluster import Cluster
from cloud_scheduler.domain.job import Job
from cloud_scheduler.domain.job_queue import JobQueue
from cloud_scheduler.domain.server import Server
from cloud_scheduler.scenario_config import ScenarioConfig
from cloud_scheduler.schedulers.first_fit import FirstFitScheduler
from cloud_scheduler.simulation import Simulation
from cloud_scheduler.workload import generate_jobs


@dataclass(frozen=True, slots=True)
class JobDefinition:
    job_id: str
    required_cpu: int
    required_memory_gb: float
    duration_steps: int
    required_gpu_count: int = 0
    arrival_step: int = 0


def create_jobs_from_definitions(
    definitions: Sequence[JobDefinition],
) -> list[Job]:
    jobs = [
        Job(
            job_id=definition.job_id,
            required_cpu=definition.required_cpu,
            required_memory_gb=definition.required_memory_gb,
            duration_steps=definition.duration_steps,
            required_gpu_count=definition.required_gpu_count,
            arrival_step=definition.arrival_step,
        )
        for definition in definitions
    ]

    return sorted(
        jobs,
        key=lambda job: job.arrival_step,
    )


def create_simulation(
    seed: int,
    config: ScenarioConfig | None = None,
    job_definitions: Sequence[JobDefinition] | None = None,
) -> Simulation:
    """Sentetik veya elle girilmiş görevlerle simülasyon oluşturur."""

    if config is None:
        config = ScenarioConfig()

    cluster = Cluster()

    cluster.add_server(
        Server(
            server_id="large-server",
            total_cpu=config.large_server_cpu,
            total_memory_gb=config.large_server_memory_gb,
        )
    )

    cluster.add_server(
        Server(
            server_id="small-server",
            total_cpu=config.small_server_cpu,
            total_memory_gb=config.small_server_memory_gb,
        )
    )

    if job_definitions is None:
        jobs = generate_jobs(
            count=config.job_count,
            seed=seed,
            max_arrival_step=config.max_arrival_step,
        )
    else:
        jobs = create_jobs_from_definitions(job_definitions)

    return Simulation(
        cluster=cluster,
        queue=JobQueue(),
        scheduler=FirstFitScheduler(),
        pending_jobs=jobs,
    )