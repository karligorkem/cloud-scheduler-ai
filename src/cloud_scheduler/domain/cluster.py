from cloud_scheduler.domain.job import Job
from cloud_scheduler.domain.server import Server


class Cluster:
    """Sunucuları ve kümenin simülasyon zamanını tutar."""

    def __init__(self) -> None:
        # Kümedeki sunucular.
        self.servers: list[Server] = []

        # Simülasyon sıfırıncı adımda başlar.
        self.current_step = 0

    def get_server(self, server_id: str) -> Server:
        """Kimliği verilen sunucuyu bulur."""

        searched_id = server_id.strip()

        for server in self.servers:
            if server.server_id == searched_id:
                return server

        raise ValueError("Server not found.")

    def add_server(self, server: Server) -> None:
        """Aynı kimlikte sunucu yoksa yeni sunucuyu ekler."""

        for existing_server in self.servers:
            if existing_server.server_id == server.server_id:
                raise ValueError("Server ID already exists.")

        self.servers.append(server)

    def advance_time(self) -> list[Job]:
        """Bütün sunucuları bir adım ilerletip biten görevleri döndürür."""

        completed_jobs: list[Job] = []

        for server in self.servers:
            server_completed_jobs = server.advance_time()

            for job in server_completed_jobs:
                completed_jobs.append(job)

        # Bütün sunucular ilerledikten sonra kümenin saatini artır.
        self.current_step = self.current_step + 1

        return completed_jobs