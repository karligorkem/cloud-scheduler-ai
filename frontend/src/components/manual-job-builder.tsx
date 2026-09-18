import { useState } from "react"

import { useSimulation } from "@/components/simulation-provider"
import { Button } from "@/components/ui/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import { Input } from "@/components/ui/input"

interface ManualJob {
  job_id: string
  required_cpu: number
  required_memory_gb: number
  required_gpu_count: number
  duration_steps: number
  arrival_step: number
}

interface WindowsWorkloadResponse {
  source?: string
  event_count?: number
  job_count?: number
  jobs: ManualJob[]
}

const API_URL = "http://127.0.0.1:8000"

function createEmptyJob(index: number): ManualJob {
  return {
    job_id: `manuel-${index}`,
    required_cpu: 1,
    required_memory_gb: 2,
    required_gpu_count: 0,
    duration_steps: 2,
    arrival_step: 0,
  }
}

async function readErrorMessage(response: Response): Promise<string> {
  try {
    const result = (await response.json()) as {
      detail?: string | Array<{ msg?: string }>
    }

    if (typeof result.detail === "string") {
      return result.detail
    }

    if (Array.isArray(result.detail)) {
      return result.detail
        .map((item) => item.msg ?? "Geçersiz veri")
        .join(", ")
    }
  } catch {
    // Yanıt JSON değilse genel hata mesajı kullanılacak.
  }

  return `API hata kodu: ${response.status}`
}

export function ManualJobBuilder() {
  const { refresh } = useSimulation()

  const [algorithm, setAlgorithm] = useState("First Fit")
  const [seed, setSeed] = useState(42)

  const [jobs, setJobs] = useState<ManualJob[]>([
    {
      job_id: "manuel-1",
      required_cpu: 2,
      required_memory_gb: 4,
      required_gpu_count: 0,
      duration_steps: 3,
      arrival_step: 0,
    },
    {
      job_id: "manuel-2",
      required_cpu: 4,
      required_memory_gb: 8,
      required_gpu_count: 0,
      duration_steps: 5,
      arrival_step: 1,
    },
  ])

  const [isLoadingEvents, setIsLoadingEvents] = useState(false)
  const [isStarting, setIsStarting] = useState(false)
  const [message, setMessage] = useState("")
  const [error, setError] = useState("")

  function updateJob<K extends keyof ManualJob>(
    index: number,
    field: K,
    value: ManualJob[K],
  ) {
    setJobs((currentJobs) =>
      currentJobs.map((job, jobIndex) =>
        jobIndex === index
          ? {
              ...job,
              [field]: value,
            }
          : job,
      ),
    )
  }

  function addJob() {
    setJobs((currentJobs) => [
      ...currentJobs,
      createEmptyJob(currentJobs.length + 1),
    ])

    setMessage("")
    setError("")
  }

  function removeJob(index: number) {
    setJobs((currentJobs) =>
      currentJobs.filter((_, jobIndex) => jobIndex !== index),
    )

    setMessage("")
    setError("")
  }

  function validateJobs(): string | null {
    if (jobs.length === 0) {
      return "En az bir görev eklemelisin."
    }

    const normalizedIds = jobs.map((job) => job.job_id.trim())

    if (normalizedIds.some((jobId) => jobId.length === 0)) {
      return "Görev adları boş bırakılamaz."
    }

    if (new Set(normalizedIds).size !== normalizedIds.length) {
      return "Görev adları birbirinden farklı olmalıdır."
    }

    for (const job of jobs) {
      if (
        !Number.isFinite(job.required_cpu) ||
        job.required_cpu < 1 ||
        job.required_cpu > 8
      ) {
        return `${job.job_id}: CPU değeri 1 ile 8 arasında olmalıdır.`
      }

      if (
        !Number.isFinite(job.required_memory_gb) ||
        job.required_memory_gb < 0.5 ||
        job.required_memory_gb > 16
      ) {
        return `${job.job_id}: RAM değeri 0.5 ile 16 GB arasında olmalıdır.`
      }

      if (job.required_gpu_count !== 0) {
        return `${job.job_id}: Mevcut sunucularda GPU bulunmadığı için GPU değeri 0 olmalıdır.`
      }

      if (
        !Number.isInteger(job.duration_steps) ||
        job.duration_steps < 1
      ) {
        return `${job.job_id}: Süre en az 1 tam sayı olmalıdır.`
      }

      if (
        !Number.isInteger(job.arrival_step) ||
        job.arrival_step < 0
      ) {
        return `${job.job_id}: Geliş adımı 0 veya daha büyük bir tam sayı olmalıdır.`
      }
    }

    return null
  }

  async function fillFromWindowsEvents() {
    setIsLoadingEvents(true)
    setMessage("")
    setError("")

    try {
      const response = await fetch(
        `${API_URL}/api/system-events/workload?limit=20`,
        {
          method: "GET",
          cache: "no-store",
        },
      )

      if (!response.ok) {
        throw new Error(await readErrorMessage(response))
      }

      const result = (await response.json()) as WindowsWorkloadResponse

      if (!Array.isArray(result.jobs) || result.jobs.length === 0) {
        throw new Error(
          "Windows olaylarından görev üretilemedi. Önce olayları toplamalısın.",
        )
      }

      const eventJobs = result.jobs.map((job, index) => ({
        job_id: String(
          job.job_id || `windows-event-${index + 1}`,
        ),
        required_cpu: Number(job.required_cpu),
        required_memory_gb: Number(job.required_memory_gb),
        required_gpu_count: 0,
        duration_steps: Number(job.duration_steps),
        arrival_step: Number(job.arrival_step),
      }))

      setJobs(eventJobs)
      setMessage(
        `${eventJobs.length} Windows olayı görev tablosuna aktarıldı.`,
      )
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Windows olayları alınamadı.",
      )
    } finally {
      setIsLoadingEvents(false)
    }
  }

  async function startExperiment() {
    const validationError = validateJobs()

    if (validationError !== null) {
      setError(validationError)
      setMessage("")
      return
    }

    if (!Number.isInteger(seed) || seed < 0) {
      setError("Seed değeri 0 veya daha büyük bir tam sayı olmalıdır.")
      setMessage("")
      return
    }

    setIsStarting(true)
    setMessage("")
    setError("")

    try {
      const response = await fetch(`${API_URL}/api/reset`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({
          seed,
          algorithm,
          jobs: jobs.map((job) => ({
            ...job,
            job_id: job.job_id.trim(),
          })),
        }),
      })

      if (!response.ok) {
        throw new Error(await readErrorMessage(response))
      }

      await response.json()
      await refresh()

      setMessage(
        `${jobs.length} manuel görevle ${algorithm} deneyi başlatıldı.`,
      )
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Deney başlatılamadı.",
      )
    } finally {
      setIsStarting(false)
    }
  }

  return (
    <Card className="border-slate-800 bg-[#171b21] text-slate-100">
      <CardHeader>
        <CardTitle>Manuel iş yükü oluştur</CardTitle>

        <CardDescription className="text-blue-300/80">
          Simülasyona gönderilecek görevleri ve kaynak ihtiyaçlarını
          kendin belirle.
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-5">
        <div className="flex flex-wrap items-end gap-3">
          <div className="space-y-2">
            <label
              htmlFor="manual-algorithm"
              className="text-sm font-medium text-slate-100"
            >
              Zamanlama algoritması
            </label>

            <select
              id="manual-algorithm"
              value={algorithm}
              onChange={(event) => setAlgorithm(event.target.value)}
              disabled={isStarting}
              className="h-10 min-w-48 rounded-md border border-slate-600 bg-[#0b0e12] px-3 text-sm text-slate-100 outline-none focus:border-orange-500"
            >
              <option value="First Fit">First Fit</option>
              <option value="Best Fit">Best Fit</option>
              <option value="Best Fit RAM">Best Fit RAM</option>
              <option value="PPO">PPO</option>
              <option value="PPO Queue">PPO Queue</option>
            </select>
          </div>

          <div className="space-y-2">
            <label
              htmlFor="manual-seed"
              className="text-sm font-medium text-slate-100"
            >
              Deney seed’i
            </label>

            <Input
              id="manual-seed"
              type="number"
              min={0}
              step={1}
              value={seed}
              disabled={isStarting}
              onChange={(event) =>
                setSeed(Number(event.target.value))
              }
              className="w-40 border-slate-600 bg-[#0b0e12]"
            />
          </div>

          <Button
            type="button"
            variant="outline"
            onClick={addJob}
            disabled={isStarting || isLoadingEvents}
            className="border-slate-600 bg-slate-800 text-slate-100 hover:bg-slate-700"
          >
            + Görev ekle
          </Button>

          <Button
            type="button"
            variant="outline"
            onClick={() => void fillFromWindowsEvents()}
            disabled={isStarting || isLoadingEvents}
            className="border-slate-600 bg-slate-800 text-orange-400 hover:bg-slate-700 hover:text-orange-300"
          >
            {isLoadingEvents
              ? "Olaylar yükleniyor..."
              : "Windows olaylarından doldur"}
          </Button>

          <Button
            type="button"
            onClick={() => void startExperiment()}
            disabled={
              isStarting ||
              isLoadingEvents ||
              jobs.length === 0
            }
            className="bg-orange-500 text-black hover:bg-orange-400"
          >
            {isStarting
              ? "Deney başlatılıyor..."
              : "Bu görevlerle deneyi başlat"}
          </Button>
        </div>

        <div className="overflow-x-auto rounded-xl border border-slate-700">
          <table className="w-full min-w-[1100px] border-collapse text-sm">
            <thead className="bg-[#101b2d] text-blue-200">
              <tr>
                <th className="px-3 py-3 text-left">Görev adı</th>
                <th className="px-3 py-3 text-left">CPU</th>
                <th className="px-3 py-3 text-left">RAM (GB)</th>
                <th className="px-3 py-3 text-left">GPU</th>
                <th className="px-3 py-3 text-left">Süre</th>
                <th className="px-3 py-3 text-left">Geliş adımı</th>
                <th className="px-3 py-3 text-center">İşlem</th>
              </tr>
            </thead>

            <tbody>
              {jobs.map((job, index) => (
                <tr
                  key={`${job.job_id}-${index}`}
                  className="border-t border-slate-700"
                >
                  <td className="p-2">
                    <Input
                      value={job.job_id}
                      disabled={isStarting}
                      onChange={(event) =>
                        updateJob(
                          index,
                          "job_id",
                          event.target.value,
                        )
                      }
                      className="min-w-52 border-slate-600 bg-[#0b0e12]"
                    />
                  </td>

                  <td className="p-2">
                    <Input
                      type="number"
                      min={1}
                      max={8}
                      step={1}
                      value={job.required_cpu}
                      disabled={isStarting}
                      onChange={(event) =>
                        updateJob(
                          index,
                          "required_cpu",
                          Number(event.target.value),
                        )
                      }
                      className="w-24 border-slate-600 bg-[#0b0e12]"
                    />
                  </td>

                  <td className="p-2">
                    <Input
                      type="number"
                      min={0.5}
                      max={16}
                      step={0.5}
                      value={job.required_memory_gb}
                      disabled={isStarting}
                      onChange={(event) =>
                        updateJob(
                          index,
                          "required_memory_gb",
                          Number(event.target.value),
                        )
                      }
                      className="w-28 border-slate-600 bg-[#0b0e12]"
                    />
                  </td>

                  <td className="p-2">
                    <Input
                      type="number"
                      min={0}
                      max={0}
                      step={1}
                      value={job.required_gpu_count}
                      disabled
                      className="w-24 border-slate-700 bg-[#10182a] text-blue-300"
                    />
                  </td>

                  <td className="p-2">
                    <Input
                      type="number"
                      min={1}
                      step={1}
                      value={job.duration_steps}
                      disabled={isStarting}
                      onChange={(event) =>
                        updateJob(
                          index,
                          "duration_steps",
                          Number(event.target.value),
                        )
                      }
                      className="w-24 border-slate-600 bg-[#0b0e12]"
                    />
                  </td>

                  <td className="p-2">
                    <Input
                      type="number"
                      min={0}
                      step={1}
                      value={job.arrival_step}
                      disabled={isStarting}
                      onChange={(event) =>
                        updateJob(
                          index,
                          "arrival_step",
                          Number(event.target.value),
                        )
                      }
                      className="w-28 border-slate-600 bg-[#0b0e12]"
                    />
                  </td>

                  <td className="p-2 text-center">
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => removeJob(index)}
                      disabled={isStarting}
                      className="border-slate-600 bg-slate-800 text-red-400 hover:bg-red-950 hover:text-red-300"
                    >
                      Sil
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <p className="text-xs text-blue-300/80">
          Large server en fazla 8 CPU ve 16 GB RAM kabul eder.
          Mevcut sunucularda GPU bulunmadığı için GPU değeri sıfırdır.
          Seed manuel görevleri değiştirmez; deney kimliği ve modelin
          rastgele sayı kaynağı için kullanılır.
        </p>

        {message !== "" && (
          <div className="rounded-md border border-emerald-700 bg-emerald-950/40 px-4 py-3 text-sm text-emerald-300">
            {message}
          </div>
        )}

        {error !== "" && (
          <div className="rounded-md border border-red-700 bg-red-950/40 px-4 py-3 text-sm text-red-300">
            {error}
          </div>
        )}
      </CardContent>
    </Card>
  )
}