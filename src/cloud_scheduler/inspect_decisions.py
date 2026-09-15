from pathlib import Path

import numpy as np
from sb3_contrib import MaskablePPO

from cloud_scheduler.compare_ppo import choose_rule_action
from cloud_scheduler.gym_environment import CloudSchedulerEnv


def describe_action(env: CloudSchedulerEnv, action: int) -> str:
    """Eylem indeksini okunabilir bir açıklamaya çevirir."""

    servers = env.environment.simulation.cluster.servers

    if action == len(servers):
        return "Bir adim bekle"

    return f"Sunucuya ata: {servers[action].server_id}"


def inspect_seed(model: MaskablePPO, seed: int) -> None:
    """İki politikanın aynı durumdaki ilk farklı kararını gösterir."""

    ppo_env = CloudSchedulerEnv(max_decisions=1000)
    best_fit_env = CloudSchedulerEnv(max_decisions=1000)

    try:
        ppo_observation, ppo_info = ppo_env.reset(seed=seed)
        best_fit_observation, best_fit_info = best_fit_env.reset(seed=seed)

        if ppo_info["episode_seed"] != best_fit_info["episode_seed"]:
            raise ValueError("Workload seeds do not match.")

        print(f"\nSENARYO: {seed}")
        print(f"Gorev seed: {ppo_info['episode_seed']}")

        for decision_number in range(1, 1001):
            # İlk farklı karara kadar gözlemler ve maskeler eşleşmeli.
            if not np.array_equal(ppo_observation, best_fit_observation):
                raise ValueError("Observations diverged before actions differed.")

            ppo_mask = ppo_env.action_masks()
            best_fit_mask = best_fit_env.action_masks()

            if not np.array_equal(ppo_mask, best_fit_mask):
                raise ValueError("Action masks do not match.")

            predicted_action, _ = model.predict(
                ppo_observation,
                action_masks=ppo_mask,
                deterministic=True,
            )

            ppo_action = int(np.asarray(predicted_action).item())

            best_fit_action = choose_rule_action(
                best_fit_env,
                "Best Fit",
            )

            if ppo_action != best_fit_action:
                simulation = ppo_env.environment.simulation
                job = simulation.queue.peek()

                print(f"Ilk farkli karar: {decision_number}")
                print(f"Simulasyon zamani: {simulation.cluster.current_step}")
                print(f"Kuyruk uzunlugu: {len(simulation.queue.jobs)}")
                print(f"Gecerli eylemler: {ppo_mask.tolist()}")

                if job is not None:
                    print(
                        f"Siradaki gorev: {job.job_id}"
                        f" | CPU: {job.required_cpu}"
                        f" | RAM: {job.required_memory_gb}"
                        f" | GPU: {job.required_gpu_count}"
                        f" | Gelis: {job.arrival_step}"
                    )

                for server in simulation.cluster.servers:
                    print(
                        f"Sunucu: {server.server_id}"
                        f" | Bos CPU: {server.available_cpu}"
                        f" | Bos RAM: {server.available_memory_gb}"
                        f" | Bos GPU: {server.available_gpu_count}"
                    )

                print(
                    "PPO karari:",
                    describe_action(ppo_env, ppo_action),
                )

                print(
                    "Best Fit karari:",
                    describe_action(best_fit_env, best_fit_action),
                )

                # İlk ayrışmayı bulduk; bu inceleme burada tamamlanır.
                return

            # Kararlar aynıysa iki ortamda da uygula ve devam et.
            ppo_result = ppo_env.step(ppo_action)
            best_fit_result = best_fit_env.step(best_fit_action)

            ppo_observation = ppo_result[0]
            best_fit_observation = best_fit_result[0]

            ppo_ended = ppo_result[2] or ppo_result[3]
            best_fit_ended = best_fit_result[2] or best_fit_result[3]

            if ppo_ended != best_fit_ended:
                raise ValueError("Episode endings do not match.")

            if ppo_ended:
                if ppo_result[2] and best_fit_result[2]:
                    print("Deney boyunca eylemler ayni kaldi.")
                else:
                    print("Karar sinirina kadar farkli eylem bulunamadi.")
                return

    finally:
        ppo_env.close()
        best_fit_env.close()


def main() -> None:
    model_path = Path("outputs/ppo_long_run/scheduler_ppo.zip")

    if not model_path.is_file():
        raise FileNotFoundError(f"Model bulunamadi: {model_path}")

    model = MaskablePPO.load(str(model_path), device="cpu")

    for seed in [3065, 3066]:
        inspect_seed(model, seed)


if __name__ == "__main__":
    main()