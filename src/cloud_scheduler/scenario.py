from cloud_scheduler.domain.cluster import Cluster
from cloud_scheduler.domain.job_queue import JobQueue
from cloud_scheduler.domain.server import Server
from cloud_scheduler.scenario_config import ScenarioConfig
from cloud_scheduler.schedulers.first_fit import FirstFitScheduler
from cloud_scheduler.simulation import Simulation
from cloud_scheduler.workload import generate_jobs


def create_simulation(
    seed: int,
    config: ScenarioConfig | None = None,
) -> Simulation:
    """Verilen ayarlarla yeni sunucular ve görevler oluşturur."""

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

    jobs = generate_jobs(
        count=config.job_count,
        seed=seed,
        max_arrival_step=config.max_arrival_step,
    )

    return Simulation(
        cluster=cluster,
        queue=JobQueue(),
        scheduler=FirstFitScheduler(),
        pending_jobs=jobs,
    )