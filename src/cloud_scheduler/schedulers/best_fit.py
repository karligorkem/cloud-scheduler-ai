from cloud_scheduler.domain.cluster import Cluster
from cloud_scheduler.domain.job import Job
from cloud_scheduler.domain.job_queue import JobQueue
from cloud_scheduler.domain.server import Server


class BestFitScheduler:
    """Görevi, yerleştirme sonrası en az boş CPU kalacak sunucuya atar."""

    def select_server(
        self,
        cluster: Cluster,
        job: Job,
    ) -> Server | None:
        selected_server: Server | None = None
        smallest_remaining_cpu: int | None = None

        for server in cluster.servers:
            # Kaynakları veya durumu uygun olmayan sunucuyu atla.
            if not server.can_host(job):
                continue

            remaining_cpu = server.available_cpu - job.required_cpu

            # İlk uygun sunucuyu başlangıç adayı olarak seç.
            if smallest_remaining_cpu is None:
                selected_server = server
                smallest_remaining_cpu = remaining_cpu

            # Daha az boş CPU bırakacak bir sunucu bulduysak seçimi değiştir.
            elif remaining_cpu < smallest_remaining_cpu:
                selected_server = server
                smallest_remaining_cpu = remaining_cpu

        return selected_server

    def schedule_next(
        self,
        cluster: Cluster,
        queue: JobQueue,
    ) -> bool:
        """Kuyruğun başındaki görevi seçilen sunucuda başlatır."""

        job = queue.peek()

        if job is None:
            return False

        selected_server = self.select_server(cluster, job)

        if selected_server is None:
            return False

        selected_server.allocate(job)
        job.started_step = cluster.current_step
        queue.pop_next()

        return True