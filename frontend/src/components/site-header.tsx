import { SidebarTrigger } from "@/components/ui/sidebar";

export function SiteHeader() {
  return (
    <header className="flex min-h-16 shrink-0 items-center justify-between gap-4 border-b border-border px-4 lg:px-6">
      <div className="flex items-center gap-3">
        <SidebarTrigger aria-label="Yan menüyü aç veya kapat" />

        <div className="h-5 w-px bg-border" />

        <div>
          <h1 className="text-sm font-semibold">
            Simülasyon merkezi
          </h1>

          <p className="mt-0.5 text-xs text-muted-foreground">
            Görev atama ve kaynak yönetimi
          </p>
        </div>
      </div>

      <span className="hidden rounded-full border border-orange-500/30 bg-orange-500/10 px-3 py-1 text-xs font-medium text-orange-300 sm:inline-flex">
        Cloud Scheduler AI
      </span>
    </header>
  );
}