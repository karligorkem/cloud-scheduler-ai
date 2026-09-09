from enum import Enum


class JobStatus(str, Enum):
    """Possible states of a job."""

    WAITING = "waiting"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Job:
    """Represents a job waiting to run in the cloud cluster."""

    def __init__(
        self,
        job_id: str,
        required_cpu: int,
        required_memory_gb: float,
        duration_steps: int,
        priority: int = 1,
        required_gpu_count: int = 0,
    ) -> None:
        if not job_id.strip():
            raise ValueError("Job ID cannot be empty.")

        # Görevin en az bir CPU istemesi gerekir.
        if required_cpu <= 0:
            raise ValueError("Required CPU must be greater than zero.")

        # Görevin RAM ihtiyacı sıfırdan büyük olmalıdır.
        if required_memory_gb <= 0:
            raise ValueError("Required memory must be greater than zero.")

        # Görev en az bir simülasyon adımı çalışmalıdır.
        if duration_steps <= 0:
            raise ValueError("Duration steps must be greater than zero.")

        # Öncelik 1 ile 5 arasında olmalıdır.
        if priority < 1 or priority > 5:
            raise ValueError("Priority must be between 1 and 5.")

        # GPU gerekmeyebilir ancak negatif GPU istenemez.
        if required_gpu_count < 0:
            raise ValueError("Required GPU count cannot be negative.")

        # Görevin temel kimliği.
        self.job_id = job_id.strip()
        

        self.required_cpu = required_cpu
        self.required_memory_gb = required_memory_gb
        self.required_gpu_count = required_gpu_count

        self.duration_steps = duration_steps
        self.remaining_steps = duration_steps

        self.priority = priority
        self.status = JobStatus.WAITING

        self.assigned_server_id: str | None = None