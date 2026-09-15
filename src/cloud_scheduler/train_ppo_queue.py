from pathlib import Path

from sb3_contrib import MaskablePPO
from stable_baselines3.common.monitor import Monitor

from cloud_scheduler.queue_gym_environment import QueueAwareCloudSchedulerEnv


def main() -> None:
    # Bu deneyin dosyalarını ayrı bir klasörde sakla.
    output_directory = Path("outputs/ppo_queue_run")
    model_path = output_directory / "scheduler_ppo.zip"

    # Yanlışlıkla önceki eğitim sonucunun üzerine yazmayı engelle.
    if model_path.exists():
        raise FileExistsError(
            f"Bu konumda zaten model var: {model_path}"
        )

    output_directory.mkdir(parents=True, exist_ok=True)

    # Varsayılan senaryo ve 26 sayılık gözlem.
    base_environment = QueueAwareCloudSchedulerEnv(
        max_decisions=1000,
    )

    # Her deneyin toplam ödülünü ve karar sayısını CSV'ye kaydet.
    environment = Monitor(
        base_environment,
        filename=str(output_directory / "training.monitor.csv"),
    )

    try:
        print("Kuyruk bilgisiyle PPO egitimi basliyor.")
        print(f"Gozlem boyutu: {environment.observation_space.shape}")
        print(f"Eylem sayisi: {environment.action_space.n}")

        model = MaskablePPO(
            policy="MlpPolicy",
            env=environment,
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

        # Önceki uzun eğitimle aynı karar bütçesi.
        model.learn(total_timesteps=102_400)

        model.save(str(model_path))

        print()
        print(f"Model kaydedildi: {model_path}")

    finally:
        environment.close()


if __name__ == "__main__":
    main()