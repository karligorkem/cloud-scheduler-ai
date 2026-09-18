export interface Job {
  id: string;
  status: string;
  required_cpu: number;
  required_memory_gb: number;
  required_gpu_count: number;
  arrival_step: number;
  remaining_steps: number;
  assigned_server_id: string | null;
}

export interface Server {
  id: string;
  is_active: boolean;
  total_cpu: number;
  available_cpu: number;
  total_memory_gb: number;
  available_memory_gb: number;
  total_gpu: number;
  available_gpu: number;
  running_jobs: Job[];
}

export interface DecisionEvent {
  decision: number;
  time_before: number;
  time_after: number;
  kind: "wait" | "assign";
  job_id: string | null;
  server_id: string | null;
  reward: number;
  completed_job_ids: string[];
}

export interface SimulationState {
  algorithm: string;
  seed: number;
  workload_seed: number;
  current_step: number;
  decision_count: number;
  total_reward: number;
  terminated: boolean;
  truncated: boolean;
  total_jobs: number;
  pending_count: number;
  queue_count: number;
  running_count: number;
  completed_count: number;
  average_waiting_completed: number | null;
  action_mask: boolean[];
  servers: Server[];
  queue: Job[];
  completed_jobs: Job[];
  events: DecisionEvent[];
}

export async function requestState(
  endpoint: "state" | "step" | "reset",
  seed?: number,
): Promise<SimulationState> {
  const controller = new AbortController();
  const timeout = window.setTimeout(() => controller.abort(), 15000);

  try {
    const response = await fetch(
      `http://127.0.0.1:8000/api/${endpoint}`,
      {
        method: endpoint === "state" ? "GET" : "POST",
        headers: { "Content-Type": "application/json" },
        body: endpoint === "reset" ? JSON.stringify({ seed }) : undefined,
        signal: controller.signal,
      },
    );

    if (!response.ok) {
      const body = await response.json().catch(() => null);
      const detail = body?.detail;

      throw new Error(
        typeof detail === "string"
          ? detail
          : `İstek başarısız oldu (${response.status}).`,
      );
    }

    return await response.json();
  } finally {
    window.clearTimeout(timeout);
  }
}