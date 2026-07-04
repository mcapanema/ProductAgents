import { useState } from "react";
import { Alert, App, Button, Input, Modal, Segmented, Space } from "antd";
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
  onCreate: (name: string, title: string, description: string) => Promise<void>;
  onClone: (newName: string, title: string) => Promise<void>;
  onRename: (newName: string, title: string) => Promise<void>;
  onDelete: () => Promise<void>;
  onSetDefault: () => Promise<void>;
  onSave: () => void;
}) {
  const { modal: confirmModal } = App.useApp();
  const [modal, setModal] = useState<ModalKind>(null);
  const [name, setName] = useState("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [modalError, setModalError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function openModal(kind: Exclude<ModalKind, null>) {
    setName(kind === "rename" ? (current?.name ?? "") : "");
    setTitle(kind === "rename" ? (current?.title ?? "") : "");
    setDescription("");
    setModalError("");
    setModal(kind);
  }

  // Only close the modal once the mutation actually succeeds — a rejection
  // (e.g. a duplicate-name collision) keeps it open with the error visible,
  // instead of closing as if nothing went wrong.
  async function submit() {
    const trimmedName = name.trim();
    if (!trimmedName) return;
    setSubmitting(true);
    try {
      if (modal === "new") await onCreate(trimmedName, title.trim(), description.trim());
      if (modal === "clone") await onClone(trimmedName, title.trim());
      if (modal === "rename") await onRename(trimmedName, title.trim());
      setModal(null);
      setModalError("");
    } catch (err) {
      setModalError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  }

  function confirmDelete() {
    if (!current) return;
    confirmModal.confirm({
      title: `Delete "${current.title}"?`,
      content: "This cannot be undone.",
      okText: "Delete",
      okButtonProps: { danger: true },
      cancelText: "Cancel",
      // A rejected onDelete keeps this confirm dialog open (antd's built-in
      // behavior for a promise-returning onOk) instead of closing silently.
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
        <Button onClick={() => void onSetDefault().catch(() => {})} disabled={!current || isDefault}>Set default</Button>
        <Button type="primary" onClick={onSave} disabled={!dirty}>Save</Button>
      </Space>
      <Modal
        title={modal ? MODAL_TITLE[modal] : ""}
        open={modal !== null}
        onOk={submit}
        okText={modal === "rename" ? "Rename" : "Create"}
        confirmLoading={submitting}
        onCancel={() => setModal(null)}
        destroyOnHidden
      >
        {modalError && (
          <Alert type="error" showIcon message={modalError} style={{ marginBottom: 8 }} />
        )}
        <Input
          placeholder="name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          onPressEnter={submit}
          autoFocus
        />
        <Input
          placeholder="title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          onPressEnter={submit}
          style={{ marginTop: 8 }}
        />
        {modal === "new" && (
          <Input.TextArea
            placeholder="description (optional)"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            autoSize={{ minRows: 2, maxRows: 4 }}
            style={{ marginTop: 8 }}
          />
        )}
      </Modal>
    </div>
  );
}
