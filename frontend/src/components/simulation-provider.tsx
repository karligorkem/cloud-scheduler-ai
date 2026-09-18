import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from "react";

import type { ReactNode } from "react";

export interface SimulationJob {
  id: string;
  status: string;
  required_cpu: number;
  required_memory_gb: number;
  required_gpu_count: number;
  arrival_step: number;
  remaining_steps: number;
  assigned_server_id: string | null;
}

export interface SimulationServer {
  id: string;
  is_active: boolean;
  total_cpu: number;
  available_cpu: number;
  total_memory_gb: number;
  available_memory_gb: number;
  total_gpu: number;
  available_gpu: number;
  running_jobs: SimulationJob[];
}

export interface SimulationState {
  algorithm: string;
  input_mode?: "manual" | "synthetic";
  seed: number;
  workload_seed: number;
  current_step: number;
  decision_count: number;
  total_jobs: number;
  pending_count: number;
  queue_count: number;
  running_count: number;
  completed_count: number;
  average_waiting_completed: number | null;
  total_reward: number;
  terminated: boolean;
  truncated: boolean;
  servers: SimulationServer[];
  queue: SimulationJob[];
  completed_jobs: SimulationJob[];
  resource_history?: {
    step: number;
    cpu_percent: number;
    ram_percent: number;
  }[];
}

interface SimulationContextValue {
  data: SimulationState | null;
  error: string;
  refresh: () => Promise<void>;
}

const SimulationContext = createContext<SimulationContextValue | null>(null);

export function SimulationProvider({
  children,
}: {
  children: ReactNode;
}) {
  const [data, setData] = useState<SimulationState | null>(null);
  const [error, setError] = useState("");

  const requestInFlight = useRef(false);

  const refresh = useCallback(async () => {
    // Önceki okuma sürüyorsa yeni istek gönderme.
    if (requestInFlight.current) return;

    requestInFlight.current = true;

    const controller = new AbortController();
    const timeout = window.setTimeout(() => {
      controller.abort();
    }, 10000);

    try {
      const response = await fetch(
        "http://127.0.0.1:8000/api/state",
        {
          signal: controller.signal,
          cache: "no-store",
        },
      );

      if (!response.ok) {
        throw new Error(`API hata kodu: ${response.status}`);
      }

      const result: SimulationState = await response.json();

      // Bütün bileşenler bu tek yanıtı kullanacak.
      setData(result);
      setError("");
    } catch {
      setError(
        "Simülasyon verisi alınamadı. Backend'in 8000 portunda çalıştığını kontrol et.",
      );
    } finally {
      window.clearTimeout(timeout);
      requestInFlight.current = false;
    }
  }, []);

  useEffect(() => {
    void refresh();

    const interval = window.setInterval(() => {
      void refresh();
    }, 1500);

    return () => {
      window.clearInterval(interval);
    };
  }, [refresh]);

  return (
    <SimulationContext.Provider value={{ data, error, refresh }}>
      {children}
    </SimulationContext.Provider>
  );
}

export function useSimulation() {
  const context = useContext(SimulationContext);

  if (context === null) {
    throw new Error(
      "useSimulation must be used inside SimulationProvider.",
    );
  }

  return context;
}