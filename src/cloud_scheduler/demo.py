from cloud_scheduler.domain.cluster import Cluster
from cloud_scheduler.domain.job import Job
from cloud_scheduler.domain.job_queue import JobQueue
from cloud_scheduler.domain.server import Server
from cloud_scheduler.schedulers.first_fit import FirstFitScheduler


def main() -> None:
    # Sistemin temel parçalarını oluştur.
    cluster = Cluster()
    queue = JobQueue()
    scheduler = FirstFitScheduler()

    # Küçük bir sunucu oluştur ve kümeye ekle.
    server = Server(
        server_id="server-1",
        total_cpu=4,
        total_memory_gb=8.0,
    )

    cluster.add_server(server)

    # İlk görev sunucunun bütün kaynaklarını kullanacak.
    first_job = Job(
        job_id="job-1",
        required_cpu=4,
        required_memory_gb=8.0,
        duration_steps=2,
    )

    # İkinci görev, ilk görev tamamlanana kadar bekleyecek.
    second_job = Job(
        job_id="job-2",
        required_cpu=2,
        required_memory_gb=4.0,
        duration_steps=1,
    )

    queue.add(first_job)
    queue.add(second_job)

    max_steps = 10

    while cluster.current_step < max_steps:
        print(f"\nZaman: {cluster.current_step}")

        # Kaynaklar yettiği sürece sıradaki görevleri başlat.
        while True:
            next_job = queue.peek()

            if next_job is None:
                break

            started = scheduler.schedule_next(cluster, queue)

            if not started:
                print(f"Bekliyor: {next_job.job_id}")
                break

            print(
                f"Basladi: {next_job.job_id}"
                f" -> {next_job.assigned_server_id}"
            )

        # Bütün sunucularda bir zaman adımı geçir.
        completed_jobs = cluster.advance_time()

        for job in completed_jobs:
            print(
                f"Tamamlandi: {job.job_id}"
                f" | Zaman: {cluster.current_step}"
            )

        # Herhangi bir sunucuda çalışan görev kaldı mı?
        has_running_jobs = False

        for current_server in cluster.servers:
            if current_server.running_jobs:
                has_running_jobs = True
                break

        # Bekleyen ve çalışan görev yoksa demo bitmiştir.
        if queue.peek() is None and not has_running_jobs:
            print("\nButun gorevler tamamlandi.")
            return

    print("\nAdim sinirina ulasildi; tamamlanmamis gorevler var.")


if __name__ == "__main__":
    main()