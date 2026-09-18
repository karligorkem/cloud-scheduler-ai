import { useState } from "react";

import { useSimulation } from "@/components/simulation-provider";
import type { SimulationJob } from "@/components/simulation-provider";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

type Tab = "waiting" | "running" | "completed";

const statusNames: Record<string, string> = {
  waiting: "Bekliyor",
  running: "Çalışıyor",
  completed: "Tamamlandı",
  failed: "Başarısız",
};

const statusColors: Record<string, string> = {
  waiting: "border-orange-500/30 bg-orange-500/10 text-orange-300",
  running: "border-slate-500/40 bg-[#202c40] text-slate-200",
  completed: "border-slate-600 bg-slate-800/50 text-slate-300",
  failed: "border-red-500/30 bg-red-500/10 text-red-300",
};

export function JobTable() {
  const {
    data: snapshot,
    error,
    refresh,
  } = useSimulation();

  const [tab, setTab] = useState<Tab>("waiting");
  const [search, setSearch] = useState("");

  // Sunuculardaki çalışan görevleri tek listede birleştir.
  const runningJobs =
    snapshot?.servers.flatMap((server) => server.running_jobs) ?? [];

  const groups: Record<Tab, SimulationJob[]> = {
    waiting: snapshot?.queue ?? [],
    running: runningJobs,
    completed: snapshot?.completed_jobs ?? [],
  };

  const tabs: { key: Tab; label: string }[] = [
    { key: "waiting", label: "Bekleyen" },
    { key: "running", label: "Çalışan" },
    { key: "completed", label: "Tamamlanan" },
  ];

  // Arama yalnızca seçili sekmenin görünümünü filtreler.
  const query = search.trim().toLowerCase();

  const visibleJobs = groups[tab].filter((job) =>
    job.id.toLowerCase().includes(query),
  );

  return (
    <section id="jobs" className="scroll-mt-6 px-4 lg:px-6">
      <Card className="overflow-hidden border-[#333943] bg-[#191c22] text-slate-100">
        <CardHeader>
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <CardTitle>Görev yönetimi</CardTitle>

              <CardDescription className="mt-2 text-slate-400">
                Görevlerin kuyruktan tamamlanmaya kadar olan durumunu izle.
              </CardDescription>
            </div>

            {snapshot && !error && (
              <Badge
                variant="outline"
                className="border-[#35445d] bg-[#202c40] text-slate-300"
              >
                Karar #{snapshot.decision_count}
              </Badge>
            )}
          </div>
        </CardHeader>

        <CardContent className="space-y-5">
          {error ? (
            <div className="rounded-lg border border-orange-500/30 bg-orange-500/10 p-4">
              <p role="alert" className="text-sm text-orange-200">
                {error}
              </p>

              <Button
                type="button"
                className="mt-3"
                onClick={() => void refresh()}
              >
                Tekrar bağlan
              </Button>
            </div>
          ) : !snapshot ? (
            <p role="status" className="py-8 text-sm text-slate-400">
              Görevler yükleniyor…
            </p>
          ) : (
            <>
              <div className="flex flex-wrap items-end justify-between gap-4">
                <div
                  className="flex flex-wrap gap-2"
                  role="group"
                  aria-label="Görev durumu filtresi"
                >
                  {tabs.map((item) => (
                    <Button
                      key={item.key}
                      type="button"
                      variant={tab === item.key ? "default" : "outline"}
                      aria-pressed={tab === item.key}
                      onClick={() => setTab(item.key)}
                    >
                      {item.label} ({groups[item.key].length})
                    </Button>
                  ))}
                </div>

                <div className="space-y-2">
                  <label
                    htmlFor="job-search"
                    className="block text-xs text-slate-400"
                  >
                    Görev kimliğiyle ara
                  </label>

                  <input
                    id="job-search"
                    type="search"
                    value={search}
                    onChange={(event) => setSearch(event.target.value)}
                    placeholder="Örneğin job-3"
                    className="h-9 w-full rounded-md border border-[#444d5c] bg-[#0d0f12] px-3 text-sm outline-none placeholder:text-slate-500 focus-visible:ring-2 focus-visible:ring-orange-400 sm:w-52"
                  />
                </div>
              </div>

              <div className="max-h-[440px] overflow-auto rounded-lg border border-[#333943]">
                <table className="w-full whitespace-nowrap text-left text-sm">
                  <caption className="sr-only">
                    {statusNames[tab]} görevlerin kaynak ve atama bilgileri
                  </caption>

                  <thead className="sticky top-0 z-10 bg-[#111b2c] text-xs text-slate-300">
                    <tr>
                      {[
                        "Görev",
                        "Durum",
                        "CPU",
                        "RAM",
                        "GPU",
                        "Geliş adımı",
                        "Kalan çalışma",
                        "Sunucu",
                      ].map((heading) => (
                        <th
                          key={heading}
                          scope="col"
                          className="px-4 py-3 font-medium"
                        >
                          {heading}
                        </th>
                      ))}
                    </tr>
                  </thead>

                  <tbody>
                    {visibleJobs.length === 0 ? (
                      <tr>
                        <td
                          colSpan={8}
                          className="px-4 py-12 text-center text-slate-400"
                        >
                          {query
                            ? "Bu sekmede aramana uyan görev bulunamadı."
                            : "Bu durumda henüz görev yok."}
                        </td>
                      </tr>
                    ) : (
                      visibleJobs.map((job) => (
                        <tr
                          key={job.id}
                          className="border-t border-[#333943] transition-colors hover:bg-[#202c40]/50"
                        >
                          <td className="px-4 py-3 font-medium text-orange-300">
                            {job.id}
                          </td>

                          <td className="px-4 py-3">
                            <Badge
                              variant="outline"
                              className={statusColors[job.status] ?? ""}
                            >
                              {statusNames[job.status] ?? job.status}
                            </Badge>
                          </td>

                          <td className="px-4 py-3">
                            {job.required_cpu}
                          </td>

                          <td className="px-4 py-3">
                            {job.required_memory_gb} GB
                          </td>

                          <td className="px-4 py-3">
                            {job.required_gpu_count}
                          </td>

                          <td className="px-4 py-3">
                            {job.arrival_step}
                          </td>

                          <td className="px-4 py-3">
                            {job.remaining_steps} adım
                          </td>

                          <td className="px-4 py-3 text-slate-400">
                            {job.assigned_server_id ?? "Atanmadı"}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>

              <div className="flex flex-wrap justify-between gap-2 text-xs text-slate-400">
                <span>
                  {visibleJobs.length} / {groups[tab].length} görev gösteriliyor
                </span>

                <span>
                  Henüz gelmeyen: {snapshot.pending_count} görev
                </span>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </section>
  );
}