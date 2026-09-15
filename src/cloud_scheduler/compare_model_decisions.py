from pathlib import Path

import numpy as np
from sb3_contrib import MaskablePPO

from cloud_scheduler.gym_environment import CloudSchedulerEnv
from cloud_scheduler.scenario_config import ScenarioConfig


def describe_action(action: int, server_names: list[str]) -> str:
    """Eylem numarasını okunabilir bir açıklamaya dönüştürür."""

    if action == len(server_names):
        return "Bekle"

    return f"Sunucuya ata: {server_names[action]}"


def main() -> None:
    single_path = Path("outputs/ppo_long_run/scheduler_ppo.zip")
    mixed_path = Path("outputs/ppo_mixed_run/scheduler_ppo.zip")

    for model_path in (single_path, mixed_path):
        if not model_path.is_file():
            raise FileNotFoundError(f"Model bulunamadi: {model_path}")

    single_model = MaskablePPO.load(str(single_path), device="cpu")
    mixed_model = MaskablePPO.load(str(mixed_path), device="cpu")

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

    # Önceki karşılaştırmadaki senaryoları kullanıyoruz.
    seeds = range(5000, 5010)

    total_decisions = 0
    total_differences = 0
    total_choice_states = 0

    for scenario_name, config in scenarios.items():
        scenario_decisions = 0
        scenario_differences = 0
        scenario_choice_states = 0
        completed_episodes = 0
        truncated_episodes = 0
        printed_differences = 0

        for seed in seeds:
            environment = CloudSchedulerEnv(
                config=config,
                max_decisions=2000,
            )

            try:
                observation, _ = environment.reset(seed=seed)

                server_names = [
                    server.server_id
                    for server in environment.environment.simulation.cluster.servers
                ]

                while True:
                    mask = environment.action_masks()

                    # İki modele de aynı gözlemi ve aynı maskeyi ver.
                    single_prediction, _ = single_model.predict(
                        observation,
                        action_masks=mask,
                        deterministic=True,
                    )

                    mixed_prediction, _ = mixed_model.predict(
                        observation,
                        action_masks=mask,
                        deterministic=True,
                    )

                    single_action = int(np.asarray(single_prediction).item())
                    mixed_action = int(np.asarray(mixed_prediction).item())

                    scenario_decisions += 1

                    # Yalnızca bekleme mümkünse iki model de onu seçmek zorunda.
                    # En az iki geçerli eylem varsa gerçek bir seçim var.
                    if np.count_nonzero(mask) >= 2:
                        scenario_choice_states += 1

                    if single_action != mixed_action:
                        scenario_differences += 1

                        # Terminali doldurmamak için senaryo başına ilk 3 farkı göster.
                        if printed_differences < 3:
                            simulation = environment.environment.simulation

                            print()
                            print(f"SENARYO: {scenario_name} | Seed: {seed}")
                            print(f"Zaman: {simulation.cluster.current_step}")
                            print(f"Gecerli eylemler: {mask.tolist()}")
                            print(
                                "Single:",
                                describe_action(single_action, server_names),
                            )
                            print(
                                "Mixed:",
                                describe_action(mixed_action, server_names),
                            )

                            printed_differences += 1

                    # Ortak simülasyonu Single modelin kararıyla ilerlet.
                    # Mixed model aynı durumlarda ne seçerdi, onu ölçüyoruz.
                    observation, _, terminated, truncated, _ = environment.step(
                        single_action
                    )

                    if terminated or truncated:
                        completed_episodes += int(terminated)
                        truncated_episodes += int(truncated)
                        break

            finally:
                environment.close()

        total_decisions += scenario_decisions
        total_differences += scenario_differences
        total_choice_states += scenario_choice_states

        print()
        print(f"OZET: {scenario_name}")
        print(f"Tamamlanan senaryo: {completed_episodes}/{len(seeds)}")
        print(f"Sinirda duran: {truncated_episodes}")
        print(f"Karsilastirilan karar: {scenario_decisions}")
        print(f"Secim yapilabilen durum: {scenario_choice_states}")
        print(f"Farkli karar: {scenario_differences}")

    print()
    print("GENEL SONUC")
    print(f"Toplam karar: {total_decisions}")
    print(f"Secim yapilabilen durum: {total_choice_states}")
    print(f"Farkli karar: {total_differences}")

    if total_choice_states > 0:
        difference_rate = 100 * total_differences / total_choice_states
        print(f"Secim durumlarinda fark orani: %{difference_rate:.2f}")


if __name__ == "__main__":
    main()