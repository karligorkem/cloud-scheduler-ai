from cloud_scheduler.domain.job import Job, JobStatus


class JobQueue:
    """Bekleyen görevleri geliş sırasına göre tutar."""

    def __init__(self) -> None:
        self.jobs: list[Job] = []

    def add(self, job: Job) -> None:
        """Bekleyen ve atanmamış bir görevi kuyruğa ekler."""

        if job.status != JobStatus.WAITING:
            raise ValueError("Only waiting jobs can be queued.")

        if job.assigned_server_id is not None:
            raise ValueError("Assigned jobs cannot be queued.")

        for existing_job in self.jobs:
            if existing_job.job_id == job.job_id:
                raise ValueError("Job ID already exists in queue.")

        self.jobs.append(job)

    def peek(self) -> Job | None:
        """İlk görevi kuyruktan çıkarmadan döndürür."""

        if not self.jobs:
            return None

        return self.jobs[0]

    def pop_next(self) -> Job | None:
        """İlk görevi kuyruktan çıkarıp döndürür."""

        if not self.jobs:
            return None

        return self.jobs.pop(0)