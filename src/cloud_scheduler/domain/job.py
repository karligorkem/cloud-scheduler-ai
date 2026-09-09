from enum import Enum


class JobStatus(str, Enum):
    WAITING = "waiting"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Job:
    """Sunucuda çalıştırılacak bir görevi temsil eder."""

    def __init__(
        self,
        job_id: str,
        required_cpu: int,
        required_memory_gb: float,
        duration_steps: int,
        priority: int = 1,
        required_gpu_count: int = 0,
    ) -> None:
        # Geçersiz görev bilgilerini reddet.
        if not job_id.strip():
            raise ValueError("Job ID cannot be empty.")

        if required_cpu <= 0:
            raise ValueError("Required CPU must be greater than zero.")

        if required_memory_gb <= 0:
            raise ValueError("Required memory must be greater than zero.")

        if duration_steps <= 0:
            raise ValueError("Duration steps must be greater than zero.")

        if priority < 1 or priority > 5:
            raise ValueError("Priority must be between 1 and 5.")

        if required_gpu_count < 0:
            raise ValueError("Required GPU count cannot be negative.")

        # Kimlik ve kaynak ihtiyaçları.
        self.job_id = job_id.strip()
        self.required_cpu = required_cpu
        self.required_memory_gb = required_memory_gb
        self.required_gpu_count = required_gpu_count

        # Toplam çalışma süresi ve kalan çalışma süresi.
        self.duration_steps = duration_steps
        self.remaining_steps = duration_steps
        self.priority = priority

        # Görev başlangıçta kuyrukta bekler.
        self.status = JobStatus.WAITING
        self.assigned_server_id: str | None = None

        # Şimdilik bütün görevler sıfırıncı adımda gelir.
        self.arrival_step: int = 0

        # Başlama ve tamamlanma zamanları henüz belli değil.
        self.started_step: int | None = None
        self.completed_step: int | None = None

    @property
    def waiting_steps(self) -> int | None:
        """Görevin başlamadan önce beklediği süreyi hesaplar."""

        if self.started_step is None:
            return None

        return self.started_step - self.arrival_step

    @property
    def turnaround_steps(self) -> int | None:
        """Tamamlanan görevin sistemde geçirdiği süreyi hesaplar."""

        if self.completed_step is None:
            return None

        return self.completed_step - self.arrival_step