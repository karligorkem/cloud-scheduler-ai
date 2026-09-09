from cloud_scheduler.domain.cluster import Cluster
from cloud_scheduler.domain.job import Job
from cloud_scheduler.domain.job_queue import JobQueue
from cloud_scheduler.schedulers.first_fit import FirstFitScheduler


class Simulation:
    """Görevlerin yerleştirilmesini ve zamanın ilerlemesini yönetir."""

    def __init__(
        self,
        cluster: Cluster,
        queue: JobQueue,
        scheduler: FirstFitScheduler,
    ) -> None:
        self.cluster = cluster
        self.queue = queue
        self.scheduler = scheduler

        # Simülasyon boyunca tamamlanan görevleri biriktirir.
        self.completed_jobs: list[Job] = []

    def is_finished(self) -> bool:
        """Bekleyen veya çalışan görev kalmadıysa True döndürür."""

        # Kuyrukta görev varsa simülasyon henüz bitmemiştir.
        if self.queue.peek() is not None:
            return False

        # Herhangi bir sunucuda çalışan görev varsa devam etmeliyiz.
        for server in self.cluster.servers:
            if server.running_jobs:
                return False

        return True

    def step(self) -> list[Job]:
        """Görevleri yerleştirir ve simülasyonu bir zaman adımı ilerletir."""

        # Bitmiş simülasyonda zamanı ilerletme.
        if self.is_finished():
            return []

        # Sıradaki görev yerleşebildiği sürece yeni görev başlat.
        while self.scheduler.schedule_next(self.cluster, self.queue):
            pass

        # Bütün sunuculardaki çalışan görevleri bir adım ilerlet.
        completed_this_step = self.cluster.advance_time()

        # Bu adımda biten görevleri genel tamamlananlar listesine ekle.
        self.completed_jobs.extend(completed_this_step)

        return completed_this_step

    def run(self, max_steps: int = 100) -> list[Job]:
        """Simülasyonu bitene veya adım sınırına ulaşana kadar çalıştırır."""

        if max_steps <= 0:
            raise ValueError("Max steps must be greater than zero.")

        for _ in range(max_steps):
            if self.is_finished():
                break

            self.step()

        # İçeride tuttuğumuz listenin bir kopyasını döndür.
        return self.completed_jobs.copy()