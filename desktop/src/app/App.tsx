import { useState } from "react";
import type { IpcClient } from "../ipc/client";
import { IpcProvider, useIpc } from "./IpcProvider";
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
import { WorkflowsPanel } from "../panels/WorkflowsPanel";
import { SettingsPanel } from "../panels/SettingsPanel";
import { ReflectionPanel } from "../panels/ReflectionPanel";
import { OrgMemoryPanel } from "../panels/OrgMemoryPanel";
import "./App.css";

const DENSITY: Density = "comfortable";

export function App({ client }: { client?: IpcClient }) {
  return (
    <IpcProvider client={client}>
      <AppShell />
    </IpcProvider>
  );
}

function AppShell() {
  const ipc = useIpc();
  const [view, setView] = useState<View>("run");
  const { pref, setPref, resolved } = useThemePreference(ipc);
  const [running, setRunning] = useState(false);

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
            {view === "run" && <RunPanel onRunningChange={setRunning} />}
            {view === "sessions" && <SessionsPanel />}
            {view === "decisions" && <DecisionsPanel />}
            {view === "memory" && <OrgMemoryPanel />}
            {view === "connectors" && <ConnectorsPanel />}
            {view === "prompts" && <PromptsPanel />}
            {view === "workflows" && <WorkflowsPanel />}
            {view === "settings" && <SettingsPanel theme={pref} onThemeChange={setPref} running={running} />}
            {view === "reflection" && <ReflectionPanel />}
          </main>
        </div>
      </div>
    </ThemeShell>
  );
}
