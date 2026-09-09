from cloud_scheduler.domain.cluster import Cluster
from cloud_scheduler.domain.job import Job
from cloud_scheduler.domain.job_queue import JobQueue
from cloud_scheduler.domain.server import Server


class FirstFitScheduler:
    """Görevi kabul edebilen ilk sunucuyu seçer."""

    def select_server(self, cluster: Cluster, job: Job) -> Server | None:
        """Uygun sunucuyu bulur; görev veya kaynakları değiştirmez."""

        for server in cluster.servers:
            if server.can_host(job):
                return server

        return None

    def schedule_next(self, cluster: Cluster, queue: JobQueue) -> bool:
        """Kuyruğun ilk görevini mümkünse başlatır."""

        job = queue.peek()

        # Kuyruk boşsa başlatılacak görev yoktur.
        if job is None:
            return False

        selected_server = self.select_server(cluster, job)

        # Uygun sunucu yoksa görev kuyrukta beklemeye devam eder.
        if selected_server is None:
            return False

        # Önce görevi başlat, başarılı olunca kuyruktan çıkar.
        selected_server.allocate(job)
        queue.pop_next()

        return True