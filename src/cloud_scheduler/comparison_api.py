from pathlib import Path

import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sb3_contrib import MaskablePPO

from cloud_scheduler.gym_environment import CloudSchedulerEnv
from cloud_scheduler.queue_gym_environment import QueueAwareCloudSchedulerEnv
from cloud_scheduler.schedulers.first_fit import FirstFitScheduler
from cloud_scheduler.schedulers.best_fit import BestFitScheduler
from cloud_scheduler.schedulers.best_fit_ram import BestFitRamScheduler


router = APIRouter(
    prefix="/api",
    tags=["Comparison"],
)

# Dosyanın konumundan proje ana klasörünü bul.
project_root = Path(__file__).resolve().parents[2]

model_paths = {
    "PPO": project_root / "outputs/ppo_long_run/scheduler_ppo.zip",
    "PPO Queue": project_root / "outputs/ppo_queue_run/scheduler_ppo.zip",
}


class ComparisonRequest(BaseModel):
    seed: int = Field(
        default=42,
        ge=0,
        le=2**31 - 1,
    )


def evaluate_method(
    algorithm: str,
    seed: int,
    models: dict[str, MaskablePPO],
) -> dict:
    """Bir yöntemi bağımsız bir simülasyonda değerlendirir."""

    if algorithm == "PPO Queue":
        environment = QueueAwareCloudSchedulerEnv(max_decisions=2000)
    else:
        environment = CloudSchedulerEnv(max_decisions=2000)

    schedulers = {
        "First Fit": FirstFitScheduler(),
        "Best Fit": BestFitScheduler(),
        "Best Fit RAM": BestFitRamScheduler(),
    }

    try:
        observation, info = environment.reset(seed=seed)
        workload_seed = info["episode_seed"]

        # Modelin giriş ve çıkış boyutlarını doğrula.
        if algorithm in models:
            model = models[algorithm]

            if (
                model.observation_space.shape
                != environment.observation_space.shape
                or model.action_space.n != environment.action_space.n
            ):
                raise ValueError(
                    f"{algorithm}: model ve ortam uyumsuz."
                )

        total_reward = 0.0

        while True:
            simulation = environment.environment.simulation
            servers = simulation.cluster.servers

            # Varsayılan eylem: bekle.
            action = len(servers)

            if algorithm in models:
                prediction, _ = models[algorithm].predict(
                    observation,
                    action_masks=environment.action_masks(),
                    deterministic=True,
                )

                action = int(np.asarray(prediction).item())

            else:
                job = simulation.queue.peek()

                if job is not None:
                    selected_server = schedulers[algorithm].select_server(
                        simulation.cluster,
                        job,
                    )

                    if selected_server is not None:
                        action = next(
                            index
                            for index, server in enumerate(servers)
                            if server.server_id == selected_server.server_id
                        )

            (
                observation,
                reward,
                terminated,
                truncated,
                _,
            ) = environment.step(action)

            total_reward += float(reward)

            if terminated or truncated:
                break

        simulation = environment.environment.simulation
        completed_jobs = simulation.completed_jobs

        finished = (
            terminated
            and not truncated
            and len(completed_jobs) == environment.config.job_count
        )

        average_waiting = None

        if finished:
            waiting_times = []

            for job in completed_jobs:
                waiting = job.waiting_steps

                if waiting is None:
                    raise ValueError(
                        "Tamamlanan gorevin bekleme suresi eksik."
                    )

                waiting_times.append(waiting)

            total_waiting = sum(waiting_times)

            if not np.isclose(total_reward, -total_waiting):
                raise ValueError(
                    "Odul ve toplam bekleme uyusmuyor."
                )

            average_waiting = total_waiting / len(completed_jobs)

        return {
            "algorithm": algorithm,
            "workload_seed": workload_seed,
            "completed_count": len(completed_jobs),
            "job_count": environment.config.job_count,
            "finished": finished,
            "truncated": truncated,
            "elapsed_steps": simulation.cluster.current_step,
            "decision_count": environment.environment.decision_count,
            "total_reward": total_reward,
            "average_waiting": average_waiting,
        }

    finally:
        environment.close()


@router.post("/compare")
def compare_algorithms(request: ComparisonRequest) -> dict:
    """Beş yöntemi aynı seed ile karşılaştırır."""

    # Eksik model varsa deneyleri başlatmadan hata ver.
    for name, path in model_paths.items():
        if not path.is_file():
            raise HTTPException(
                status_code=404,
                detail=(
                    f"{name} model dosyasi bulunamadi: "
                    f"{path.parent.name}/{path.name}"
                ),
            )

    try:
        models: dict[str, MaskablePPO] = {}

        for name, path in model_paths.items():
            models[name] = MaskablePPO.load(
                str(path),
                device="cpu",
            )

        methods = [
            "First Fit",
            "Best Fit",
            "Best Fit RAM",
            "PPO",
            "PPO Queue",
        ]

        results = [
            evaluate_method(
                algorithm=method,
                seed=request.seed,
                models=models,
            )
            for method in methods
        ]

        # Bütün yöntemler aynı görev üretim seed'ini kullanmalı.
        workload_seeds = {
            row["workload_seed"]
            for row in results
        }

        if len(workload_seeds) != 1:
            raise ValueError(
                "Yontemler farkli gorev seed'leri kullandi."
            )

        baseline = results[0]["average_waiting"]

        for row in results:
            waiting = row["average_waiting"]
            improvement = None

            if (
                baseline is not None
                and baseline > 0
                and waiting is not None
            ):
                improvement = (
                    100 * (baseline - waiting) / baseline
                )

            row["improvement_percent"] = improvement

        return {
            "seed": request.seed,
            "workload_seed": results[0]["workload_seed"],
            "results": results,
        }

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Karsilastirma tamamlanamadi: {exc}",
        ) from exc