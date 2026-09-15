import csv
from pathlib import Path

import numpy as np
from sb3_contrib import MaskablePPO

from cloud_scheduler.gym_environment import CloudSchedulerEnv
from cloud_scheduler.scenario_config import ScenarioConfig
from cloud_scheduler.schedulers.best_fit import BestFitScheduler
from cloud_scheduler.schedulers.best_fit_ram import BestFitRamScheduler
from cloud_scheduler.schedulers.first_fit import FirstFitScheduler


def run_experiment(
    model: MaskablePPO,
    algorithm: str,
    scenario_name: str,
    config: ScenarioConfig,
    seed: int,
) -> dict:
    """Bir yöntemi belirtilen senaryo ayarlarıyla çalıştırır."""

    schedulers = {
        "First Fit": FirstFitScheduler(),
        "Best Fit": BestFitScheduler(),
        "Best Fit RAM": BestFitRamScheduler(),
    }

    env = CloudSchedulerEnv(
        config=config,
        max_decisions=2000,
    )

    try:
        observation, info = env.reset(seed=seed)
        workload_seed = info["episode_seed"]
        total_reward = 0.0

        while True:
            if algorithm == "PPO":
                predicted_action, _ = model.predict(
                    observation,
                    action_masks=env.action_masks(),
                    deterministic=True,
                )

                action = int(np.asarray(predicted_action).item())

            else:
                simulation = env.environment.simulation
                servers = simulation.cluster.servers
                job = simulation.queue.peek()

                action = len(servers)

                if job is not None:
                    selected_server = schedulers[algorithm].select_server(
                        simulation.cluster,
                        job,
                    )

                    if selected_server is not None:
                        action = servers.index(selected_server)

            observation, reward, terminated, truncated, info = (
                env.step(action)
            )

            total_reward = total_reward + reward

            if terminated or truncated:
                break

        jobs = env.environment.simulation.completed_jobs
        average_waiting = None

        if terminated:
            if len(jobs) != config.job_count:
                raise ValueError("Completed job count does not match scenario.")

            total_waiting = 0

            for job in jobs:
                if job.waiting_steps is None:
                    raise ValueError("Completed job is missing timing.")

                total_waiting = total_waiting + job.waiting_steps

            if total_reward != -total_waiting:
                raise ValueError("Reward and waiting time do not match.")

            average_waiting = total_waiting / config.job_count

        return {
            "scenario": scenario_name,
            "algorithm": algorithm,
            "seed": seed,
            "workload_seed": workload_seed,
            "job_count": config.job_count,
            "max_arrival_step": config.max_arrival_step,
            "large_server_cpu": config.large_server_cpu,
            "large_server_memory_gb": config.large_server_memory_gb,
            "small_server_cpu": config.small_server_cpu,
            "small_server_memory_gb": config.small_server_memory_gb,
            "completed_count": len(jobs),
            "terminated": terminated,
            "truncated": truncated,
            "elapsed_steps": info["current_step"],
            "total_reward": total_reward,
            "average_waiting": average_waiting,
        }

    finally:
        env.close()


def main() -> None:
    model_path = Path("outputs/ppo_long_run/scheduler_ppo.zip")

    if not model_path.is_file():
        raise FileNotFoundError(f"Model bulunamadi: {model_path}")

    model = MaskablePPO.load(str(model_path), device="cpu")

    scenarios = {
        "default": ScenarioConfig(),
        "busy": ScenarioConfig(
            job_count=40,
            max_arrival_step=5,
        ),
        "larger_servers": ScenarioConfig(
            large_server_cpu=16,
            large_server_memory_gb=32.0,
            small_server_cpu=8,
            small_server_memory_gb=16.0,
        ),
    }

    algorithms = ["First Fit", "Best Fit", "Best Fit RAM", "PPO"]
    seeds = list(range(4000, 4010))
    all_results = []

    for scenario_name, config in scenarios.items():
        print(f"\nSENARYO: {scenario_name}")

        scenario_results = []
        common_results = []
        common_count = 0

        for seed in seeds:
            seed_results = []

            for algorithm in algorithms:
                result = run_experiment(
                    model=model,
                    algorithm=algorithm,
                    scenario_name=scenario_name,
                    config=config,
                    seed=seed,
                )

                seed_results.append(result)
                scenario_results.append(result)
                all_results.append(result)

            workload_seeds = {
                result["workload_seed"] for result in seed_results
            }

            if len(workload_seeds) != 1:
                raise ValueError("Workload seeds do not match.")

            if all(
                result["terminated"] and not result["truncated"]
                for result in seed_results
            ):
                common_results.extend(seed_results)
                common_count = common_count + 1

            print(f"Seed {seed} tamamlandi.")

        print(f"\nOrtak tamamlanan: {common_count}/{len(seeds)}")

        for algorithm in algorithms:
            completed_count = sum(
                1
                for result in scenario_results
                if result["algorithm"] == algorithm
                and result["terminated"]
                and not result["truncated"]
            )

            waiting_values = [
                result["average_waiting"]
                for result in common_results
                if result["algorithm"] == algorithm
            ]

            if waiting_values:
                average = sum(waiting_values) / len(waiting_values)
                average_text = f"{average:.4f}"
            else:
                average_text = "hesaplanamadi"

            print(
                f"{algorithm}"
                f" | Tamamlanan deney: {completed_count}/{len(seeds)}"
                f" | Ortak ortalama bekleme: {average_text}"
            )

    output_path = Path(
        "outputs/ppo_long_run/scenario_comparison.csv"
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open(
        mode="w",
        newline="",
        encoding="utf-8-sig",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=list(all_results[0].keys()),
        )

        writer.writeheader()
        writer.writerows(all_results)

    print(f"\nCSV kaydedildi: {output_path.resolve()}")


if __name__ == "__main__":
    main()