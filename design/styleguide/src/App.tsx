import { useLayoutEffect, useState } from "react";
import type { Theme, Density } from "./sg";
import { Foundation } from "./Foundation";
import { Tokens } from "./Tokens";
import { Components } from "./Components";
import { AIComponents } from "./AIComponents";
import { WorkflowCli } from "./WorkflowCli";
import { Phase6Project } from "./phase6/Phase6Project";
import { Phase7Settings } from "./phase7/Phase7Settings";
import { Phase8Monitoring } from "./phase8/Phase8Monitoring";
import { Phase9EmptyStates } from "./phase9/Phase9EmptyStates";
import { Phase10AFlowPatterns } from "./phase10/Phase10AFlowPatterns";
import { Phase10BEditingPatterns } from "./phase10/Phase10BEditingPatterns";
import { Phase10CSystemPatterns } from "./phase10/Phase10CSystemPatterns";
import { ConfigProvider } from "antd";
import { buildAntdTheme } from "./antd-pilot/theme";
import { AntdPilotForms } from "./antd-pilot/AntdPilotForms";
import { AntdPilotDataDisplay } from "./antd-pilot/AntdPilotDataDisplay";
import { AntdPilotOverlays } from "./antd-pilot/AntdPilotOverlays";

type Category = "foundation" | "tokens" | "components" | "ai-components" | "workflow-cli" | "project" | "settings" | "monitoring" | "empty-states" | "design-patterns" | "antd-pilot";

/** Top-level categories. `soon` entries are placeholders for future work
 *  (Documentation = Phase 11) — shown disabled so the overall shape of the
 *  system is legible. */
const CATEGORIES: { id: Category; label: string }[] = [
  { id: "foundation", label: "Foundation" },
  { id: "tokens", label: "Tokens" },
  { id: "components", label: "Components" },
  { id: "ai-components", label: "AI Components" },
  { id: "workflow-cli", label: "Workflow & CLI" },
  { id: "project", label: "Project" },
  { id: "settings", label: "Settings" },
  { id: "monitoring", label: "Monitoring" },
  { id: "empty-states", label: "Empty States" },
  { id: "design-patterns", label: "Design patterns" },
  { id: "antd-pilot", label: "AntD Pilot" },
];
const SOON: { label: string }[] = [
  { label: "Documentation" },
];

/** Two-option segmented toggle that writes a data-* attribute on <html>. */
function Toggle<T extends string>(props: {
  label: string;
  value: T;
  options: readonly { value: T; label: string }[];
  onChange: (v: T) => void;
}) {
  return (
    <div className="sg-toggle" role="group" aria-label={props.label}>
      <span className="sg-label">{props.label}</span>
      {props.options.map((o) => (
        <button
          key={o.value}
          type="button"
          aria-pressed={props.value === o.value}
          onClick={() => props.onChange(o.value)}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

export function App() {
  const [theme, setTheme] = useState<Theme>("light"); // light is the default theme (owner decision)
  const [density, setDensity] = useState<Density>("comfortable");
  const [category, setCategory] = useState<Category>("foundation");

  // Layout effects so the attribute write happens BEFORE useResolvedVars' passive
  // read (which displays the resolved hexes) — otherwise the values lag a theme.
  useLayoutEffect(() => { document.documentElement.setAttribute("data-theme", theme); }, [theme]);
  useLayoutEffect(() => { document.documentElement.setAttribute("data-density", density); }, [density]);
  // Switching category is a "page" change — start it from the top.
  useLayoutEffect(() => { window.scrollTo(0, 0); }, [category]);

  return (
    <div className="sg-shell">
      <div className="sg-top">
      <header className="sg-bar">
        <h1>ProductAgents</h1>
        <span className="sg-sub">Design System</span>
        <span className="sg-spacer" />
        <Toggle
          label="Theme"
          value={theme}
          onChange={setTheme}
          options={[{ value: "light", label: "Light" }, { value: "dark", label: "Dark" }]}
        />
        <Toggle
          label="Density"
          value={density}
          onChange={setDensity}
          options={[{ value: "comfortable", label: "Comfortable" }, { value: "compact", label: "Compact" }]}
        />
      </header>

      <nav className="sg-nav" aria-label="Categories">
        {CATEGORIES.map((c) => (
          <button
            key={c.id}
            type="button"
            className="sg-nav-tab"
            aria-current={category === c.id ? "page" : undefined}
            onClick={() => setCategory(c.id)}
          >
            {c.label}
          </button>
        ))}
        {SOON.map((c) => (
          <button key={c.label} type="button" className="sg-nav-tab" disabled aria-disabled="true">
            {c.label}
            <span className="sg-nav-soon">soon</span>
          </button>
        ))}
      </nav>
      </div>

      <main className="sg-main">
        {category === "foundation" && <Foundation theme={theme} />}
        {category === "tokens" && <Tokens theme={theme} density={density} />}
        {category === "components" && <Components />}
        {category === "ai-components" && <AIComponents />}
        {category === "workflow-cli" && <WorkflowCli density={density} />}
        {category === "project" && <Phase6Project density={density} />}
        {category === "settings" && <Phase7Settings density={density} />}
        {category === "monitoring" && <Phase8Monitoring density={density} />}
        {category === "empty-states" && <Phase9EmptyStates density={density} />}
        {category === "design-patterns" && (
          <>
            <Phase10AFlowPatterns density={density} />
            <Phase10BEditingPatterns density={density} />
            <Phase10CSystemPatterns density={density} />
          </>
        )}
        {category === "antd-pilot" && (
          <ConfigProvider theme={buildAntdTheme(theme, density)}>
            <AntdPilotForms />
            <AntdPilotDataDisplay />
            <AntdPilotOverlays />
          </ConfigProvider>
        )}
      </main>
    </div>
  );
}
