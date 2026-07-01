// design/styleguide/src/antd-pilot/AntdPilotDataDisplay.tsx
// AntD Pilot — Table. Compare against Phase 3D's sortable Table.
import { Table, Tag, theme as antdTheme } from "antd";
import type { TableColumnsType } from "antd";
import { Section, Specimen } from "../sg";

interface ConnectorRow {
  key: string;
  connector: string;
  status: "healthy" | "degraded" | "down";
  lastSync: string;
}

const ROWS: ConnectorRow[] = [
  { key: "1", connector: "github", status: "healthy", lastSync: "2026-07-01 08:12" },
  { key: "2", connector: "jira", status: "degraded", lastSync: "2026-06-30 22:04" },
  { key: "3", connector: "linear", status: "down", lastSync: "2026-06-28 11:47" },
];

export function AntdPilotDataDisplay() {
  // theme.useToken() reads the CURRENT resolved AntD tokens (after
  // ConfigProvider applies buildAntdTheme's algorithm/token mapping), so Tag
  // colors stay in sync with "Instrument" without a second hardcoded palette.
  const { token } = antdTheme.useToken();
  const statusColor: Record<ConnectorRow["status"], string> = {
    healthy: token.colorSuccess,
    degraded: token.colorWarning,
    down: token.colorError,
  };

  const columns: TableColumnsType<ConnectorRow> = [
    {
      title: "Connector",
      dataIndex: "connector",
      key: "connector",
      sorter: (a, b) => a.connector.localeCompare(b.connector),
    },
    {
      title: "Status",
      dataIndex: "status",
      key: "status",
      filters: [
        { text: "Healthy", value: "healthy" },
        { text: "Degraded", value: "degraded" },
        { text: "Down", value: "down" },
      ],
      onFilter: (value, row) => row.status === value,
      render: (status: ConnectorRow["status"]) => <Tag color={statusColor[status]}>{status}</Tag>,
    },
    {
      title: "Last sync",
      dataIndex: "lastSync",
      key: "lastSync",
      sorter: (a, b) => a.lastSync.localeCompare(b.lastSync),
    },
  ];

  return (
    <Section
      id="antd-datadisplay"
      title="AntD Pilot · Table"
      desc="Sortable, filterable Table with status Tags colored from the resolved theme tokens (theme.useToken()) — compare against Phase 3D's sortable Table."
    >
      <Specimen label="Connector health">
        <Table<ConnectorRow> columns={columns} dataSource={ROWS} pagination={false} size="middle" />
      </Specimen>
    </Section>
  );
}
