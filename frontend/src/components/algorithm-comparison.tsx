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

interface ComparisonJob {
  job_id: string
  required_cpu: number
  required_memory_gb: number
  required_gpu_count: number
  duration_steps: number
  arrival_step: number
}

interface ComparisonRow {
  algorithm: string
  workload_seed?: number
  completed_count: number
  total_jobs: number
  finished?: boolean
  terminated?: boolean
  truncated: boolean
  elapsed?: number
  elapsed_steps?: number
  current_step?: number
  decision_count: number
  total_reward: number
  average_waiting: number | null
  improvement_vs_first_fit?: number | null
  improvement_percentage?: number | null
}

interface ComparisonResponse {
  seed: number
  workload_seed: number
  input_mode?: "manual" | "synthetic"
  job_count?: number
  results: ComparisonRow[]
}

interface SimulationWithDefinitions {
  input_mode?: "manual" | "synthetic"
  job_definitions?: ComparisonJob[]
}

const API_URL = "http://127.0.0.1:8000"

const BAR_COLORS: Record<string, string> = {
  "First Fit": "#4f6f9f",
  "Best Fit": "#71849f",
  "Best Fit RAM": "#9aabc1",
  PPO: "#ff6b0a",
  "PPO Queue": "#ff963d",
}

function formatNumber(value: number, digits = 2) {
  return new Intl.NumberFormat("tr-TR", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  }).format(value)
}

function getElapsedSteps(row: ComparisonRow) {
  return (
    row.elapsed_steps ??
    row.elapsed ??
    row.current_step ??
    0
  )
}

function getImprovement(row: ComparisonRow) {
  return (
    row.improvement_vs_first_fit ??
    row.improvement_percentage ??
    null
  )
}

function getStatus(row: ComparisonRow) {
  if (row.finished || row.terminated) {
    return "Tamamlandı"
  }

  if (row.truncated) {
    return "Sınırda durduruldu"
  }

  return "Tamamlanmadı"
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
    // JSON olmayan hata yanıtında genel mesaj kullanılacak.
  }

  return `API hata kodu: ${response.status}`
}

export function AlgorithmComparison() {
  const { data: simulation } = useSimulation()

  const [seed, setSeed] = useState(42)
  const [result, setResult] =
    useState<ComparisonResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState("")

  const simulationWithDefinitions =
    simulation as (typeof simulation & SimulationWithDefinitions) | null

  const activeJobs = useMemo(() => {
    if (
      simulationWithDefinitions?.input_mode === "manual" &&
      Array.isArray(simulationWithDefinitions.job_definitions) &&
      simulationWithDefinitions.job_definitions.length > 0
    ) {
      return simulationWithDefinitions.job_definitions
    }

    return undefined
  }, [simulationWithDefinitions])

  const validResults = result?.results.filter(
    (row) =>
      row.average_waiting !== null &&
      Number.isFinite(row.average_waiting),
  ) ?? []

  const maximumWaiting = Math.max(
    ...validResults.map(
      (row) => row.average_waiting as number,
    ),
    1,
  )

  const minimumWaiting =
    validResults.length > 0
      ? Math.min(
          ...validResults.map(
            (row) => row.average_waiting as number,
          ),
        )
      : null

  async function compareAlgorithms() {
    if (!Number.isInteger(seed) || seed < 0) {
      setError(
        "Karşılaştırma seed’i 0 veya daha büyük bir tam sayı olmalıdır.",
      )
      return
    }

    setIsLoading(true)
    setError("")
    setResult(null)

    try {
      const response = await fetch(`${API_URL}/api/compare`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Accept: "application/json",
        },
        body: JSON.stringify({
          seed,
          jobs: activeJobs,
        }),
      })

      if (!response.ok) {
        throw new Error(await readErrorMessage(response))
      }

      const comparison =
        (await response.json()) as ComparisonResponse

      if (
        !Array.isArray(comparison.results) ||
        comparison.results.length === 0
      ) {
        throw new Error(
          "Karşılaştırma API’si sonuç döndürmedi.",
        )
      }

      setResult(comparison)
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Algoritmalar karşılaştırılamadı.",
      )
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <Card className="border-slate-800 bg-[#171b21] text-slate-100">
      <CardHeader>
        <CardTitle>Algoritma karşılaştırması</CardTitle>

        <CardDescription className="text-blue-300/80">
          Beş zamanlama yöntemini aynı görevler üzerinde
          karşılaştır. Daha düşük ortalama bekleme daha iyidir.
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
          <p className="font-medium text-slate-100">
            {activeJobs
              ? `${activeJobs.length} aktif manuel/Event ID görevi beş yöntemde karşılaştırılacak.`
              : "Aktif deney sentetik iş yükü kullanıyor."}
          </p>

          <p className="mt-1 text-sm text-blue-300/80">
            {activeJobs
              ? "Karşılaştırmada her algoritmaya aynı görev listesi gönderilecek."
              : "Karşılaştırmada seçilen seed ile aynı sentetik görevler üretilecek."}
          </p>
        </div>

        <div className="flex flex-wrap items-end gap-3">
          <div className="space-y-2">
            <label
              htmlFor="comparison-seed"
              className="text-sm font-medium"
            >
              Karşılaştırma seed’i
            </label>

            <Input
              id="comparison-seed"
              type="number"
              min={0}
              step={1}
              value={seed}
              disabled={isLoading}
              onChange={(event) =>
                setSeed(Number(event.target.value))
              }
              className="w-40 border-slate-600 bg-[#0b0e12]"
            />
          </div>

          <Button
            type="button"
            onClick={() => void compareAlgorithms()}
            disabled={isLoading}
            className="bg-orange-500 text-black hover:bg-orange-400"
          >
            {isLoading
              ? "Karşılaştırılıyor..."
              : "Beş yöntemi karşılaştır"}
          </Button>
        </div>

        <p className="text-xs text-blue-300/80">
          Her yöntem bağımsız bir simülasyonda çalışır. Mevcut
          canlı deney değiştirilmez. Sonuçlar tek senaryoya aittir;
          genel başarı sıralaması değildir.
        </p>

        {error !== "" && (
          <div className="rounded-lg border border-red-800 bg-red-950/30 p-4 text-sm text-red-300">
            {error}
          </div>
        )}

        {result !== null && (
          <>
            <div className="flex flex-wrap gap-2">
              <span className="rounded-full border border-slate-700 bg-[#101722] px-3 py-1 text-xs text-blue-200">
                Sonuç seed’i: {result.seed}
              </span>

              <span className="rounded-full border border-slate-700 bg-[#101722] px-3 py-1 text-xs text-blue-200">
                Görev seed’i: {result.workload_seed}
              </span>

              <span className="rounded-full border border-slate-700 bg-[#101722] px-3 py-1 text-xs text-blue-200">
                Kaynak:{" "}
                {result.input_mode === "manual"
                  ? "Manuel / Event ID"
                  : "Sentetik"}
              </span>

              <span className="rounded-full border border-orange-800 bg-orange-950/20 px-3 py-1 text-xs text-orange-400">
                Görev sayısı:{" "}
                {result.job_count ??
                  activeJobs?.length ??
                  result.results[0]?.total_jobs ??
                  0}
              </span>
            </div>

            <div className="rounded-xl border border-slate-700 bg-[#101722] p-5">
              <div className="mb-5 flex flex-wrap items-start justify-between gap-3">
                <div>
                  <h3 className="font-semibold">
                    Ortalama bekleme süresi
                  </h3>

                  <p className="text-sm text-blue-300/80">
                    Daha kısa çubuk, daha az bekleme demektir.
                  </p>
                </div>

                {minimumWaiting !== null && (
                  <span className="rounded-full border border-orange-800 bg-orange-950/30 px-3 py-1 text-xs text-orange-400">
                    En düşük:{" "}
                    {formatNumber(minimumWaiting)} adım
                  </span>
                )}
              </div>

              <div className="space-y-5">
                {result.results.map((row) => {
                  const waiting = row.average_waiting
                  const width =
                    waiting === null
                      ? 0
                      : Math.max(
                          (waiting / maximumWaiting) * 100,
                          1,
                        )

                  return (
                    <div key={row.algorithm}>
                      <div className="mb-2 flex items-center justify-between gap-4">
                        <span className="font-medium">
                          {row.algorithm}
                        </span>

                        <span className="font-semibold tabular-nums">
                          {waiting === null
                            ? "Tamamlanmadı"
                            : `${formatNumber(waiting)} adım`}
                        </span>
                      </div>

                      <div className="h-8 overflow-hidden rounded-md bg-[#17243a]">
                        <div
                          className="h-full rounded-md transition-all duration-500"
                          style={{
                            width: `${width}%`,
                            backgroundColor:
                              BAR_COLORS[row.algorithm] ??
                              "#ff6b0a",
                          }}
                        />
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>

            <div className="overflow-x-auto rounded-xl border border-slate-700">
              <table className="w-full min-w-[1050px] border-collapse text-sm">
                <thead className="bg-[#101b2d] text-blue-200">
                  <tr>
                    <th className="px-4 py-3 text-left">
                      Yöntem
                    </th>
                    <th className="px-4 py-3 text-left">
                      Tamamlanan
                    </th>
                    <th className="px-4 py-3 text-left">
                      Durum
                    </th>
                    <th className="px-4 py-3 text-left">
                      Süre
                    </th>
                    <th className="px-4 py-3 text-left">
                      Karar sayısı
                    </th>
                    <th className="px-4 py-3 text-left">
                      Ort. bekleme
                    </th>
                    <th className="px-4 py-3 text-left">
                      Toplam ödül
                    </th>
                    <th className="px-4 py-3 text-left">
                      First Fit’e göre
                    </th>
                  </tr>
                </thead>

                <tbody>
                  {result.results.map((row) => {
                    const improvement = getImprovement(row)

                    return (
                      <tr
                        key={row.algorithm}
                        className="border-t border-slate-700"
                      >
                        <td className="px-4 py-4 font-semibold text-orange-400">
                          {row.algorithm}
                        </td>

                        <td className="px-4 py-4">
                          {row.completed_count} /{" "}
                          {row.total_jobs ??
                           result.job_count ??
                           activeJobs?.length ??
                           0}
                        </td>

                        <td className="px-4 py-4">
                          {getStatus(row)}
                        </td>

                        <td className="px-4 py-4 tabular-nums">
                          {getElapsedSteps(row)} adım
                        </td>

                        <td className="px-4 py-4 tabular-nums">
                          {row.decision_count}
                        </td>

                        <td className="px-4 py-4 tabular-nums">
                          {row.average_waiting === null
                            ? "—"
                            : formatNumber(
                                row.average_waiting,
                              )}
                        </td>

                        <td className="px-4 py-4 tabular-nums">
                          {formatNumber(row.total_reward)}
                        </td>

                        <td className="px-4 py-4 tabular-nums">
                          {improvement === null
                            ? "—"
                            : `%${formatNumber(improvement)}`}
                        </td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>

            <p className="text-xs text-blue-300/80">
              Pozitif iyileşme daha az bekleme, negatif değer daha
              fazla bekleme anlamına gelir. Tamamlanmayan deneylerde
              bekleme karşılaştırması yapılmaz.
            </p>
          </>
        )}
      </CardContent>
    </Card>
  )
}