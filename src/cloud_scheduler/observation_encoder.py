from cloud_scheduler.observation import SchedulerObservation


class ObservationEncoder:
    """Sistem gözlemini ölçeklendirilmiş sayı listesine dönüştürür."""

    def __init__(
        self,
        server_count: int,
        cpu_scale: float = 8.0,
        memory_scale: float = 16.0,
        gpu_scale: float = 1.0,
        queue_scale: float = 20.0,
        waiting_scale: float = 100.0,
    ) -> None:
        if server_count < 0:
            raise ValueError("Server count cannot be negative.")

        scales = [
            cpu_scale,
            memory_scale,
            gpu_scale,
            queue_scale,
            waiting_scale,
        ]

        for scale in scales:
            if scale <= 0:
                raise ValueError("Scales must be greater than zero.")

        self.server_count = server_count
        self.cpu_scale = cpu_scale
        self.memory_scale = memory_scale
        self.gpu_scale = gpu_scale
        self.queue_scale = queue_scale
        self.waiting_scale = waiting_scale

    def encode(self, observation: SchedulerObservation) -> list[float]:
        """Her çağrıda aynı sırayla sayısal özellikler üretir."""

        if len(observation.servers) != self.server_count:
            raise ValueError("Observation server count does not match.")

        values: list[float] = []

        # Her sunucu için dört özellik ekle.
        for server in observation.servers:
            values.extend(
                [
                    float(server.is_active),
                    server.available_cpu / self.cpu_scale,
                    server.available_memory_gb / self.memory_scale,
                    server.available_gpu_count / self.gpu_scale,
                ]
            )

        # Kuyruk uzunluğunu ekle.
        values.append(observation.queue_length / self.queue_scale)

        job = observation.next_job

        if job is None:
            # Görev yoksa da vektörün uzunluğu aynı kalsın.
            values.extend([0.0, 0.0, 0.0, 0.0, 0.0])
        else:
            values.extend(
                [
                    1.0,
                    job.required_cpu / self.cpu_scale,
                    job.required_memory_gb / self.memory_scale,
                    job.required_gpu_count / self.gpu_scale,
                    job.waiting_steps / self.waiting_scale,
                ]
            )

        return values