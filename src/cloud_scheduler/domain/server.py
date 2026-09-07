class Server:
    """Represents a physical or virtual server in the cloud cluster."""

    def __init__(
        self,
        server_id: str,
        total_cpu: int,
        total_memory_gb: float,
        gpu_count: int = 0,
    ) -> None:
        # Sunucu kimliği boş bırakılamaz.
        if not server_id.strip():
            raise ValueError("Server ID cannot be empty.")

        # Sunucuda en az bir CPU bulunmalıdır.
        if total_cpu <= 0:
            raise ValueError("Total CPU must be greater than zero.")

        # Sunucunun RAM miktarı sıfırdan büyük olmalıdır.
        if total_memory_gb <= 0:
            raise ValueError("Total memory must be greater than zero.")

        # GPU bulunmayabilir ancak GPU sayısı negatif olamaz.
        if gpu_count < 0:
            raise ValueError("GPU count cannot be negative.")

        # Sunucunun temel bilgileri.
        self.server_id = server_id.strip()

        # Toplam ve kullanılabilir CPU miktarı.
        self.total_cpu = total_cpu
        self.available_cpu = total_cpu

        # Toplam ve kullanılabilir RAM miktarı.
        self.total_memory_gb = total_memory_gb
        self.available_memory_gb = total_memory_gb

        # Toplam ve kullanılabilir GPU sayısı.
        self.gpu_count = gpu_count
        self.available_gpu_count = gpu_count

        # Sunucu ilk oluşturulduğunda aktif durumdadır.
        self.is_active = True