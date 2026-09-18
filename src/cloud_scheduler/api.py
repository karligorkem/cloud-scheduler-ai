from pathlib import Path
from threading import Lock
from typing import Literal
from cloud_scheduler.comparison_api import router as comparison_router
import numpy as np
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sb3_contrib import MaskablePPO
from uuid import uuid4
from cloud_scheduler.system_events_api import router as system_events_router

from cloud_scheduler.storage import (
    get_experiment,
    initialize_database,
    list_experiments,
    save_experiment,
)
from cloud_scheduler.scenario import JobDefinition
from cloud_scheduler.gym_environment import CloudSchedulerEnv
from cloud_scheduler.queue_gym_environment import QueueAwareCloudSchedulerEnv
from cloud_scheduler.schedulers.first_fit import FirstFitScheduler
from cloud_scheduler.schedulers.best_fit import BestFitScheduler
from cloud_scheduler.schedulers.best_fit_ram import BestFitRamScheduler


app = FastAPI(
    title="Cloud Scheduler API",
    version="0.3.0",
)

app.include_router(comparison_router)
app.include_router(system_events_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

AlgorithmName = Literal[
    "First Fit",
    "Best Fit",
    "Best Fit RAM",
    "PPO",
    "PPO Queue",
]

schedulers = {
    "First Fit": FirstFitScheduler(),
    "Best Fit": BestFitScheduler(),
    "Best Fit RAM": BestFitRamScheduler(),
}

# api.py -> cloud_scheduler -> src -> proje ana klasörü
project_root = Path(__file__).resolve().parents[2]

model_paths = {
    "PPO": project_root / "outputs/ppo_long_run/scheduler_ppo.zip",
    "PPO Queue": project_root / "outputs/ppo_queue_run/scheduler_ppo.zip",
}

# Aynı modeli her kararda yeniden yüklememek için sakla.
model_cache: dict[str, MaskablePPO] = {}

simulation_lock = Lock()
initialize_database()
current_experiment_id = str(uuid4())

environment = CloudSchedulerEnv(max_decisions=2000)
current_observation, initial_info = environment.reset(seed=42)

current_algorithm = "First Fit"
current_seed = 42
workload_seed = initial_info["episode_seed"]

total_reward = 0.0
terminated = False
truncated = False

events: list[dict] = []
resource_history: list[dict] = []


def record_resource_usage() -> None:
    """Her simülasyon zamanı için en son kaynak durumunu kaydeder."""
    simulation = environment.environment.simulation
    servers = simulation.cluster.servers

    total_cpu = sum(server.total_cpu for server in servers)
    used_cpu = sum(
        server.total_cpu - server.available_cpu
        for server in servers
    )

    total_ram = sum(server.total_memory_gb for server in servers)
    used_ram = sum(
        server.total_memory_gb - server.available_memory_gb
        for server in servers
    )

    point = {
        "step": simulation.cluster.current_step,
        "cpu_percent": 100.0 * used_cpu / total_cpu if total_cpu else 0.0,
        "ram_percent": 100.0 * used_ram / total_ram if total_ram else 0.0,
    }

    # Atama zamanı ilerletmez. Aynı zamandaki yeni atamalar,
    # o zamana ait kaynak durumunu günceller.
    if resource_history and resource_history[-1]["step"] == point["step"]:
        resource_history[-1] = point
    else:
        resource_history.append(point)


record_resource_usage()
class ManualJobRequest(BaseModel):
    job_id: str = Field(min_length=1, max_length=80)
    required_cpu: int = Field(ge=1, le=8)
    required_memory_gb: float = Field(gt=0, le=16)
    duration_steps: int = Field(ge=1, le=1000)
    required_gpu_count: int = Field(default=0, ge=0)
    arrival_step: int = Field(default=0, ge=0)
class ResetRequest(BaseModel):
    seed: int = Field(default=42, ge=0, le=2**31 - 1)
    algorithm: AlgorithmName = "First Fit"
    jobs: list[ManualJobRequest] | None = Field(
        default=None,
        min_length=1,
        max_length=200,
    )

def load_model(algorithm: str) -> MaskablePPO:
    """Modeli ilk kullanımda yükler, sonraki kullanımlarda önbellekten alır."""

    if algorithm in model_cache:
        return model_cache[algorithm]

    model_path = model_paths[algorithm]

    if not model_path.is_file():
        raise HTTPException(
            status_code=404,
            detail=f"Model dosyasi bulunamadi: {model_path.name} "
            f"({model_path.parent.name})",
        )

    try:
        model = MaskablePPO.load(str(model_path), device="cpu")
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Model yuklenemedi. Dosyayi ve kutuphane surumlerini kontrol et.",
        ) from exc

    model_cache[algorithm] = model
    return model


def serialize_job(job) -> dict:
    return {
        "id": job.job_id,
        "status": job.status.value,
        "required_cpu": job.required_cpu,
        "required_memory_gb": job.required_memory_gb,
        "required_gpu_count": job.required_gpu_count,
        "arrival_step": job.arrival_step,
        "remaining_steps": job.remaining_steps,
        "assigned_server_id": job.assigned_server_id,
    }


def build_state() -> dict:
    decision_environment = environment.environment
    simulation = decision_environment.simulation

    servers = []

    for server in simulation.cluster.servers:
        servers.append(
            {
                "id": server.server_id,
                "is_active": server.is_active,
                "total_cpu": server.total_cpu,
                "available_cpu": server.available_cpu,
                "total_memory_gb": server.total_memory_gb,
                "available_memory_gb": server.available_memory_gb,
                "total_gpu": server.gpu_count,
                "available_gpu": server.available_gpu_count,
                "running_jobs": [
                    serialize_job(job)
                    for job in server.running_jobs
                ],
            }
        )

    waiting_times = [
        job.waiting_steps
        for job in simulation.completed_jobs
        if job.waiting_steps is not None
    ]

    average_waiting = None

    if waiting_times:
        average_waiting = sum(waiting_times) / len(waiting_times)

    return {
        "experiment_id": current_experiment_id,
        "algorithm": current_algorithm,
        "seed": current_seed,
        "workload_seed": workload_seed,
        "observation_size": len(current_observation),
        "current_step": simulation.cluster.current_step,
        "decision_count": decision_environment.decision_count,
        "total_reward": total_reward,
        "terminated": terminated,
        "truncated": truncated,
        "total_jobs": environment.job_count,
        "input_mode": (
            "manual"
            if environment.job_definitions is not None
            else "synthetic"
        ),
                "job_definitions": [
            {
                "job_id": definition.job_id,
                "required_cpu": definition.required_cpu,
                "required_memory_gb": (
                    definition.required_memory_gb
                ),
                "duration_steps": definition.duration_steps,
                "required_gpu_count": (
                    definition.required_gpu_count
                ),
                "arrival_step": definition.arrival_step,
            }
            for definition in (
                environment.job_definitions or ()
            )
        ],
        "pending_count": len(simulation.pending_jobs),
        "pending_count": len(simulation.pending_jobs),
        "queue_count": len(simulation.queue.jobs),
        "running_count": sum(
            len(server.running_jobs)
            for server in simulation.cluster.servers
        ),
        "completed_count": len(simulation.completed_jobs),
        "average_waiting_completed": average_waiting,
        "action_mask": environment.action_masks().tolist(),
        "servers": servers,
        "queue": [
            serialize_job(job)
            for job in simulation.queue.jobs
        ],
        "completed_jobs": [
            serialize_job(job)
            for job in simulation.completed_jobs
        ],
        "events": list(events),
                "resource_history": [
            dict(point) for point in resource_history
        ],
    }

def save_current_state() -> dict:
    state = build_state()
    save_experiment(current_experiment_id, state)
    return state

def choose_action() -> int:
    simulation = environment.environment.simulation

    # Öğrenilmiş modelle karar ver.
    if current_algorithm in model_paths:
        model = load_model(current_algorithm)

        prediction, _ = model.predict(
            current_observation,
            action_masks=environment.action_masks(),
            deterministic=True,
        )

        return int(np.asarray(prediction).item())

    # Klasik algoritmayla karar ver.
    servers = simulation.cluster.servers
    wait_action = len(servers)

    job = simulation.queue.peek()

    if job is None:
        return wait_action

    selected_server = schedulers[current_algorithm].select_server(
        simulation.cluster,
        job,
    )

    if selected_server is None:
        return wait_action

    for index, server in enumerate(servers):
        if server.server_id == selected_server.server_id:
            return index

    raise RuntimeError("Selected server is not in the cluster.")


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/algorithms")
def get_algorithms() -> dict:
    return {
        "algorithms": [
            *schedulers.keys(),
            *model_paths.keys(),
        ]
    }


@app.get("/api/state")
def get_state() -> dict:
    with simulation_lock:
        return build_state()


@app.post("/api/reset")
def reset_simulation(request: ResetRequest) -> dict:
    global environment, current_observation
    global current_algorithm, current_seed, workload_seed
    global total_reward, terminated, truncated
    global current_experiment_id

    with simulation_lock:
        job_definitions = None

        if request.jobs is not None:
            normalized_ids = [
                job.job_id.replace(" ", "").lower()
                for job in request.jobs
            ]

            if any(
                job_id == ""
                for job_id in normalized_ids
            ):
                raise HTTPException(
                    status_code=422,
                    detail="Gorev kimligi bos olamaz.",
                )

            if len(normalized_ids) != len(
                set(normalized_ids)
            ):
                raise HTTPException(
                    status_code=422,
                    detail="Gorev kimlikleri benzersiz olmali.",
                )

            job_definitions = tuple(
                JobDefinition(
                    job_id=job.job_id,
                    required_cpu=job.required_cpu,
                    required_memory_gb=(
                        job.required_memory_gb
                    ),
                    duration_steps=job.duration_steps,
                    required_gpu_count=(
                        job.required_gpu_count
                    ),
                    arrival_step=job.arrival_step,
                )
                for job in request.jobs
            )

        if request.algorithm == "PPO Queue":
            new_environment = (
                QueueAwareCloudSchedulerEnv(
                    max_decisions=2000,
                    job_definitions=job_definitions,
                )
            )
        else:
            new_environment = CloudSchedulerEnv(
                max_decisions=2000,
                job_definitions=job_definitions,
            )

        try:
            new_observation, info = (
                new_environment.reset(
                    seed=request.seed,
                )
            )

            if request.algorithm in model_paths:
                model = load_model(request.algorithm)

                if (
                    model.observation_space.shape
                    != new_environment.observation_space.shape
                ):
                    raise HTTPException(
                        status_code=422,
                        detail=(
                            "Modelin gozlem boyutu "
                            "secilen ortamla uyusmuyor."
                        ),
                    )

                if (
                    model.action_space.n
                    != new_environment.action_space.n
                ):
                    raise HTTPException(
                        status_code=422,
                        detail=(
                            "Modelin eylem sayisi "
                            "secilen ortamla uyusmuyor."
                        ),
                    )
        except Exception:
            new_environment.close()
            raise

        old_environment = environment

        environment = new_environment
        current_observation = new_observation
        current_experiment_id = str(uuid4())

        current_algorithm = request.algorithm
        current_seed = request.seed
        workload_seed = info["episode_seed"]

        total_reward = 0.0
        terminated = False
        truncated = False

        events.clear()
        resource_history.clear()
        record_resource_usage()

        old_environment.close()

        return save_current_state()


@app.post("/api/reset")
def reset_simulation(request: ResetRequest) -> dict:
    global current_experiment_id
    global environment, current_observation
    global current_algorithm, current_seed, workload_seed
    global total_reward, terminated, truncated

    with simulation_lock:
        # Önce yeni ortamı hazırla.
        # Model yüklenemezse mevcut deney korunur.
        if request.algorithm == "PPO Queue":
            new_environment = QueueAwareCloudSchedulerEnv(
                max_decisions=2000,
                job_definitions=job_definitions,
            )
        else:
            new_environment = CloudSchedulerEnv(
                max_decisions=2000,
                job_definitions=job_definitions,

            
            )

            

        try:
            new_observation, info = new_environment.reset(seed=request.seed)

            if request.algorithm in model_paths:
                model = load_model(request.algorithm)

                if (
                    model.observation_space.shape
                    != new_environment.observation_space.shape
                ):
                    raise HTTPException(
                        status_code=422,
                        detail="Modelin gozlem boyutu secilen ortamla uyusmuyor.",
                    )

                if model.action_space.n != new_environment.action_space.n:
                    raise HTTPException(
                        status_code=422,
                        detail="Modelin eylem sayisi secilen ortamla uyusmuyor.",
                    )
        except Exception:
            new_environment.close()
            raise

        # Hazırlık başarılı; artık yeni deneye geçebiliriz.
        old_environment = environment

        environment = new_environment
        current_experiment_id = str(uuid4())
        current_observation = new_observation

        current_algorithm = request.algorithm
        current_seed = request.seed
        workload_seed = info["episode_seed"]

        total_reward = 0.0
        terminated = False
        truncated = False
        events.clear()
        resource_history.clear()
        record_resource_usage()
        old_environment.close()

        return save_current_state()


@app.post("/api/step")
def advance_decision() -> dict:
    global current_observation
    global total_reward, terminated, truncated

    with simulation_lock:
        if environment.environment.closed:
            raise HTTPException(
                status_code=409,
                detail="Deney sona erdi. Yeni deney baslatin.",
            )

        simulation = environment.environment.simulation
        wait_action = len(simulation.cluster.servers)

        action = choose_action()

        time_before = simulation.cluster.current_step
        next_job = simulation.queue.peek()

        job_id = None
        server_id = None

        if action != wait_action:
            job_id = next_job.job_id
            server_id = simulation.cluster.servers[action].server_id

        completed_before = len(simulation.completed_jobs)

        (
            current_observation,
            reward,
            terminated,
            truncated,
            _,
        ) = environment.step(action)

        total_reward += float(reward)
        record_resource_usage()

        newly_completed = simulation.completed_jobs[completed_before:]

        events.append(
            {
                "decision": environment.environment.decision_count,
                "algorithm": current_algorithm,
                "time_before": time_before,
                "time_after": simulation.cluster.current_step,
                "kind": "wait" if action == wait_action else "assign",
                "job_id": job_id,
                "server_id": server_id,
                "reward": float(reward),
                "completed_job_ids": [
                    job.job_id for job in newly_completed
                ],
            }
        )

        return save_current_state()

@app.get("/api/experiments")
def experiment_history() -> dict:
    return {
        "experiments": list_experiments(),
    }


@app.get("/api/experiments/{experiment_id}")
def experiment_detail(experiment_id: str) -> dict:
    experiment = get_experiment(experiment_id)

    if experiment is None:
        raise HTTPException(
            status_code=404,
            detail="Deney bulunamadi.",
        )

    return experiment


# Backend açıldığında yeni deneyin başlangıç durumunu kaydet.
save_current_state()   