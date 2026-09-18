from pathlib import Path
from typing import Literal, Sequence

import numpy as np
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sb3_contrib import MaskablePPO

from cloud_scheduler.gym_environment import CloudSchedulerEnv
from cloud_scheduler.queue_gym_environment import (
    QueueAwareCloudSchedulerEnv,
)
from cloud_scheduler.scenario import JobDefinition
from cloud_scheduler.schedulers.best_fit import BestFitScheduler
from cloud_scheduler.schedulers.best_fit_ram import (
    BestFitRamScheduler,
)
from cloud_scheduler.schedulers.first_fit import FirstFitScheduler


router = APIRouter(
    prefix="/api",
    tags=["Comparison"],
)

AlgorithmName = Literal[
    "First Fit",
    "Best Fit",
    "Best Fit RAM",
    "PPO",
    "PPO Queue",
]

PROJECT_ROOT = Path(__file__).resolve().parents[2]

MODEL_PATHS = {
    "PPO": (
        PROJECT_ROOT
        / "outputs"
        / "ppo_long_run"
        / "scheduler_ppo.zip"
    ),
    "PPO Queue": (
        PROJECT_ROOT
        / "outputs"
        / "ppo_queue_run"
        / "scheduler_ppo.zip"
    ),
}

SCHEDULERS = {
    "First Fit": FirstFitScheduler(),
    "Best Fit": BestFitScheduler(),
    "Best Fit RAM": BestFitRamScheduler(),
}


class ComparisonJobRequest(BaseModel):
    job_id: str = Field(min_length=1, max_length=80)
    required_cpu: int = Field(ge=1, le=8)
    required_memory_gb: float = Field(gt=0, le=16)
    duration_steps: int = Field(ge=1, le=1000)
    required_gpu_count: int = Field(default=0, ge=0, le=0)
    arrival_step: int = Field(default=0, ge=0)


class ComparisonRequest(BaseModel):
    seed: int = Field(default=42, ge=0, le=2**31 - 1)
    jobs: list[ComparisonJobRequest] | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )


def convert_job_definitions(
    jobs: list[ComparisonJobRequest] | None,
) -> tuple[JobDefinition, ...] | None:
    if jobs is None:
        return None

    normalized_ids = [
        job.job_id.replace(" ", "").lower()
        for job in jobs
    ]

    if any(job_id == "" for job_id in normalized_ids):
        raise HTTPException(
            status_code=422,
            detail="Gorev kimligi bos olamaz.",
        )

    if len(normalized_ids) != len(set(normalized_ids)):
        raise HTTPException(
            status_code=422,
            detail="Gorev kimlikleri benzersiz olmali.",
        )

    return tuple(
        JobDefinition(
            job_id=job.job_id,
            required_cpu=job.required_cpu,
            required_memory_gb=job.required_memory_gb,
            duration_steps=job.duration_steps,
            required_gpu_count=job.required_gpu_count,
            arrival_step=job.arrival_step,
        )
        for job in jobs
    )


def choose_rule_action(
    algorithm: str,
    environment: CloudSchedulerEnv,
) -> int:
    simulation = environment.environment.simulation
    servers = simulation.cluster.servers
    wait_action = len(servers)

    job = simulation.queue.peek()

    if job is None:
        return wait_action

    selected_server = SCHEDULERS[algorithm].select_server(
        simulation.cluster,
        job,
    )

    if selected_server is None:
        return wait_action

    for index, server in enumerate(servers):
        if server.server_id == selected_server.server_id:
            return index

    raise RuntimeError(
        "Selected server is not in the cluster."
    )


def evaluate_method(
    algorithm: str,
    seed: int,
    models: dict[str, MaskablePPO],
    job_definitions: Sequence[JobDefinition] | None,
) -> dict:
    if algorithm == "PPO Queue":
        environment = QueueAwareCloudSchedulerEnv(
            max_decisions=2000,
            job_definitions=job_definitions,
        )
    else:
        environment = CloudSchedulerEnv(
            max_decisions=2000,
            job_definitions=job_definitions,
        )

    try:
        observation, info = environment.reset(seed=seed)

        if algorithm in models:
            model = models[algorithm]

            if (
                model.observation_space.shape
                != environment.observation_space.shape
            ):
                raise RuntimeError(
                    f"{algorithm} observation shape mismatch."
                )

            if (
                model.action_space.n
                != environment.action_space.n
            ):
                raise RuntimeError(
                    f"{algorithm} action count mismatch."
                )

        total_reward = 0.0
        terminated = False
        truncated = False

        while not terminated and not truncated:
            if algorithm in models:
                prediction, _ = models[algorithm].predict(
                    observation,
                    action_masks=environment.action_masks(),
                    deterministic=True,
                )

                action = int(
                    np.asarray(prediction).item()
                )
            else:
                action = choose_rule_action(
                    algorithm,
                    environment,
                )

            (
                observation,
                reward,
                terminated,
                truncated,
                _,
            ) = environment.step(action)

            total_reward += float(reward)

        simulation = environment.environment.simulation
        completed_jobs = simulation.completed_jobs

        finished = (
            terminated
            and not truncated
            and len(completed_jobs) == environment.job_count
        )

        waiting_times = [
            job.waiting_steps
            for job in completed_jobs
            if job.waiting_steps is not None
        ]

        average_waiting = None

        if finished and waiting_times:
            average_waiting = (
                sum(waiting_times) / len(waiting_times)
            )

            if not np.isclose(
                total_reward,
                -sum(waiting_times),
            ):
                raise RuntimeError(
                    f"{algorithm} reward and waiting mismatch."
                )

        return {
            "algorithm": algorithm,
            "workload_seed": info["episode_seed"],
            "completed_count": len(completed_jobs),
            "job_count": environment.job_count,
            "finished": finished,
            "truncated": truncated,
            "elapsed_steps": (
                simulation.cluster.current_step
            ),
            "decision_count": (
                environment.environment.decision_count
            ),
            "total_reward": total_reward,
            "average_waiting": average_waiting,
        }
    finally:
        environment.close()


@router.post("/compare")
def compare_algorithms(
    request: ComparisonRequest,
) -> dict:
    for algorithm, model_path in MODEL_PATHS.items():
        if not model_path.is_file():
            raise HTTPException(
                status_code=404,
                detail=(
                    f"{algorithm} model dosyasi "
                    f"bulunamadi: {model_path}"
                ),
            )

    job_definitions = convert_job_definitions(
        request.jobs
    )

    try:
        models = {
            algorithm: MaskablePPO.load(
                str(model_path),
                device="cpu",
            )
            for algorithm, model_path
            in MODEL_PATHS.items()
        }

        algorithms = [
            "First Fit",
            "Best Fit",
            "Best Fit RAM",
            "PPO",
            "PPO Queue",
        ]

        results = [
            evaluate_method(
                algorithm=algorithm,
                seed=request.seed,
                models=models,
                job_definitions=job_definitions,
            )
            for algorithm in algorithms
        ]

        workload_seeds = {
            result["workload_seed"]
            for result in results
        }

        if len(workload_seeds) != 1:
            raise RuntimeError(
                "Algorithms used different workload seeds."
            )

        first_fit_waiting = results[0][
            "average_waiting"
        ]

        for result in results:
            waiting = result["average_waiting"]

            if (
                first_fit_waiting is None
                or waiting is None
            ):
                result["improvement_percent"] = None
            elif first_fit_waiting == 0:
                result["improvement_percent"] = (
                    0.0 if waiting == 0 else None
                )
            else:
                result["improvement_percent"] = (
                    100.0
                    * (first_fit_waiting - waiting)
                    / first_fit_waiting
                )

        return {
            "seed": request.seed,
            "workload_seed": results[0][
                "workload_seed"
            ],
            "input_mode": (
                "manual"
                if job_definitions is not None
                else "synthetic"
            ),
            "job_count": (
                len(job_definitions)
                if job_definitions is not None
                else results[0]["job_count"]
            ),
            "results": results,
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Karsilastirma basarisiz: {exc}",
        ) from exc
    
class BenchmarkRequest(BaseModel):
    base_seed: int = Field(
        default=42,
        ge=0,
        le=2**31 - 1,
    )
    run_count: int = Field(
        default=10,
        ge=2,
        le=50,
    )
    jobs: list[ComparisonJobRequest] | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )


def create_run_seed(
    base_seed: int,
    run_index: int,
) -> int:
    """Her benchmark deneyi için tekrarlanabilir seed üretir."""

    maximum_seed = (2**31) - 1

    return (
        base_seed + (run_index * 7919)
    ) % maximum_seed


def create_manual_workload_variant(
    job_definitions: Sequence[JobDefinition],
    seed: int,
    run_index: int,
) -> tuple[JobDefinition, ...]:
    """
    Aynı görevleri korur fakat geliş sırasını değiştirir.

    İlk deney orijinal görev sırasını kullanır. Sonraki deneylerde
    CPU, RAM ve süre değerleri değişmez; yalnızca görevlerin geliş
    sırası seed kullanılarak yeniden düzenlenir.
    """

    original_jobs = tuple(job_definitions)

    if run_index == 0:
        return original_jobs

    random_generator = np.random.default_rng(seed)

    shuffled_indexes = random_generator.permutation(
        len(original_jobs)
    )

    arrival_steps = sorted(
        job.arrival_step
        for job in original_jobs
    )

    variants: list[JobDefinition] = []

    for position, shuffled_index in enumerate(
        shuffled_indexes
    ):
        original_job = original_jobs[
            int(shuffled_index)
        ]

        variants.append(
            JobDefinition(
                job_id=original_job.job_id,
                required_cpu=original_job.required_cpu,
                required_memory_gb=(
                    original_job.required_memory_gb
                ),
                duration_steps=(
                    original_job.duration_steps
                ),
                required_gpu_count=(
                    original_job.required_gpu_count
                ),
                arrival_step=arrival_steps[position],
            )
        )

    return tuple(variants)


def calculate_optional_mean(
    values: list[float],
) -> float | None:
    if not values:
        return None

    return float(np.mean(values))


def calculate_optional_standard_deviation(
    values: list[float],
) -> float | None:
    if not values:
        return None

    return float(np.std(values))


@router.post("/benchmark")
def benchmark_algorithms(
    request: BenchmarkRequest,
) -> dict:
    """
    Algoritmaları birden fazla senaryoda değerlendirir.

    Sentetik modda her deney farklı seed ile yeni görevler üretir.
    Manuel modda aynı görevlerin geliş sırası değiştirilir.
    """

    for algorithm, model_path in MODEL_PATHS.items():
        if not model_path.is_file():
            raise HTTPException(
                status_code=404,
                detail=(
                    f"{algorithm} model dosyasi "
                    f"bulunamadi: {model_path}"
                ),
            )

    base_job_definitions = convert_job_definitions(
        request.jobs
    )

    algorithms = [
        "First Fit",
        "Best Fit",
        "Best Fit RAM",
        "PPO",
        "PPO Queue",
    ]

    try:
        models = {
            algorithm: MaskablePPO.load(
                str(model_path),
                device="cpu",
            )
            for algorithm, model_path
            in MODEL_PATHS.items()
        }

        runs: list[dict] = []

        win_counts = {
            algorithm: 0
            for algorithm in algorithms
        }

        exclusive_win_counts = {
            algorithm: 0
            for algorithm in algorithms
        }

        for run_index in range(
            request.run_count
        ):
            run_seed = create_run_seed(
                request.base_seed,
                run_index,
            )

            if base_job_definitions is None:
                run_job_definitions = None
            else:
                run_job_definitions = (
                    create_manual_workload_variant(
                        job_definitions=(
                            base_job_definitions
                        ),
                        seed=run_seed,
                        run_index=run_index,
                    )
                )

            run_results = [
                evaluate_method(
                    algorithm=algorithm,
                    seed=run_seed,
                    models=models,
                    job_definitions=(
                        run_job_definitions
                    ),
                )
                for algorithm in algorithms
            ]

            completed_results = [
                result
                for result in run_results
                if (
                    result["finished"]
                    and result["average_waiting"]
                    is not None
                )
            ]

            winners: list[str] = []

            if completed_results:
                best_waiting = min(
                    float(
                        result["average_waiting"]
                    )
                    for result in completed_results
                )

                winners = [
                    str(result["algorithm"])
                    for result in completed_results
                    if np.isclose(
                        float(
                            result[
                                "average_waiting"
                            ]
                        ),
                        best_waiting,
                    )
                ]

                for winner in winners:
                    win_counts[winner] += 1

                if len(winners) == 1:
                    exclusive_win_counts[
                        winners[0]
                    ] += 1

            runs.append(
                {
                    "run_number": run_index + 1,
                    "seed": run_seed,
                    "winner_algorithms": winners,
                    "results": run_results,
                }
            )

        summaries = []

        for algorithm in algorithms:
            algorithm_results = [
                result
                for run in runs
                for result in run["results"]
                if result["algorithm"] == algorithm
            ]

            completed_results = [
                result
                for result in algorithm_results
                if (
                    result["finished"]
                    and result["average_waiting"]
                    is not None
                )
            ]

            waiting_values = [
                float(result["average_waiting"])
                for result in completed_results
            ]

            reward_values = [
                float(result["total_reward"])
                for result in algorithm_results
            ]

            elapsed_values = [
                float(result["elapsed_steps"])
                for result in algorithm_results
            ]

            decision_values = [
                float(result["decision_count"])
                for result in algorithm_results
            ]

            summaries.append(
                {
                    "algorithm": algorithm,
                    "run_count": request.run_count,
                    "completed_runs": len(
                        completed_results
                    ),
                    "failed_runs": (
                        request.run_count
                        - len(completed_results)
                    ),
                    "mean_waiting": (
                        calculate_optional_mean(
                            waiting_values
                        )
                    ),
                    "std_waiting": (
                        calculate_optional_standard_deviation(
                            waiting_values
                        )
                    ),
                    "minimum_waiting": (
                        min(waiting_values)
                        if waiting_values
                        else None
                    ),
                    "maximum_waiting": (
                        max(waiting_values)
                        if waiting_values
                        else None
                    ),
                    "mean_reward": (
                        calculate_optional_mean(
                            reward_values
                        )
                    ),
                    "mean_elapsed_steps": (
                        calculate_optional_mean(
                            elapsed_values
                        )
                    ),
                    "mean_decision_count": (
                        calculate_optional_mean(
                            decision_values
                        )
                    ),
                    "win_count": (
                        win_counts[algorithm]
                    ),
                    "exclusive_win_count": (
                        exclusive_win_counts[
                            algorithm
                        ]
                    ),
                }
            )

        ranked_summaries = sorted(
            summaries,
            key=lambda summary: (
                summary["mean_waiting"] is None,
                (
                    summary["mean_waiting"]
                    if summary["mean_waiting"]
                    is not None
                    else float("inf")
                ),
                -summary["completed_runs"],
            ),
        )

        for rank, summary in enumerate(
            ranked_summaries,
            start=1,
        ):
            summary["rank"] = rank

        best_algorithm = (
            ranked_summaries[0]["algorithm"]
            if (
                ranked_summaries
                and ranked_summaries[0][
                    "mean_waiting"
                ] is not None
            )
            else None
        )

        return {
            "base_seed": request.base_seed,
            "run_count": request.run_count,
            "input_mode": (
                "manual"
                if base_job_definitions is not None
                else "synthetic"
            ),
            "workload_strategy": (
                "seeded_arrival_permutations"
                if base_job_definitions is not None
                else "synthetic_seed_series"
            ),
            "job_count": (
                len(base_job_definitions)
                if base_job_definitions is not None
                else (
                    runs[0]["results"][0][
                        "job_count"
                    ]
                    if runs
                    else 0
                )
            ),
            "best_algorithm": best_algorithm,
            "summaries": ranked_summaries,
            "runs": runs,
        }

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Benchmark basarisiz: {exc}",
        ) from exc