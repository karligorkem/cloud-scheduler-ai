from cloud_scheduler.domain.cluster import Cluster
from cloud_scheduler.domain.job import Job
from cloud_scheduler.domain.job_queue import JobQueue
from cloud_scheduler.schedulers.base import Scheduler
from cloud_scheduler.metrics import ResourceSnapshot, measure_resources


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

        self.completed_jobs: list[Job] = []
                # Her çalışma aralığı için bir kaynak ölçümü tutar.
        self.resource_history: list[ResourceSnapshot] = []

        # Gelecekte gelecek görevleri geliş zamanına göre sırala.
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

            # İlk görevin bile zamanı gelmediyse sonraki görevler bekler.
            if next_job.arrival_step > self.cluster.current_step:
                break

            # Önce kuyruğa ekle; başarılıysa gelecek görevlerden çıkar.
            self.queue.add(next_job)
            self.pending_jobs.pop(0)

    def is_finished(self) -> bool:
        """Gelecek, bekleyen veya çalışan görev kalmadığını kontrol eder."""

        if self.pending_jobs:
            return False

        if self.queue.peek() is not None:
            return False

        for server in self.cluster.servers:
            if server.running_jobs:
                return False

        return True

    def step(self) -> list[Job]:
        """Görevleri kabul eder, kaynakları ölçer ve zamanı ilerletir."""

        if self.is_finished():
            return []

        self.admit_arrivals()

        while self.scheduler.schedule_next(self.cluster, self.queue):
            pass

        # Atamalar yapıldıktan sonra, görevler tamamlanmadan önce ölç.
        snapshot = measure_resources(self.cluster)
        self.resource_history.append(snapshot)

        completed_this_step = self.cluster.advance_time()

        self.completed_jobs.extend(completed_this_step)

        return completed_this_step

    def run(self, max_steps: int = 100) -> list[Job]:
        """En fazla belirtilen sayıda ek zaman adımı çalıştırır."""

        if max_steps <= 0:
            raise ValueError("Max steps must be greater than zero.")

        for _ in range(max_steps):
            if self.is_finished():
                break

            self.step()

        return self.completed_jobs.copy()