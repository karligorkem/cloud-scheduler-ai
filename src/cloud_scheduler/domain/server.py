from cloud_scheduler.domain.job import Job, JobStatus


class Server:
    """Bulut kümesindeki bir sunucuyu temsil eder."""

    def __init__(
        self,
        server_id: str,
        total_cpu: int,
        total_memory_gb: float,
        gpu_count: int = 0,
    ) -> None:
        # Sunucu bilgilerini doğrula.
        if not server_id.strip():
            raise ValueError("Server ID cannot be empty.")

        if total_cpu <= 0:
            raise ValueError("Total CPU must be greater than zero.")

        if total_memory_gb <= 0:
            raise ValueError("Total memory must be greater than zero.")

        if gpu_count < 0:
            raise ValueError("GPU count cannot be negative.")

        # Sunucu kimliğini kaydet.
        self.server_id = server_id.strip()

        # Başlangıçta bütün kaynaklar kullanılabilir.
        self.total_cpu = total_cpu
        self.available_cpu = total_cpu

        self.total_memory_gb = total_memory_gb
        self.available_memory_gb = total_memory_gb

        self.gpu_count = gpu_count
        self.available_gpu_count = gpu_count

        # Sunucu aktif ve çalışan görev listesi boş olarak başlar.
        self.is_active = True
        self.running_jobs: list[Job] = []

    def can_host(self, job: Job) -> bool:
        """Görevin bu sunucuda başlatılıp başlatılamayacağını kontrol eder."""

        # Kapalı sunucu görev kabul edemez.
        if not self.is_active:
            return False

        # Görev henüz başlamamış ve atanmamış olmalıdır.
        if job.status != JobStatus.WAITING:
            return False

        if job.assigned_server_id is not None:
            return False

        # Kullanılabilir kaynaklar yeterli olmalıdır.
        if self.available_cpu < job.required_cpu:
            return False

        if self.available_memory_gb < job.required_memory_gb:
            return False

        if self.available_gpu_count < job.required_gpu_count:
            return False

        return True

    def allocate(self, job: Job) -> None:
        """Göreve kaynak ayırır ve görevi bu sunucuda başlatır."""

        # Kontroller başarısızsa hiçbir değeri değiştirmeden dur.
        if not self.can_host(job):
            raise ValueError("Server cannot host this job.")

        # Göreve ayrılan kaynakları boş kaynaklardan düş.
        self.available_cpu = self.available_cpu - job.required_cpu

        self.available_memory_gb = (
            self.available_memory_gb - job.required_memory_gb
        )

        self.available_gpu_count = (
            self.available_gpu_count - job.required_gpu_count
        )

        # Görevi sunucuya bağla ve başlat.
        job.assigned_server_id = self.server_id
        job.status = JobStatus.RUNNING

        # Çalışan görevi takip et.
        self.running_jobs.append(job)

    def advance_time(self) -> list[Job]:
        """Görevleri bir adım ilerletir ve tamamlanan görevleri döndürür."""

        completed_jobs: list[Job] = []

        # Önce bütün çalışan görevlerin kalan süresini azalt.
        for job in self.running_jobs:
            job.remaining_steps = job.remaining_steps - 1

            if job.remaining_steps == 0:
                completed_jobs.append(job)

        # Ardından tamamlanan görevlerin kaynaklarını geri bırak.
        for job in completed_jobs:
            self.available_cpu = self.available_cpu + job.required_cpu

            self.available_memory_gb = (
                self.available_memory_gb + job.required_memory_gb
            )

            self.available_gpu_count = (
                self.available_gpu_count + job.required_gpu_count
            )

            # Görevi tamamlandı olarak işaretle.
            job.status = JobStatus.COMPLETED

            # Artık çalışmadığı için listeden çıkar.
            self.running_jobs.remove(job)

        return completed_jobs