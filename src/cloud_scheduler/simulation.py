from cloud_scheduler.domain.cluster import Cluster
from cloud_scheduler.domain.job import Job
from cloud_scheduler.domain.job_queue import JobQueue
from cloud_scheduler.metrics import ResourceSnapshot, measure_resources
from cloud_scheduler.schedulers.base import Scheduler


class Simulation:
    """Görevlerin gelişini, yerleştirilmesini ve zamanı yönetir."""

    def __init__(
        self,
        cluster: Cluster,
        queue: JobQueue,
        scheduler: Scheduler,
        pending_jobs: list[Job] | None = None,
    ) -> None:
        self.cluster = cluster
        self.queue = queue
        self.scheduler = scheduler

        # Simülasyon boyunca tamamlanan görevler.
        self.completed_jobs: list[Job] = []

        # Her zaman adımındaki kaynak kullanım kayıtları.
        self.resource_history: list[ResourceSnapshot] = []

        # Henüz kuyruğa alınmamış görevleri geliş zamanına göre sırala.
        if pending_jobs is None:
            self.pending_jobs: list[Job] = []
        else:
            self.pending_jobs = sorted(
                pending_jobs,
                key=lambda job: job.arrival_step,
            )

    def admit_arrivals(self) -> None:
        """Geliş zamanı gelen görevleri bekleme kuyruğuna ekler."""

        while self.pending_jobs:
            next_job = self.pending_jobs[0]

            # Liste sıralı olduğu için ilk görevin zamanı gelmediyse dur.
            if next_job.arrival_step > self.cluster.current_step:
                break

            # Kuyruğa ekleme başarılı olduktan sonra listeden çıkar.
            self.queue.add(next_job)
            self.pending_jobs.pop(0)

    def is_finished(self) -> bool:
        """Gelecek, bekleyen veya çalışan görev kalmadıysa True döndürür."""

        if self.pending_jobs:
            return False

        if self.queue.peek() is not None:
            return False

        for server in self.cluster.servers:
            if server.running_jobs:
                return False

        return True

    def advance_one_step(self) -> list[Job]:
        """Otomatik görev atamadan kaynakları ölçer ve zamanı ilerletir."""

        if self.is_finished():
            return []

        # Görevler kaynaklarını bırakmadan önce kullanım ölçümünü al.
        snapshot = measure_resources(self.cluster)
        self.resource_history.append(snapshot)

        # Çalışan görevleri ve ortak saati bir adım ilerlet.
        completed_jobs = self.cluster.advance_time()

        # Bu adımda biten görevleri geçmişe ekle.
        self.completed_jobs.extend(completed_jobs)

        return completed_jobs

    def step(self) -> list[Job]:
        """Kural tabanlı zamanlayıcıyla bir zaman adımı çalıştırır."""

        if self.is_finished():
            return []

        # Önce bu zamanda gelen görevleri kabul et.
        self.admit_arrivals()

        # Yerleştirilebildiği sürece sıradaki görevi başlat.
        while self.scheduler.schedule_next(self.cluster, self.queue):
            pass

        # Atamalar tamamlandı; ölçüm al ve zamanı ilerlet.
        return self.advance_one_step()

    def run(self, max_steps: int = 100) -> list[Job]:
        """En fazla belirtilen sayıda ek zaman adımı çalıştırır."""

        if max_steps <= 0:
            raise ValueError("Max steps must be greater than zero.")

        for _ in range(max_steps):
            if self.is_finished():
                break

            self.step()

        # İç listeyi doğrudan vermek yerine bir kopyasını döndür.
        return self.completed_jobs.copy()