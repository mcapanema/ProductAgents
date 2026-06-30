import { useLayoutEffect, useState } from "react";
import type { Theme, Density } from "./sg";
import { Foundation } from "./Foundation";
import { Tokens } from "./Tokens";
import { Components } from "./Components";
import { AIComponents } from "./AIComponents";
import { WorkflowCli } from "./WorkflowCli";
import { Phase6Project } from "./phase6/Phase6Project";

type Category = "foundation" | "tokens" | "components" | "ai-components" | "workflow-cli" | "project";

/** Top-level categories. `soon` entries are placeholders for future work
 *  (Design patterns = Phase 10, Documentation = Phase 11) — shown disabled so
 *  the overall shape of the system is legible. */
const CATEGORIES: { id: Category; label: string }[] = [
  { id: "foundation", label: "Foundation" },
  { id: "tokens", label: "Tokens" },
  { id: "components", label: "Components" },
  { id: "ai-components", label: "AI Components" },
  { id: "workflow-cli", label: "Workflow & CLI" },
  { id: "project", label: "Project" },
];
const SOON: { label: string }[] = [
  { label: "Design patterns" },
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
      </main>
    </div>
  );
}
