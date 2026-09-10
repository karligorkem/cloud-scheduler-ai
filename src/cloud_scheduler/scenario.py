from cloud_scheduler.domain.cluster import Cluster
from cloud_scheduler.domain.job_queue import JobQueue
from cloud_scheduler.domain.server import Server
from cloud_scheduler.schedulers.first_fit import FirstFitScheduler
from cloud_scheduler.simulation import Simulation
from cloud_scheduler.workload import generate_jobs


def create_simulation(seed: int) -> Simulation:
    """Her çağrıda yeni sunucular ve görevlerle bir deney oluşturur."""

    cluster = Cluster()

    cluster.add_server(
        Server(
            server_id="large-server",
            total_cpu=8,
            total_memory_gb=16.0,
        )
    )

    cluster.add_server(
        Server(
            server_id="small-server",
            total_cpu=4,
            total_memory_gb=8.0,
        )
    )

    jobs = generate_jobs(
        count=20,
        seed=seed,
        max_arrival_step=10,
    )

    return Simulation(
        cluster=cluster,
        queue=JobQueue(),
        scheduler=FirstFitScheduler(),
        pending_jobs=jobs,
    )