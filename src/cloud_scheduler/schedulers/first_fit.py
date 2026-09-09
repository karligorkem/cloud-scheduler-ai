from cloud_scheduler.domain.cluster import Cluster
from cloud_scheduler.domain.job import Job
from cloud_scheduler.domain.job_queue import JobQueue
from cloud_scheduler.domain.server import Server


class FirstFitScheduler:
    """Görevi listedeki ilk uygun sunucuya yerleştirir."""

    def select_server(
        self,
        cluster: Cluster,
        job: Job,
    ) -> Server | None:
        """Görevi kabul edebilen ilk sunucuyu bulur."""

        for server in cluster.servers:
            if server.can_host(job):
                return server

        return None

    def schedule_next(
        self,
        cluster: Cluster,
        queue: JobQueue,
    ) -> bool:
        """Kuyruğun başındaki görevi uygun sunucuda başlatır."""

        job = queue.peek()

        if job is None:
            return False

        selected_server = self.select_server(cluster, job)

        if selected_server is None:
            return False

        # Önce kaynakları ayır ve görevi başlat.
        selected_server.allocate(job)

        # Başarılı atamanın gerçekleştiği zamanı kaydet.
        job.started_step = cluster.current_step

        # Başlayan görevi bekleme kuyruğundan çıkar.
        queue.pop_next()

        return True