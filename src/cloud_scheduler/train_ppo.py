from pathlib import Path

from sb3_contrib import MaskablePPO
from stable_baselines3.common.monitor import Monitor

from cloud_scheduler.gym_environment import CloudSchedulerEnv


def main() -> None:
    output_directory = Path("outputs/ppo_first_run")
    output_directory.mkdir(parents=True, exist_ok=True)

    # Monitor, tamamlanan deneylerin ödül ve karar sayılarını kaydeder.
    train_env = Monitor(
        CloudSchedulerEnv(max_decisions=1000),
        filename=str(output_directory / "training.monitor.csv"),
    )

    try:
        model = MaskablePPO(
            policy="MlpPolicy",
            env=train_env,
            learning_rate=0.0003,
            n_steps=256,
            batch_size=64,
            n_epochs=10,
            gamma=1.0,
            ent_coef=0.01,
            seed=42,
            device="cpu",
            verbose=1,
        )

        print("Ilk egitim basliyor.")

        # Buradaki adim, bir agent karari anlamina gelir.
        model.learn(total_timesteps=10_240)

        model_path = output_directory / "scheduler_ppo"
        model.save(str(model_path))

        print(f"Model kaydedildi: {model_path}.zip")

    finally:
        train_env.close()

    # Eğitim ortamından ayrı bir ortamda kısa değerlendirme yap.
    eval_env = CloudSchedulerEnv(max_decisions=1000)

    try:
        for seed in [1001, 1002, 1003]:
            observation, info = eval_env.reset(seed=seed)
            episode_seed = info["episode_seed"]

            total_reward = 0.0

            while True:
                action, _ = model.predict(
                    observation,
                    action_masks=eval_env.action_masks(),
                    deterministic=True,
                )

                observation, reward, terminated, truncated, info = (
                    eval_env.step(int(action.item()))
                )

                total_reward = total_reward + reward

                if terminated or truncated:
                    break

            print(
                f"\nDegerlendirme seed: {seed}"
                f"\nGorev seed: {episode_seed}"
                f"\nTamamlandi: {terminated}"
                f"\nSinirda durdu: {truncated}"
                f"\nTamamlanan gorev: {info['completed_count']}/20"
                f"\nGecen zaman: {info['current_step']}"
                f"\nToplam odul: {total_reward:.2f}"
            )

    finally:
        eval_env.close()


if __name__ == "__main__":
    main()