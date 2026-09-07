class Server:
    """Represents a physical or virtual server in the cloud cluster."""

    def __init__(
        self,
        server_id: str,
        total_cpu: int,
        total_memory_gb: float,
        gpu_count: int = 0,
    ) -> None:
        self.server_id = server_id

        self.total_cpu = total_cpu
        self.available_cpu = total_cpu

        self.total_memory_gb = total_memory_gb
        self.available_memory_gb = total_memory_gb

        self.gpu_count = gpu_count
        self.available_gpu_count = gpu_count

        self.is_active = True