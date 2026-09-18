import { useCallback, useEffect, useMemo, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

interface SystemEvent {
  identity: string;
  log_name: string;
  record_id: number;
  event_id: number;
  provider: string;
  level: string;
  level_number: number | null;
  time_created: string;
  message: string;
  collected_at: string;
}

interface SystemEventsResponse {
  count?: number;
  collected_count?: number;
  saved_count?: number;
  event_id_filter?: number | null;
  events: SystemEvent[];
}

type LevelFilter = "all" | "critical" | "error" | "warning" | "information";

const API_URL = "http://127.0.0.1:8000/api/system-events";

function eventLevel(event: SystemEvent): LevelFilter {
  if (event.level_number === 1) return "critical";
  if (event.level_number === 2) return "error";
  if (event.level_number === 3) return "warning";
  return "information";
}

function levelLabel(event: SystemEvent): string {
  const level = eventLevel(event);

  if (level === "critical") return "Kritik";
  if (level === "error") return "Hata";
  if (level === "warning") return "Uyarı";
  return event.level || "Bilgi";
}

function levelClass(event: SystemEvent): string {
  const level = eventLevel(event);

  if (level === "critical") {
    return "border-red-500/40 bg-red-500/15 text-red-300";
  }

  if (level === "error") {
    return "border-red-500/30 bg-red-500/10 text-red-300";
  }

  if (level === "warning") {
    return "border-orange-500/40 bg-orange-500/10 text-orange-300";
  }

  return "border-slate-600 bg-[#111b2c] text-slate-300";
}

function formatDate(value: string): string {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) return value || "—";

  return date.toLocaleString("tr-TR", {
    dateStyle: "short",
    timeStyle: "medium",
  });
}

async function apiError(response: Response): Promise<string> {
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

export function SystemEvents() {
  const [events, setEvents] = useState<SystemEvent[]>([]);
  const [eventIdInput, setEventIdInput] = useState("");
  const [eventIdFilter, setEventIdFilter] = useState("");
  const [search, setSearch] = useState("");
  const [levelFilter, setLevelFilter] =
    useState<LevelFilter>("all");

  const [loading, setLoading] = useState(true);
  const [collecting, setCollecting] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const fetchEvents = useCallback(
    async (selectedEventId: string) => {
      setLoading(true);
      setError("");

      try {
        const parameters = new URLSearchParams({
          limit: "100",
        });

        if (selectedEventId !== "") {
          parameters.set("event_id", selectedEventId);
        }

        const response = await fetch(
          `${API_URL}?${parameters.toString()}`,
          {
            cache: "no-store",
          },
        );

        if (!response.ok) {
          throw new Error(await apiError(response));
        }

        const result: SystemEventsResponse =
          await response.json();

        setEvents(result.events);
      } catch (caughtError) {
        setError(
          caughtError instanceof TypeError
            ? "Backend'e bağlanılamadı. 8000 portunu kontrol et."
            : caughtError instanceof Error
              ? caughtError.message
              : "Sistem olayları alınamadı.",
        );
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  useEffect(() => {
    void fetchEvents("");
  }, [fetchEvents]);

  async function collectEvents(): Promise<void> {
    if (collecting) return;

    setCollecting(true);
    setError("");
    setMessage("");

    try {
      const response = await fetch(
        `${API_URL}/collect?limit=100`,
        {
          method: "POST",
        },
      );

      if (!response.ok) {
        throw new Error(await apiError(response));
      }

      const result: SystemEventsResponse =
        await response.json();

      setMessage(
        `${result.collected_count ?? 0} Windows olayı okundu ve kaydedildi.`,
      );

      await fetchEvents(eventIdFilter);
    } catch (caughtError) {
      setError(
        caughtError instanceof TypeError
          ? "Backend'e bağlanılamadı. 8000 portunu kontrol et."
          : caughtError instanceof Error
            ? caughtError.message
            : "Windows olayları toplanamadı.",
      );
    } finally {
      setCollecting(false);
    }
  }

  function applyEventIdFilter(): void {
    const trimmedValue = eventIdInput.trim();

    if (
      trimmedValue !== "" &&
      (!Number.isInteger(Number(trimmedValue)) ||
        Number(trimmedValue) < 0)
    ) {
      setError("Event ID sıfır veya pozitif bir tam sayı olmalı.");
      return;
    }

    setEventIdFilter(trimmedValue);
    setError("");
    setMessage("");
    void fetchEvents(trimmedValue);
  }

  function clearFilters(): void {
    setEventIdInput("");
    setEventIdFilter("");
    setSearch("");
    setLevelFilter("all");
    setError("");
    setMessage("");
    void fetchEvents("");
  }

  const visibleEvents = useMemo(() => {
    const normalizedSearch = search.trim().toLocaleLowerCase("tr-TR");

    return events.filter((event) => {
      const matchesLevel =
        levelFilter === "all" ||
        eventLevel(event) === levelFilter;

      const searchableText = [
        event.event_id,
        event.provider,
        event.log_name,
        event.level,
        event.message,
      ]
        .join(" ")
        .toLocaleLowerCase("tr-TR");

      const matchesSearch =
        normalizedSearch === "" ||
        searchableText.includes(normalizedSearch);

      return matchesLevel && matchesSearch;
    });
  }, [events, levelFilter, search]);

  const errorCount = events.filter(
    (event) =>
      event.level_number === 1 ||
      event.level_number === 2,
  ).length;

  const warningCount = events.filter(
    (event) => event.level_number === 3,
  ).length;

  return (
    <section
      id="system-events"
      aria-labelledby="system-events-title"
      className="min-w-0 scroll-mt-20 px-4 lg:px-6"
    >
      <Card className="min-w-0 border-slate-700/70 bg-[#191c22]">
        <CardHeader>
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <CardTitle
                id="system-events-title"
                className="text-slate-100"
              >
                Windows sistem olayları
              </CardTitle>

              <CardDescription className="mt-1 text-slate-400">
                System ve Application günlüklerinden alınan kalıcı
                Event ID kayıtları.
              </CardDescription>
            </div>

            <Button
              type="button"
              disabled={collecting}
              onClick={() => void collectEvents()}
              className="bg-orange-500 text-black hover:bg-orange-400"
            >
              {collecting
                ? "Olaylar okunuyor…"
                : "Windows olaylarını topla"}
            </Button>
          </div>
        </CardHeader>

        <CardContent className="min-w-0 space-y-5">
          <div className="grid gap-3 sm:grid-cols-3">
            <div className="rounded-lg border border-slate-700 bg-[#111820] p-4">
              <p className="text-xs text-slate-400">
                Yüklenen kayıt
              </p>
              <p className="mt-1 text-2xl font-semibold tabular-nums text-slate-100">
                {events.length}
              </p>
            </div>

            <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-4">
              <p className="text-xs text-red-300">
                Kritik ve hata
              </p>
              <p className="mt-1 text-2xl font-semibold tabular-nums text-red-300">
                {errorCount}
              </p>
            </div>

            <div className="rounded-lg border border-orange-500/20 bg-orange-500/5 p-4">
              <p className="text-xs text-orange-300">
                Uyarı
              </p>
              <p className="mt-1 text-2xl font-semibold tabular-nums text-orange-300">
                {warningCount}
              </p>
            </div>
          </div>

          <div className="flex flex-wrap items-end gap-3">
            <div className="space-y-2">
              <label
                htmlFor="system-event-id"
                className="block text-sm font-medium text-slate-200"
              >
                Event ID
              </label>

              <input
                id="system-event-id"
                type="number"
                min={0}
                step={1}
                value={eventIdInput}
                onChange={(event) =>
                  setEventIdInput(event.target.value)
                }
                onKeyDown={(event) => {
                  if (event.key === "Enter") {
                    applyEventIdFilter();
                  }
                }}
                placeholder="Örn. 1000"
                className="h-10 w-40 rounded-lg border border-slate-600 bg-[#0d0f12] px-3 text-sm text-slate-100 outline-none focus:border-orange-500"
              />
            </div>

            <div className="min-w-[200px] flex-1 space-y-2">
              <label
                htmlFor="system-event-search"
                className="block text-sm font-medium text-slate-200"
              >
                Metin ara
              </label>

              <input
                id="system-event-search"
                type="search"
                value={search}
                onChange={(event) => setSearch(event.target.value)}
                placeholder="Kaynak, açıklama veya günlük ara"
                className="h-10 w-full rounded-lg border border-slate-600 bg-[#0d0f12] px-3 text-sm text-slate-100 outline-none focus:border-orange-500"
              />
            </div>

            <div className="space-y-2">
              <label
                htmlFor="system-event-level"
                className="block text-sm font-medium text-slate-200"
              >
                Seviye
              </label>

              <select
                id="system-event-level"
                value={levelFilter}
                onChange={(event) =>
                  setLevelFilter(
                    event.target.value as LevelFilter,
                  )
                }
                className="h-10 rounded-lg border border-slate-600 bg-[#0d0f12] px-3 text-sm text-slate-100 outline-none focus:border-orange-500"
              >
                <option value="all">Tümü</option>
                <option value="critical">Kritik</option>
                <option value="error">Hata</option>
                <option value="warning">Uyarı</option>
                <option value="information">Bilgi</option>
              </select>
            </div>

            <Button
              type="button"
              variant="secondary"
              onClick={applyEventIdFilter}
              disabled={loading}
            >
              Event ID filtrele
            </Button>

            <Button
              type="button"
              variant="outline"
              onClick={clearFilters}
              disabled={loading}
            >
              Filtreleri temizle
            </Button>
          </div>

          {eventIdFilter !== "" && (
            <p className="text-xs text-orange-400">
              Yalnızca Event ID {eventIdFilter} gösteriliyor.
            </p>
          )}

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

          {loading ? (
            <div
              role="status"
              className="rounded-lg border border-slate-700 p-6 text-sm text-slate-400"
            >
              Sistem olayları yükleniyor…
            </div>
          ) : visibleEvents.length === 0 ? (
            <div className="rounded-lg border border-dashed border-slate-700 p-8 text-center text-sm text-slate-400">
              Bu filtrelere uygun kayıt bulunamadı. Önce Windows
              olaylarını toplamayı dene.
            </div>
          ) : (
            <div className="min-w-0 overflow-x-auto rounded-xl border border-slate-700">
              <table className="w-full min-w-[1050px] text-left text-sm">
                <thead className="bg-[#111b2c] text-xs text-slate-300">
                  <tr>
                    <th scope="col" className="px-4 py-3">
                      Zaman
                    </th>
                    <th scope="col" className="px-4 py-3">
                      Günlük
                    </th>
                    <th scope="col" className="px-4 py-3">
                      Event ID
                    </th>
                    <th scope="col" className="px-4 py-3">
                      Seviye
                    </th>
                    <th scope="col" className="px-4 py-3">
                      Kaynak
                    </th>
                    <th scope="col" className="px-4 py-3">
                      Açıklama
                    </th>
                  </tr>
                </thead>

                <tbody>
                  {visibleEvents.map((event) => (
                    <tr
                      key={event.identity}
                      className="border-t border-slate-700/70 align-top text-slate-200 even:bg-white/[0.02]"
                    >
                      <td className="whitespace-nowrap px-4 py-4 text-xs text-slate-300">
                        {formatDate(event.time_created)}
                      </td>

                      <td className="whitespace-nowrap px-4 py-4">
                        {event.log_name}
                      </td>

                      <td className="px-4 py-4 font-semibold tabular-nums text-orange-400">
                        {event.event_id}
                      </td>

                      <td className="px-4 py-4">
                        <Badge
                          variant="outline"
                          className={levelClass(event)}
                        >
                          {levelLabel(event)}
                        </Badge>
                      </td>

                      <td className="max-w-[240px] px-4 py-4 text-xs text-slate-300">
                        {event.provider}
                      </td>

                      <td className="max-w-[460px] px-4 py-4">
                        <details>
                          <summary className="cursor-pointer text-xs leading-5 text-slate-300 hover:text-orange-400">
                            {event.message.length > 140
                              ? `${event.message.slice(0, 140)}…`
                              : event.message}
                          </summary>

                          {event.message.length > 140 && (
                            <p className="mt-3 whitespace-pre-wrap rounded-lg bg-[#0d0f12] p-3 text-xs leading-5 text-slate-300">
                              {event.message}
                            </p>
                          )}
                        </details>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <p className="text-xs leading-5 text-slate-400">
            Event ID tek başına yeterli değildir. Olayın anlamı günlük,
            kaynak, seviye ve açıklamayla birlikte değerlendirilir.
            Toplanan kayıtlar SQLite veritabanında saklanır.
          </p>
        </CardContent>
      </Card>
    </section>
  );
}