import { useState } from "react";

import { useSimulation } from "@/components/simulation-provider";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

type Algorithm =
  | "First Fit"
  | "Best Fit"
  | "Best Fit RAM"
  | "PPO"
  | "PPO Queue";

interface JobDraft {
  key: number;
  job_id: string;
  required_cpu: string;
  required_memory_gb: string;
  duration_steps: string;
  required_gpu_count: string;
  arrival_step: string;
}
interface EventWorkloadResponse {
  source: string;
  event_count: number;
  job_count: number;
  jobs: {
    job_id: string;
    required_cpu: number;
    required_memory_gb: number;
    duration_steps: number;
    required_gpu_count: number;
    arrival_step: number;
  }[];
}

let nextKey = 3;

function createEmptyJob(): JobDraft {
  const key = nextKey;
  nextKey += 1;

  return {
    key,
    job_id: `manuel-${key}`,
    required_cpu: "1",
    required_memory_gb: "2",
    duration_steps: "3",
    required_gpu_count: "0",
    arrival_step: "0",
  };
}

async function readApiError(response: Response): Promise<string> {
  const body: unknown = await response.json().catch(() => null);

  if (
    typeof body === "object" &&
    body !== null &&
    "detail" in body &&
    typeof body.detail === "string"
  ) {
    return body.detail;
  }

  return `API hata kodu: ${response.status}`;
}

export function ManualJobBuilder() {
  const { refresh } = useSimulation();

  const [seed, setSeed] = useState("42");
  const [algorithm, setAlgorithm] =
    useState<Algorithm>("First Fit");

  const [jobs, setJobs] = useState<JobDraft[]>([
    {
      key: 1,
      job_id: "manuel-1",
      required_cpu: "2",
      required_memory_gb: "4",
      duration_steps: "3",
      required_gpu_count: "0",
      arrival_step: "0",
    },
    {
      key: 2,
      job_id: "manuel-2",
      required_cpu: "4",
      required_memory_gb: "8",
      duration_steps: "5",
      required_gpu_count: "0",
      arrival_step: "1",
    },
  ]);

  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  function updateJob(
    key: number,
    field: keyof Omit<JobDraft, "key">,
    value: string,
  ): void {
    setJobs((currentJobs) =>
      currentJobs.map((job) =>
        job.key === key
          ? {
              ...job,
              [field]: value,
            }
          : job,
      ),
    );
  }

  function removeJob(key: number): void {
    if (jobs.length === 1) {
      setError("En az bir görev bulunmalı.");
      return;
    }

    setJobs((currentJobs) =>
      currentJobs.filter((job) => job.key !== key),
    );

    setError("");
  }

  function addJob(): void {
    setJobs((currentJobs) => [
      ...currentJobs,
      createEmptyJob(),
    ]);

    setError("");
  }
  async function loadJobsFromWindowsEvents(): Promise<void> {
    if (busy) return;

    setBusy(true);
    setError("");
    setMessage("");

    try {
      const response = await fetch(
        "http://127.0.0.1:8000/api/system-events/workload?limit=20",
        {
          cache: "no-store",
        },
      );

      if (!response.ok) {
        throw new Error(await readApiError(response));
      }

      const result: EventWorkloadResponse =
        await response.json();

      const eventJobs: JobDraft[] = result.jobs.map(
        (job) => {
          const key = nextKey;
          nextKey += 1;

          return {
            key,
            job_id: job.job_id,
            required_cpu: String(job.required_cpu),
            required_memory_gb: String(
              job.required_memory_gb,
            ),
            duration_steps: String(job.duration_steps),
            required_gpu_count: String(
              job.required_gpu_count,
            ),
            arrival_step: String(job.arrival_step),
          };
        },
      );

      setJobs(eventJobs);

      setMessage(
        `${result.event_count} Windows olayı görev formuna aktarıldı. Değerleri kontrol edip deneyi başlatabilirsin.`,
      );
    } catch (caughtError) {
      setError(
        caughtError instanceof TypeError
          ? "Backend'e bağlanılamadı. 8000 portunu kontrol et."
          : caughtError instanceof Error
            ? caughtError.message
            : "Windows olayları görevlere dönüştürülemedi.",
      );
    } finally {
      setBusy(false);
    }
  }
  async function startManualExperiment(): Promise<void> {
    if (busy) return;

    const parsedSeed = Number(seed);

    if (
      seed.trim() === "" ||
      !Number.isInteger(parsedSeed) ||
      parsedSeed < 0 ||
      parsedSeed > 2147483647
    ) {
      setError(
        "Seed, 0 ile 2147483647 arasında bir tam sayı olmalı.",
      );
      return;
    }

    const normalizedIds = jobs.map((job) =>
      job.job_id.replaceAll(" ", "").toLocaleLowerCase("tr-TR"),
    );

    if (normalizedIds.some((jobId) => jobId === "")) {
      setError("Görev adı boş olamaz.");
      return;
    }

    if (new Set(normalizedIds).size !== normalizedIds.length) {
      setError("Görev adları benzersiz olmalı.");
      return;
    }

    const parsedJobs = jobs.map((job) => ({
      job_id: job.job_id.trim(),
      required_cpu: Number(job.required_cpu),
      required_memory_gb: Number(job.required_memory_gb),
      duration_steps: Number(job.duration_steps),
      required_gpu_count: Number(job.required_gpu_count),
      arrival_step: Number(job.arrival_step),
    }));

    for (const job of parsedJobs) {
      if (
        !Number.isInteger(job.required_cpu) ||
        job.required_cpu < 1 ||
        job.required_cpu > 8
      ) {
        setError(
          `${job.job_id}: CPU 1 ile 8 arasında tam sayı olmalı.`,
        );
        return;
      }

      if (
        !Number.isFinite(job.required_memory_gb) ||
        job.required_memory_gb <= 0 ||
        job.required_memory_gb > 16
      ) {
        setError(
          `${job.job_id}: RAM 0'dan büyük, 16 GB veya daha az olmalı.`,
        );
        return;
      }

      if (
        !Number.isInteger(job.duration_steps) ||
        job.duration_steps < 1
      ) {
        setError(
          `${job.job_id}: Süre en az 1 adım olmalı.`,
        );
        return;
      }

      if (
        !Number.isInteger(job.arrival_step) ||
        job.arrival_step < 0
      ) {
        setError(
          `${job.job_id}: Geliş adımı sıfır veya daha büyük olmalı.`,
        );
        return;
      }

      if (job.required_gpu_count !== 0) {
        setError(
          `${job.job_id}: Mevcut sunucularda GPU olmadığı için GPU ihtiyacı 0 olmalı.`,
        );
        return;
      }
    }

    setBusy(true);
    setError("");
    setMessage("");

    try {
      const response = await fetch(
        "http://127.0.0.1:8000/api/reset",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            seed: parsedSeed,
            algorithm,
            jobs: parsedJobs,
          }),
        },
      );

      if (!response.ok) {
        throw new Error(await readApiError(response));
      }

      setMessage(
        `${parsedJobs.length} manuel görevle ${algorithm} deneyi başlatıldı.`,
      );

      await refresh();
    } catch (caughtError) {
      setError(
        caughtError instanceof TypeError
          ? "Backend'e bağlanılamadı. 8000 portunu kontrol et."
          : caughtError instanceof Error
            ? caughtError.message
            : "Manuel deney başlatılamadı.",
      );
    } finally {
      setBusy(false);
    }
  }

  return (
    <section
      id="manual-input"
      aria-labelledby="manual-input-title"
      className="min-w-0 scroll-mt-20 px-4 lg:px-6"
    >
      <Card className="border-slate-700/70 bg-[#191c22]">
        <CardHeader>
          <CardTitle
            id="manual-input-title"
            className="text-slate-100"
          >
            Manuel iş yükü oluştur
          </CardTitle>

          <CardDescription className="text-slate-400">
            Simülasyona gönderilecek görevleri ve kaynak
            ihtiyaçlarını kendin belirle.
          </CardDescription>
        </CardHeader>

        <CardContent className="space-y-5">
          <div className="flex flex-wrap items-end gap-3">
            <div className="space-y-2">
              <label
                htmlFor="manual-algorithm"
                className="block text-sm font-medium text-slate-200"
              >
                Zamanlama algoritması
              </label>

              <select
                id="manual-algorithm"
                value={algorithm}
                disabled={busy}
                onChange={(event) =>
                  setAlgorithm(
                    event.target.value as Algorithm,
                  )
                }
                className="h-10 rounded-lg border border-slate-600 bg-[#0d0f12] px-3 text-sm text-slate-100 outline-none focus:border-orange-500"
              >
                <option value="First Fit">First Fit</option>
                <option value="Best Fit">Best Fit</option>
                <option value="Best Fit RAM">
                  Best Fit RAM
                </option>
                <option value="PPO">PPO — 14 girdi</option>
                <option value="PPO Queue">
                  PPO Queue — 26 girdi
                </option>
              </select>
            </div>

            <div className="space-y-2">
              <label
                htmlFor="manual-seed"
                className="block text-sm font-medium text-slate-200"
              >
                Deney seed’i
              </label>

              <input
                id="manual-seed"
                type="number"
                min={0}
                max={2147483647}
                step={1}
                value={seed}
                disabled={busy}
                onChange={(event) =>
                  setSeed(event.target.value)
                }
                className="h-10 w-40 rounded-lg border border-slate-600 bg-[#0d0f12] px-3 text-sm text-slate-100 outline-none focus:border-orange-500"
              />
            </div>

            <Button
              type="button"
              variant="outline"
              disabled={busy || jobs.length >= 200}
              onClick={addJob}
            >
              + Görev ekle
              <Button
                 type="button"
                 variant="outline"
                disabled={busy}
                onClick={() => void loadJobsFromWindowsEvents()}
              className="border-orange-500/30 text-orange-300 hover:bg-orange-500/10"
>
  Windows olaylarından doldur
</Button>
            </Button>

            <Button
              type="button"
              disabled={busy}
              onClick={() => void startManualExperiment()}
              className="bg-orange-500 text-black hover:bg-orange-400"
            >
              {busy
                ? "Deney hazırlanıyor…"
                : "Bu görevlerle deneyi başlat"}
            </Button>
          </div>

          <div className="overflow-x-auto rounded-xl border border-slate-700">
            <table className="w-full min-w-[950px] text-left text-sm">
              <thead className="bg-[#111b2c] text-xs text-slate-300">
                <tr>
                  <th className="px-3 py-3">Görev adı</th>
                  <th className="px-3 py-3">CPU</th>
                  <th className="px-3 py-3">RAM (GB)</th>
                  <th className="px-3 py-3">GPU</th>
                  <th className="px-3 py-3">Süre</th>
                  <th className="px-3 py-3">Geliş adımı</th>
                  <th className="px-3 py-3">İşlem</th>
                </tr>
              </thead>

              <tbody>
                {jobs.map((job) => (
                  <tr
                    key={job.key}
                    className="border-t border-slate-700/70"
                  >
                    <td className="p-2">
                      <input
                        value={job.job_id}
                        disabled={busy}
                        onChange={(event) =>
                          updateJob(
                            job.key,
                            "job_id",
                            event.target.value,
                          )
                        }
                        className="h-9 w-40 rounded-md border border-slate-600 bg-[#0d0f12] px-2 text-slate-100"
                      />
                    </td>

                    <td className="p-2">
                      <input
                        type="number"
                        min={1}
                        max={8}
                        step={1}
                        value={job.required_cpu}
                        disabled={busy}
                        onChange={(event) =>
                          updateJob(
                            job.key,
                            "required_cpu",
                            event.target.value,
                          )
                        }
                        className="h-9 w-20 rounded-md border border-slate-600 bg-[#0d0f12] px-2 text-slate-100"
                      />
                    </td>

                    <td className="p-2">
                      <input
                        type="number"
                        min={0.5}
                        max={16}
                        step={0.5}
                        value={job.required_memory_gb}
                        disabled={busy}
                        onChange={(event) =>
                          updateJob(
                            job.key,
                            "required_memory_gb",
                            event.target.value,
                          )
                        }
                        className="h-9 w-24 rounded-md border border-slate-600 bg-[#0d0f12] px-2 text-slate-100"
                      />
                    </td>

                    <td className="p-2">
                      <input
                        type="number"
                        value="0"
                        disabled
                        aria-label={`${job.job_id} GPU ihtiyacı`}
                        className="h-9 w-20 rounded-md border border-slate-700 bg-slate-900 px-2 text-slate-500"
                      />
                    </td>

                    <td className="p-2">
                      <input
                        type="number"
                        min={1}
                        step={1}
                        value={job.duration_steps}
                        disabled={busy}
                        onChange={(event) =>
                          updateJob(
                            job.key,
                            "duration_steps",
                            event.target.value,
                          )
                        }
                        className="h-9 w-20 rounded-md border border-slate-600 bg-[#0d0f12] px-2 text-slate-100"
                      />
                    </td>

                    <td className="p-2">
                      <input
                        type="number"
                        min={0}
                        step={1}
                        value={job.arrival_step}
                        disabled={busy}
                        onChange={(event) =>
                          updateJob(
                            job.key,
                            "arrival_step",
                            event.target.value,
                          )
                        }
                        className="h-9 w-24 rounded-md border border-slate-600 bg-[#0d0f12] px-2 text-slate-100"
                      />
                    </td>

                    <td className="p-2">
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        disabled={busy || jobs.length === 1}
                        onClick={() => removeJob(job.key)}
                        className="border-red-500/30 text-red-300 hover:bg-red-500/10"
                      >
                        Sil
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <p className="text-xs leading-5 text-slate-400">
            Large server en fazla 8 CPU ve 16 GB RAM kabul
            eder. Mevcut sunucularda GPU bulunmadığı için GPU
            değeri sıfırdır. Seed manuel görevleri değiştirmez;
            deney kimliği ve modelin rastgele sayı kaynağı için
            tutulur.
          </p>

          {message && (
            <div
              role="status"
              className="rounded-lg border border-emerald-500/30 bg-emerald-500/10 p-3 text-sm text-emerald-300"
            >
              {message}
            </div>
          )}

          {error && (
            <div
              role="alert"
              className="rounded-lg border border-red-500/30 bg-red-500/10 p-3 text-sm text-red-300"
            >
              {error}
            </div>
          )}
        </CardContent>
      </Card>
    </section>
  );
}