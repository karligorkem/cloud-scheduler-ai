from cloud_scheduler.domain.job import Job
from cloud_scheduler.domain.job_queue import JobQueue
from cloud_scheduler.queue_encoder import encode_queue_preview


def test_queue_preview_pads_missing_jobs_without_changing_queue() -> None:
    queue = JobQueue()

    job = Job(
        job_id="job-1",
        required_cpu=4,
        required_memory_gb=8.0,
        duration_steps=3,
    )

    queue.add(job)

    result = encode_queue_preview(queue)

    # İlk görev kodlanır, eksik iki görev sıfırlarla doldurulur.
    assert result == (
        1.0, 0.5, 0.5, 0.0,
        0.0, 0.0, 0.0, 0.0,
        0.0, 0.0, 0.0, 0.0,
    )

    # Gözlem oluşturmak kuyruğu değiştirmemeli.
    assert len(queue.jobs) == 1
    assert queue.peek() is job
    assert job.remaining_steps == 3
    assert job.assigned_server_id is None


def test_queue_preview_preserves_order_and_limits_visible_jobs() -> None:
    queue = JobQueue()

    for index, cpu in enumerate([1, 2, 4, 8]):
        job = Job(
            job_id=f"job-{index + 1}",
            required_cpu=cpu,
            required_memory_gb=4.0,
            duration_steps=2,
        )

        queue.add(job)

    # Döngü bittikten sonra kuyruğun ilk üç görevini kodla.
    result = encode_queue_preview(queue)

    assert result == (
        1.0, 0.125, 0.25, 0.0,
        1.0, 0.250, 0.25, 0.0,
        1.0, 0.500, 0.25, 0.0,
    )

    # Dördüncü görev gözleme alınmaz ama kuyrukta kalır.
    assert len(queue.jobs) == 4