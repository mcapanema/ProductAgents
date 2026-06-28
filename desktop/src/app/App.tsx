import { useState } from "react";
import type { IpcClient } from "../ipc/client";
import { IpcProvider } from "./IpcProvider";
import { RunPanel } from "../panels/RunPanel";
import { SessionsPanel } from "../panels/SessionsPanel";
import { DecisionsPanel } from "../panels/DecisionsPanel";
import "./App.css";

type View = "run" | "sessions" | "decisions";

const NAV: { view: View; label: string }[] = [
  { view: "run", label: "Run" },
  { view: "sessions", label: "Sessions" },
  { view: "decisions", label: "Decisions" },
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
        </main>
      </div>
    </IpcProvider>
  );
}
