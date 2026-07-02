import { useState } from "react";
import type { IpcClient } from "../ipc/client";
import { IpcProvider } from "./IpcProvider";
import { ThemeShell } from "../ui/ThemeShell";
import type { Density } from "../ui/theme";
import { useThemePreference } from "../ui/useThemePreference";
import { Sidebar, type View } from "./Sidebar";
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
  const [view, setView] = useState<View>("run");
  const { pref, setPref, resolved } = useThemePreference();
  const [running, setRunning] = useState(false);

  return (
    <IpcProvider client={client}>
      <ThemeShell theme={resolved} density={DENSITY}>
        <div className="shell">
          <Sidebar
            view={view}
            onNavigate={setView}
            running={running}
          />
          <main className="content">
            {view === "run" && <RunPanel onRunningChange={setRunning} />}
            {view === "sessions" && <SessionsPanel />}
            {view === "decisions" && <DecisionsPanel />}
            {view === "memory" && <OrgMemoryPanel />}
            {view === "connectors" && <ConnectorsPanel />}
            {view === "prompts" && <PromptsPanel />}
            {view === "workflows" && <WorkflowsPanel />}
            {view === "settings" && <SettingsPanel theme={pref} onThemeChange={setPref} />}
            {view === "reflection" && <ReflectionPanel />}
          </main>
        </div>
      </ThemeShell>
    </IpcProvider>
  );
}
