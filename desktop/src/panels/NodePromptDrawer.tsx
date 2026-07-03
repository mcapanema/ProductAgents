import type { WorkflowNode } from "../ipc/types";

interface Props {
  node: WorkflowNode | null;
  onClose: () => void;
}

// Stub — Task 7 replaces this with the real prompt-editing drawer.
export function NodePromptDrawer(_props: Props) {
  return null;
}
