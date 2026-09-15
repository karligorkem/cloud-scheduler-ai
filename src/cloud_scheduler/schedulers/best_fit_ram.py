from cloud_scheduler.domain.cluster import Cluster
from cloud_scheduler.domain.job import Job
from cloud_scheduler.domain.server import Server
from cloud_scheduler.schedulers.best_fit import BestFitScheduler


class BestFitRamScheduler(BestFitScheduler):
    """CPU eşitliğinde kalan RAM miktarına göre sunucu seçer."""

    def select_server(
        self,
        cluster: Cluster,
        job: Job,
    ) -> Server | None:
        selected_server: Server | None = None
        best_score: tuple[int, float] | None = None

        for server in cluster.servers:
            if not server.can_host(job):
                continue

            remaining_cpu = server.available_cpu - job.required_cpu

            remaining_memory = (
                server.available_memory_gb - job.required_memory_gb
            )

            score = (remaining_cpu, remaining_memory)

            if best_score is None or score < best_score:
                selected_server = server
                best_score = score

        return selected_server