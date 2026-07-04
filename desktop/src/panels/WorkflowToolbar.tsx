import { useState } from "react";
import { Button, Input, Modal, Segmented, Space } from "antd";
import type { WorkflowSummary } from "../ipc/types";
import "./WorkflowToolbar.css";

export type CurrentWorkflow = WorkflowSummary & { builtin: boolean };

type ModalKind = "new" | "clone" | "rename" | null;

const MODAL_TITLE: Record<Exclude<ModalKind, null>, string> = {
  new: "New workflow",
  clone: "Clone workflow",
  rename: "Rename workflow",
};

export function WorkflowToolbar({
  workflows,
  current,
  dirty,
  onSelect,
  onCreate,
  onClone,
  onRename,
  onDelete,
  onSetDefault,
  onSave,
}: {
  workflows: WorkflowSummary[];
  current: CurrentWorkflow | null;
  dirty: boolean;
  onSelect: (name: string) => void;
  onCreate: (name: string, title: string) => void;
  onClone: (newName: string, title: string) => void;
  onRename: (newName: string) => void;
  onDelete: () => void;
  onSetDefault: () => void;
  onSave: () => void;
}) {
  const [modal, setModal] = useState<ModalKind>(null);
  const [name, setName] = useState("");
  const [title, setTitle] = useState("");

  function openModal(kind: Exclude<ModalKind, null>) {
    setName(kind === "rename" ? (current?.name ?? "") : "");
    setTitle(kind === "rename" ? (current?.title ?? "") : "");
    setModal(kind);
  }

  function submit() {
    const trimmedName = name.trim();
    if (!trimmedName) return;
    if (modal === "new") onCreate(trimmedName, title.trim());
    if (modal === "clone") onClone(trimmedName, title.trim());
    if (modal === "rename") onRename(trimmedName);
    setModal(null);
  }

  function confirmDelete() {
    if (!current) return;
    Modal.confirm({
      title: `Delete "${current.title}"?`,
      content: "This cannot be undone.",
      okText: "Delete",
      okButtonProps: { danger: true },
      cancelText: "Cancel",
      onOk: onDelete,
    });
  }

  const builtin = current?.builtin ?? false;
  const isDefault = current?.is_default ?? false;

  return (
    <div className="wf-toolbar">
      <Segmented
        className="wf-toolbar__switcher"
        value={current?.name}
        onChange={(v) => onSelect(String(v))}
        options={workflows.map((w) => ({
          label: w.is_default ? `★ ${w.title}` : w.title,
          value: w.name,
        }))}
      />
      <Space wrap>
        <Button onClick={() => openModal("new")}>+ New</Button>
        <Button onClick={() => openModal("clone")} disabled={!current}>Clone</Button>
        <Button onClick={() => openModal("rename")} disabled={!current || builtin}>Rename</Button>
        <Button onClick={confirmDelete} disabled={!current || builtin}>Delete</Button>
        <Button onClick={onSetDefault} disabled={!current || isDefault}>Set default</Button>
        <Button type="primary" onClick={onSave} disabled={!dirty}>Save</Button>
      </Space>
      <Modal
        title={modal ? MODAL_TITLE[modal] : ""}
        open={modal !== null}
        onOk={submit}
        okText={modal === "rename" ? "Rename" : "Create"}
        onCancel={() => setModal(null)}
        destroyOnHidden
      >
        <Input
          placeholder="name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          onPressEnter={submit}
          autoFocus
        />
        {modal !== "rename" && (
          <Input
            placeholder="title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            onPressEnter={submit}
            style={{ marginTop: 8 }}
          />
        )}
      </Modal>
    </div>
  );
}
