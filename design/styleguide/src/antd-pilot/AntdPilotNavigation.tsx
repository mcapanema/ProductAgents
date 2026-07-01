// design/styleguide/src/antd-pilot/AntdPilotNavigation.tsx
// AntD Pilot — Navigation. Compare against Phase 3B (Phase3Navigation.tsx).
import { useState } from "react";
import { Breadcrumb, Menu, Tabs } from "antd";
import { Section, Specimen } from "../sg";

export function AntdPilotNavigation() {
  const [selectedKey, setSelectedKey] = useState("run");

  return (
    <Section
      id="antd-navigation"
      title="AntD Pilot · Navigation"
      desc="Menu, Tabs, Breadcrumb — compare against Phase 3B's sidebar nav and command palette."
    >
      <Specimen label="Sidebar menu">
        <Menu
          mode="inline"
          style={{ maxWidth: "var(--width-sidebar)" }}
          selectedKeys={[selectedKey]}
          onClick={({ key }) => setSelectedKey(key)}
          items={[
            { key: "run", label: "Run" },
            { key: "workflows", label: "Workflows" },
            { key: "sessions", label: "Sessions" },
            { key: "decisions", label: "Decisions" },
            { key: "connectors", label: "Connectors" },
          ]}
        />
      </Specimen>

      <Specimen label="Tabs">
        <Tabs
          items={[
            { key: "evidence", label: "Evidence", children: "Five analysts, run in parallel." },
            { key: "debate", label: "Debate", children: "Advocate vs Skeptic, per round." },
            { key: "risk", label: "Risk", children: "Five risk dimensions scored." },
          ]}
        />
      </Specimen>

      <Specimen label="Breadcrumb">
        <Breadcrumb
          items={[
            { title: "Decisions" },
            { title: "2026-07-01 — Ship the connector health page" },
            { title: "Debate" },
          ]}
        />
      </Specimen>
    </Section>
  );
}
