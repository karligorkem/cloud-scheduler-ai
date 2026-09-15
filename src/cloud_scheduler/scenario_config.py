from dataclasses import dataclass


@dataclass(frozen=True)
class ScenarioConfig:
    """Bir deneyin görev ve sunucu ayarlarını tutar."""

    job_count: int = 20
    max_arrival_step: int = 10

    large_server_cpu: int = 8
    large_server_memory_gb: float = 16.0

    small_server_cpu: int = 4
    small_server_memory_gb: float = 8.0

    def __post_init__(self) -> None:
        """Ayar nesnesi oluşturulduktan sonra değerleri kontrol eder."""

        if self.job_count <= 0:
            raise ValueError("Job count must be greater than zero.")

        if self.max_arrival_step < 0:
            raise ValueError("Max arrival step cannot be negative.")

        if self.large_server_cpu <= 0 or self.small_server_cpu <= 0:
            raise ValueError("Server CPU must be greater than zero.")

        if (
            self.large_server_memory_gb <= 0
            or self.small_server_memory_gb <= 0
        ):
            raise ValueError("Server memory must be greater than zero.")