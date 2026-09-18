import { useMemo, useState } from "react"

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

interface BenchmarkJob {
  job_id: string
  required_cpu: number
  required_memory_gb: number
  required_gpu_count: number
  duration_steps: number
  arrival_step: number
}

interface BenchmarkSummary {
  algorithm: string
  rank: number
  run_count: number
  completed_runs: number
  failed_runs: number
  mean_waiting: number | null
  std_waiting: number | null
  minimum_waiting: number | null
  maximum_waiting: number | null
  mean_reward: number | null
  mean_elapsed_steps: number | null
  mean_decision_count: number | null
  win_count: number
  exclusive_win_count: number
}

interface BenchmarkResponse {
  base_seed: number
  run_count: number
  input_mode: "manual" | "synthetic"
  workload_strategy: string
  job_count: number
  best_algorithm: string | null
  summaries: BenchmarkSummary[]
}

interface SimulationWithDefinitions {
  input_mode?: "manual" | "synthetic"
  job_definitions?: BenchmarkJob[]
}

const API_URL = "http://127.0.0.1:8000"

const ALGORITHM_COLORS: Record<string, string> = {
  "First Fit": "#4f6f9f",
  "Best Fit": "#71849f",
  "Best Fit RAM": "#9aabc1",
  PPO: "#ff6b0a",
  "PPO Queue": "#ff963d",
}

function formatNumber(
  value: number | null,
  digits = 2,
) {
  if (value === null || !Number.isFinite(value)) {
    return "—"
  }

  return new Intl.NumberFormat("tr-TR", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(value)
}

async function readErrorMessage(response: Response) {
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
    // JSON olmayan yanıtta genel hata mesajı kullanılacak.
  }

  return `API hata kodu: ${response.status}`
}

export function BenchmarkPanel() {
  const { data: simulation } = useSimulation()

  const [baseSeed, setBaseSeed] = useState(42)
  const [runCount, setRunCount] = useState(10)

  const [result, setResult] =
    useState<BenchmarkResponse | null>(null)

  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState("")

  const simulationWithDefinitions =
    simulation as (typeof simulation & SimulationWithDefinitions) | null

  const activeJobs = useMemo(() => {
    if (
      simulationWithDefinitions?.input_mode === "manual" &&
      Array.isArray(
        simulationWithDefinitions.job_definitions,
      ) &&
      simulationWithDefinitions.job_definitions.length > 0
    ) {
      return simulationWithDefinitions.job_definitions
    }

    return undefined
  }, [simulationWithDefinitions])

  const maximumMeanWaiting = Math.max(
    ...(result?.summaries
      .filter(
        (summary) =>
          summary.mean_waiting !== null,
      )
      .map(
        (summary) =>
          summary.mean_waiting as number,
      ) ?? []),
    1,
  )

  async function runBenchmark() {
    if (
      !Number.isInteger(baseSeed) ||
      baseSeed < 0
    ) {
      setError(
        "Başlangıç seed’i 0 veya daha büyük bir tam sayı olmalıdır.",
      )
      return
    }

    if (
      !Number.isInteger(runCount) ||
      runCount < 2 ||
      runCount > 50
    ) {
      setError(
        "Deney sayısı 2 ile 50 arasında olmalıdır.",
      )
      return
    }

    setIsLoading(true)
    setError("")
    setResult(null)

    try {
      const response = await fetch(
        `${API_URL}/api/benchmark`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            Accept: "application/json",
          },
          body: JSON.stringify({
            base_seed: baseSeed,
            run_count: runCount,
            jobs: activeJobs,
          }),
        },
      )

      if (!response.ok) {
        throw new Error(
          await readErrorMessage(response),
        )
      }

      const benchmarkResult =
        (await response.json()) as BenchmarkResponse

      if (
        !Array.isArray(
          benchmarkResult.summaries,
        ) ||
        benchmarkResult.summaries.length === 0
      ) {
        throw new Error(
          "Benchmark API’si sonuç döndürmedi.",
        )
      }

      setResult(benchmarkResult)
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Benchmark çalıştırılamadı.",
      )
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <Card className="border-slate-800 bg-[#171b21] text-slate-100">
      <CardHeader>
        <CardTitle>
          Çoklu deney benchmarkı
        </CardTitle>

        <CardDescription className="text-blue-300/80">
          Algoritmaları birden fazla senaryoda çalıştırarak
          ortalama performanslarını ve kararlılıklarını ölç.
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-6">
        <div
          className={
            activeJobs
              ? "rounded-lg border border-orange-800 bg-orange-950/20 p-4"
              : "rounded-lg border border-slate-700 bg-[#101722] p-4"
          }
        >
          <p className="font-medium">
            {activeJobs
              ? `${activeJobs.length} manuel/Event ID görevi farklı geliş sıralarıyla test edilecek.`
              : "Her deneyde farklı sentetik görev kümesi üretilecek."}
          </p>

          <p className="mt-1 text-sm text-blue-300/80">
            Her deney içerisinde beş algoritma tamamen aynı
            görev kümesini kullanır.
          </p>
        </div>

        <div className="flex flex-wrap items-end gap-3">
          <div className="space-y-2">
            <label
              htmlFor="benchmark-seed"
              className="text-sm font-medium"
            >
              Başlangıç seed’i
            </label>

            <Input
              id="benchmark-seed"
              type="number"
              min={0}
              step={1}
              value={baseSeed}
              disabled={isLoading}
              onChange={(event) =>
                setBaseSeed(
                  Number(event.target.value),
                )
              }
              className="w-40 border-slate-600 bg-[#0b0e12]"
            />
          </div>

          <div className="space-y-2">
            <label
              htmlFor="benchmark-count"
              className="text-sm font-medium"
            >
              Deney sayısı
            </label>

            <Input
              id="benchmark-count"
              type="number"
              min={2}
              max={50}
              step={1}
              value={runCount}
              disabled={isLoading}
              onChange={(event) =>
                setRunCount(
                  Number(event.target.value),
                )
              }
              className="w-32 border-slate-600 bg-[#0b0e12]"
            />
          </div>

          <Button
            type="button"
            onClick={() => void runBenchmark()}
            disabled={isLoading}
            className="bg-orange-500 text-black hover:bg-orange-400"
          >
            {isLoading
              ? `${runCount} deney çalıştırılıyor...`
              : "Benchmarkı başlat"}
          </Button>
        </div>

        <p className="text-xs text-blue-300/80">
          Deney sayısı arttıkça sonuçlar daha güvenilir olur,
          ancak hesaplama süresi de uzar. İlk test için 10 deney
          yeterlidir.
        </p>

        {error !== "" && (
          <div className="rounded-lg border border-red-800 bg-red-950/30 p-4 text-sm text-red-300">
            {error}
          </div>
        )}

        {result !== null && (
          <>
            <div className="grid gap-3 md:grid-cols-4">
              <div className="rounded-lg border border-slate-700 bg-[#101722] p-4">
                <p className="text-xs text-blue-300/80">
                  En iyi yöntem
                </p>

                <p className="mt-1 text-xl font-semibold text-orange-400">
                  {result.best_algorithm ?? "—"}
                </p>
              </div>

              <div className="rounded-lg border border-slate-700 bg-[#101722] p-4">
                <p className="text-xs text-blue-300/80">
                  Deney sayısı
                </p>

                <p className="mt-1 text-xl font-semibold">
                  {result.run_count}
                </p>
              </div>

              <div className="rounded-lg border border-slate-700 bg-[#101722] p-4">
                <p className="text-xs text-blue-300/80">
                  Görev sayısı
                </p>

                <p className="mt-1 text-xl font-semibold">
                  {result.job_count}
                </p>
              </div>

              <div className="rounded-lg border border-slate-700 bg-[#101722] p-4">
                <p className="text-xs text-blue-300/80">
                  Veri kaynağı
                </p>

                <p className="mt-1 text-xl font-semibold">
                  {result.input_mode === "manual"
                    ? "Event ID"
                    : "Sentetik"}
                </p>
              </div>
            </div>

            <div className="rounded-xl border border-slate-700 bg-[#101722] p-5">
              <div className="mb-5">
                <h3 className="font-semibold">
                  Ortalama bekleme karşılaştırması
                </h3>

                <p className="text-sm text-blue-300/80">
                  Daha kısa çubuk daha iyi performansı gösterir.
                </p>
              </div>

              <div className="space-y-5">
                {result.summaries.map((summary) => {
                  const width =
                    summary.mean_waiting === null
                      ? 0
                      : Math.max(
                          (
                            summary.mean_waiting /
                            maximumMeanWaiting
                          ) * 100,
                          1,
                        )

                  return (
                    <div key={summary.algorithm}>
                      <div className="mb-2 flex items-center justify-between gap-4">
                        <span className="font-medium">
                          #{summary.rank}{" "}
                          {summary.algorithm}
                        </span>

                        <span className="font-semibold tabular-nums">
                          {formatNumber(
                            summary.mean_waiting,
                          )}{" "}
                          adım
                        </span>
                      </div>

                      <div className="h-8 overflow-hidden rounded-md bg-[#17243a]">
                        <div
                          className="h-full rounded-md transition-all duration-500"
                          style={{
                            width: `${width}%`,
                            backgroundColor:
                              ALGORITHM_COLORS[
                                summary.algorithm
                              ] ?? "#ff6b0a",
                          }}
                        />
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>

            <div className="overflow-x-auto rounded-xl border border-slate-700">
              <table className="w-full min-w-[1250px] border-collapse text-sm">
                <thead className="bg-[#101b2d] text-blue-200">
                  <tr>
                    <th className="px-4 py-3 text-left">
                      Sıra
                    </th>
                    <th className="px-4 py-3 text-left">
                      Yöntem
                    </th>
                    <th className="px-4 py-3 text-left">
                      Tamamlanan
                    </th>
                    <th className="px-4 py-3 text-left">
                      Ort. bekleme
                    </th>
                    <th className="px-4 py-3 text-left">
                      Sapma
                    </th>
                    <th className="px-4 py-3 text-left">
                      En iyi
                    </th>
                    <th className="px-4 py-3 text-left">
                      En kötü
                    </th>
                    <th className="px-4 py-3 text-left">
                      Ort. ödül
                    </th>
                    <th className="px-4 py-3 text-left">
                      Ort. süre
                    </th>
                    <th className="px-4 py-3 text-left">
                      Kazanma
                    </th>
                  </tr>
                </thead>

                <tbody>
                  {result.summaries.map((summary) => (
                    <tr
                      key={summary.algorithm}
                      className="border-t border-slate-700"
                    >
                      <td className="px-4 py-4 font-semibold text-orange-400">
                        #{summary.rank}
                      </td>

                      <td className="px-4 py-4 font-semibold">
                        {summary.algorithm}
                      </td>

                      <td className="px-4 py-4">
                        {summary.completed_runs} /{" "}
                        {summary.run_count}
                      </td>

                      <td className="px-4 py-4 tabular-nums">
                        {formatNumber(
                          summary.mean_waiting,
                        )}
                      </td>

                      <td className="px-4 py-4 tabular-nums">
                        ±
                        {formatNumber(
                          summary.std_waiting,
                        )}
                      </td>

                      <td className="px-4 py-4 tabular-nums">
                        {formatNumber(
                          summary.minimum_waiting,
                        )}
                      </td>

                      <td className="px-4 py-4 tabular-nums">
                        {formatNumber(
                          summary.maximum_waiting,
                        )}
                      </td>

                      <td className="px-4 py-4 tabular-nums">
                        {formatNumber(
                          summary.mean_reward,
                        )}
                      </td>

                      <td className="px-4 py-4 tabular-nums">
                        {formatNumber(
                          summary.mean_elapsed_steps,
                        )}{" "}
                        adım
                      </td>

                      <td className="px-4 py-4">
                        {summary.win_count} beraber /{" "}
                        {summary.exclusive_win_count} tek
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <p className="text-xs text-blue-300/80">
              Standart sapmanın düşük olması yöntemin farklı
              senaryolarda daha kararlı çalıştığını gösterir.
              Beraber kazanma eşit en iyi sonuçları, tek kazanma
              ise yalnızca o algoritmanın en iyi olduğu deneyleri
              ifade eder.
            </p>
          </>
        )}
      </CardContent>
    </Card>
  )
}