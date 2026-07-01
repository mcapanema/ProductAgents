// design/styleguide/src/antd-pilot/AntdPilotOverlays.tsx
// AntD Pilot — Overlays. Compare against Phase 3F (Phase3Overlays.tsx).
import { useState } from "react";
import { Button, Drawer, Modal, Popover, Space, Tooltip } from "antd";
import { Section, Specimen } from "../sg";

export function AntdPilotOverlays() {
  const [modalOpen, setModalOpen] = useState(false);
  const [drawerOpen, setDrawerOpen] = useState(false);

  return (
    <Section
      id="antd-overlays"
      title="AntD Pilot · Overlays"
      desc="Modal, Drawer, Tooltip, and Popover — compare against Phase 3F's dialog/drawer/tooltip/popover set."
    >
      <Specimen label="Modal">
        <Button onClick={() => setModalOpen(true)}>Open modal</Button>
        <Modal
          title="Approve recommendation?"
          open={modalOpen}
          onOk={() => setModalOpen(false)}
          onCancel={() => setModalOpen(false)}
          okText="Approve"
          cancelText="Cancel"
        >
          <p>This governance decision will be recorded to the DecisionStore.</p>
        </Modal>
      </Specimen>

      <Specimen label="Drawer">
        <Button onClick={() => setDrawerOpen(true)}>Open drawer</Button>
        <Drawer title="Run detail" open={drawerOpen} onClose={() => setDrawerOpen(false)} placement="right">
          <p>Reasoning timeline detail renders here.</p>
        </Drawer>
      </Specimen>

      <Specimen label="Tooltip & Popover">
        <Space wrap>
          <Tooltip title="Confidence is a measured quantity, not a guess.">
            <Button>Hover for tooltip</Button>
          </Tooltip>
          <Popover title="Evidence source" content="github · issue #142 · synced 2026-07-01">
            <Button>Click for popover</Button>
          </Popover>
        </Space>
      </Specimen>
    </Section>
  );
}
