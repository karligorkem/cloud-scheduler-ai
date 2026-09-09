from cloud_scheduler.domain.job import JobStatus
from cloud_scheduler.workload import generate_jobs


def test_same_seed_produces_same_job_requirements() -> None:
    first_jobs = generate_jobs(count=10, seed=42)
    second_jobs = generate_jobs(count=10, seed=42)

    assert len(first_jobs) == 10
    assert len(second_jobs) == 10

    for first_job, second_job in zip(first_jobs, second_jobs):
        assert first_job.job_id == second_job.job_id
        assert first_job.required_cpu == second_job.required_cpu
        assert first_job.required_memory_gb == second_job.required_memory_gb
        assert first_job.duration_steps == second_job.duration_steps

        # Özellikler aynı olsa da nesneler ayrı olmalı.
        assert first_job is not second_job


def test_generated_workloads_do_not_share_job_state() -> None:
    first_jobs = generate_jobs(count=3, seed=42)

    # İlk deneyde bir görevin başladığını varsay.
    first_jobs[0].status = JobStatus.RUNNING
    first_jobs[0].remaining_steps = 0
    first_jobs[0].assigned_server_id = "server-1"

    # Aynı özelliklerle ikinci deneyin görevlerini oluştur.
    second_jobs = generate_jobs(count=3, seed=42)

    # İlk deneydeki değişiklikler yeni görevlere taşınmamalı.
    assert second_jobs[0].status == JobStatus.WAITING
    assert second_jobs[0].assigned_server_id is None
    assert second_jobs[0].remaining_steps == second_jobs[0].duration_steps