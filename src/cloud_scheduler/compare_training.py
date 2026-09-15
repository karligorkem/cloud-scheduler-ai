import csv
from pathlib import Path

from sb3_contrib import MaskablePPO

from cloud_scheduler.compare_scenarios import run_experiment
from cloud_scheduler.scenario_config import ScenarioConfig


def main() -> None:
    model_paths = {
        "PPO Single": Path(
            "outputs/ppo_long_run/scheduler_ppo.zip"
        ),
        "PPO Mixed": Path(
            "outputs/ppo_mixed_run/scheduler_ppo.zip"
        ),
    }

    models = {}

    for name, path in model_paths.items():
        if not path.is_file():
            raise FileNotFoundError(f"Model bulunamadi: {path}")

        models[name] = MaskablePPO.load(str(path), device="cpu")

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

    methods = [
        "First Fit",
        "Best Fit",
        "Best Fit RAM",
        "PPO Single",
        "PPO Mixed",
    ]

    seeds = list(range(5000, 5010))
    all_results = []

    for scenario_name, config in scenarios.items():
        scenario_results = []
        common_results = []
        common_count = 0

        print(f"\nSENARYO: {scenario_name}")

        for seed in seeds:
            seed_results = []

            for method in methods:
                if method in models:
                    algorithm = "PPO"
                    selected_model = models[method]
                else:
                    algorithm = method

                    # Kural tabanlı dalda model kullanılmıyor.
                    selected_model = models["PPO Single"]

                result = run_experiment(
                    model=selected_model,
                    algorithm=algorithm,
                    scenario_name=scenario_name,
                    config=config,
                    seed=seed,
                )

                # İki PPO sonucunu ayrı isimlerle kaydet.
                result["algorithm"] = method

                if method in model_paths:
                    result["model_path"] = str(model_paths[method])
                else:
                    result["model_path"] = ""

                seed_results.append(result)
                scenario_results.append(result)
                all_results.append(result)

            workload_seeds = {
                result["workload_seed"] for result in seed_results
            }

            if len(workload_seeds) != 1:
                raise ValueError("Workload seeds do not match.")

            all_completed = all(
                result["terminated"]
                and not result["truncated"]
                and result["completed_count"] == config.job_count
                for result in seed_results
            )

            if all_completed:
                common_results.extend(seed_results)
                common_count = common_count + 1

            print(f"Seed {seed} tamamlandi.")

        print(f"\nOrtak tamamlanan: {common_count}/{len(seeds)}")

        for method in methods:
            completed_count = sum(
                1
                for result in scenario_results
                if result["algorithm"] == method
                and result["terminated"]
                and not result["truncated"]
                and result["completed_count"] == config.job_count
            )

            waiting_values = [
                result["average_waiting"]
                for result in common_results
                if result["algorithm"] == method
            ]

            if waiting_values:
                average = sum(waiting_values) / len(waiting_values)
                average_text = f"{average:.4f}"
            else:
                average_text = "hesaplanamadi"

            print(
                f"{method}"
                f" | Tamamlanan: {completed_count}/{len(seeds)}"
                f" | Ortalama bekleme: {average_text}"
            )

    output_path = Path(
        "outputs/ppo_mixed_run/training_comparison.csv"
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

    print(f"\nSonuclar kaydedildi: {output_path.resolve()}")


if __name__ == "__main__":
    main()