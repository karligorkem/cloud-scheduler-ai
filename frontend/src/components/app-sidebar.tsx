import type { ComponentProps } from "react";

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
} from "@/components/ui/sidebar";

export function AppSidebar(props: ComponentProps<typeof Sidebar>) {
    const links = [
    {
      href: "#overview",
      number: "01",
      title: "Genel görünüm",
      description: "Deneyin anlık özeti",
    },
    {
      href: "#controls",
      number: "02",
      title: "Simülasyon kontrolü",
      description: "Sıfırla ve adım ilerlet",
    },
    {
      href: "#servers",
      number: "03",
      title: "Sunucu kümesi",
      description: "Kaynaklar ve çalışan işler",
    },
    {
      href: "#jobs",
      number: "04",
      title: "Görev yönetimi",
      description: "Kuyruk ve tamamlanan işler",
    },
    {
      href: "#comparison",
      number: "05",
      title: "Karşılaştırma",
      description: "Beş yöntemin sonuçları",
    },
  ];

  return (
    <Sidebar collapsible="offcanvas" {...props}>
      <SidebarHeader className="border-b border-sidebar-border p-5">
        <a
          href="#overview"
          className="flex items-center gap-3 rounded-md focus-visible:outline-2 focus-visible:outline-orange-400"
        >
          <div className="flex size-10 shrink-0 items-center justify-center rounded-xl bg-orange-500 text-sm font-bold text-black">
            CS
          </div>

          <div>
            <div className="text-sm font-semibold text-sidebar-foreground">
              Cloud Scheduler
            </div>

            <div className="mt-1 text-[10px] uppercase tracking-[0.18em] text-slate-400">
              AI Laboratuvarı
            </div>
          </div>
        </a>
      </SidebarHeader>

      <SidebarContent className="gap-6 px-3 py-6">
        <div>
          <p className="mb-3 px-3 text-[10px] font-medium uppercase tracking-[0.18em] text-slate-400">
            Çalışma alanı
          </p>

          <nav
            aria-label="Simülasyon bölümleri"
            className="space-y-2"
          >
            {links.map((link) => (
              <a
                key={link.href}
                href={link.href}
                className="group flex items-center gap-3 rounded-lg border border-transparent px-3 py-3 transition-colors hover:border-sidebar-border hover:bg-sidebar-accent focus-visible:outline-2 focus-visible:outline-orange-400"
              >
                <span className="flex size-8 shrink-0 items-center justify-center rounded-md border border-slate-600/40 bg-slate-800/70 text-xs font-medium text-orange-300">
                  {link.number}
                </span>

                <div>
                  <div className="text-sm font-medium text-slate-200 group-hover:text-white">
                    {link.title}
                  </div>

                  <div className="mt-1 text-[11px] text-slate-400">
                    {link.description}
                  </div>
                </div>
              </a>
            ))}
          </nav>
        </div>

        <div className="mx-1 rounded-xl border border-sidebar-border bg-black/10 p-4">
          <p className="text-xs font-medium text-slate-200">
            Kararlar nasıl uygulanır?
          </p>

          <p className="mt-2 text-xs leading-6 text-slate-400">
            Atama, göreve kaynak ayırır. Bekleme, zamanı bir adım
            ilerletir. Biten görevler kaynaklarını serbest bırakır.
          </p>
        </div>
      </SidebarContent>

      <SidebarFooter className="border-t border-sidebar-border p-5">
        <div className="flex items-center gap-2 text-xs font-medium text-slate-300">
          <span className="size-2 shrink-0 rounded-full bg-orange-400" />
          Sentetik iş yükü simülasyonu
        </div>

        <p className="mt-2 text-[11px] leading-5 text-slate-400">
          Gerçek bulut sunucuları yerine yerel simülasyon kullanılır.
        </p>
      </SidebarFooter>
    </Sidebar>
  );
}