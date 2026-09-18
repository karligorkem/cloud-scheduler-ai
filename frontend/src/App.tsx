import { AppSidebar } from "@/components/app-sidebar";
import { SectionCards } from "@/components/section-cards";
import { SimulationControls } from "@/components/simulation-controls";
import { ServerCards } from "@/components/server-cards";
import { JobTable } from "@/components/job-table";
import { AlgorithmComparison } from "@/components/algorithm-comparison";
import { SiteHeader } from "@/components/site-header";
import { SimulationProvider } from "@/components/simulation-provider";
import { ResourceHistoryChart } from "@/components/resource-history-chart";
import { ManualJobBuilder } from "@/components/manual-job-builder";
import {
  SidebarInset,
  SidebarProvider,
} from "@/components/ui/sidebar";
import { SystemEvents } from "@/components/system-events";
export default function App() {
  return (
    <SimulationProvider>
      <SidebarProvider>
        <AppSidebar variant="inset" />

        <SidebarInset>
          <SiteHeader />

          <main className="flex flex-1 flex-col">
            <div className="@container/main flex flex-1 flex-col gap-6 py-6">
              <section
                id="overview"
                aria-label="Simülasyon özeti"
                className="scroll-mt-6"
              >
                <SectionCards />
              </section>

              <section
                id="controls"
                aria-label="Simülasyon kontrolleri"
                className="scroll-mt-6"
              >
                <ManualJobBuilder />
                 
                <SimulationControls />
              </section>

              <ServerCards />
              <ResourceHistoryChart />

              <JobTable />
              <SystemEvents />

              <AlgorithmComparison />
            </div>
          </main>
        </SidebarInset>
      </SidebarProvider>
    </SimulationProvider>
  );
}