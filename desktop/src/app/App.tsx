import { useState } from "react";
import type { IpcClient } from "../ipc/client";
import { IpcProvider } from "./IpcProvider";
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

type View = "run" | "workflows" | "sessions" | "decisions" | "connectors" | "prompts" | "settings" | "reflection" | "memory";

const NAV: { view: View; label: string }[] = [
  { view: "run", label: "Run" },
  { view: "workflows", label: "Workflows" },
  { view: "sessions", label: "Sessions" },
  { view: "decisions", label: "Decisions" },
  { view: "memory", label: "Memory" },
  { view: "connectors", label: "Connectors" },
  { view: "prompts", label: "Prompts" },
  { view: "settings", label: "Settings" },
  { view: "reflection", label: "Reflection" },
];

export function App({ client }: { client?: IpcClient }) {
  const [view, setView] = useState<View>("run");
  return (
    <IpcProvider client={client}>
      <div className="shell">
        <nav className="sidebar">
          <div className="brand">ProductAgents</div>
          {NAV.map((item) => (
            <button
              key={item.view}
              className={view === item.view ? "nav active" : "nav"}
              onClick={() => setView(item.view)}
            >
              {item.label}
            </button>
          ))}
        </nav>
        <main className="content">
          {view === "run" && <RunPanel />}
          {view === "sessions" && <SessionsPanel />}
          {view === "decisions" && <DecisionsPanel />}
          {view === "memory" && <OrgMemoryPanel />}
          {view === "connectors" && <ConnectorsPanel />}
          {view === "prompts" && <PromptsPanel />}
          {view === "workflows" && <WorkflowsPanel />}
          {view === "settings" && <SettingsPanel />}
          {view === "reflection" && <ReflectionPanel />}
        </main>
      </div>
    </IpcProvider>
  );
}
