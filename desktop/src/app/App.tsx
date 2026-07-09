import { lazy, Suspense, useState } from "react";
import type { IpcClient } from "../ipc/client";
import { IpcProvider, useIpc } from "./IpcProvider";
import { RunProvider, useRun } from "./RunContext";
import { ThemeShell } from "../ui/ThemeShell";
import type { Density } from "../ui/theme";
import { useThemePreference } from "../ui/useThemePreference";
import { Sidebar, type View } from "./Sidebar";
import { TopBar } from "./TopBar";
import { RunPanel } from "../panels/RunPanel";
import { SessionsPanel } from "../panels/SessionsPanel";
import { DecisionsPanel } from "../panels/DecisionsPanel";
import { ConnectorsPanel } from "../panels/ConnectorsPanel";
import { PromptsPanel } from "../panels/PromptsPanel";
import { SettingsPanel } from "../panels/SettingsPanel";
import { ReflectionPanel } from "../panels/ReflectionPanel";
import { OrgMemoryPanel } from "../panels/OrgMemoryPanel";
import "./App.css";

// Lazy: pulls in @xyflow/react, the heaviest dependency in the app, and only
// mounts when the user navigates to Workflows — code-split out of the main bundle.
const WorkflowsPanel = lazy(() =>
  import("../panels/WorkflowsPanel").then((m) => ({ default: m.WorkflowsPanel })),
);

const DENSITY: Density = "comfortable";

export function App({ client }: { client?: IpcClient }) {
  return (
    <IpcProvider client={client}>
      <RunProvider>
        <AppShell />
      </RunProvider>
    </IpcProvider>
  );
}

function AppShell() {
  const ipc = useIpc();
  const [view, setView] = useState<View>("run");
  const { pref, setPref, resolved } = useThemePreference(ipc);
  const running = useRun().state.status === "running";

  return (
    <ThemeShell theme={resolved} density={DENSITY}>
      <div className="shell">
        <Sidebar
          view={view}
          onNavigate={setView}
          running={running}
        />
        <div className="main">
          <TopBar view={view} onNavigate={setView} running={running} />
          <main className="content">
            {view === "run" && <RunPanel />}
            {view === "sessions" && <SessionsPanel />}
            {view === "decisions" && <DecisionsPanel />}
            {view === "memory" && <OrgMemoryPanel />}
            {view === "connectors" && <ConnectorsPanel />}
            {view === "prompts" && <PromptsPanel />}
            {view === "workflows" && (
              <Suspense fallback={<div className="content-loading">Loading…</div>}>
                <WorkflowsPanel />
              </Suspense>
            )}
            {view === "settings" && <SettingsPanel theme={pref} onThemeChange={setPref} running={running} />}
            {view === "reflection" && <ReflectionPanel />}
          </main>
        </div>
      </div>
    </ThemeShell>
  );
}
