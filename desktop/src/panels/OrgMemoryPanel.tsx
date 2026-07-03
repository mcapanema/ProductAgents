import { useEffect, useState } from "react";
import { useIpc } from "../app/IpcProvider";
import type { Lesson } from "../ipc/types";
import { formatConfidence } from "./decisionView";
import { EmptyState } from "../ui/EmptyState";

export function OrgMemoryPanel() {
  const ipc = useIpc();
  const [lessons, setLessons] = useState<Lesson[]>([]);

  useEffect(() => {
    if (ipc) ipc.memoryLessons().then(setLessons).catch(() => setLessons([]));
  }, [ipc]);

  return (
    <div>
      <h1>Organizational Memory</h1>
      <p className="page-desc">Lessons distilled from past decisions and their recorded outcomes.</p>
      {lessons.length === 0 && (
        <EmptyState
          title="No lessons recorded yet"
          description="Reflect on a past decision to capture its outcome; validated lessons surface here and feed future runs."
        />
      )}
      {lessons.map((l, i) => (
        <div className="list-item" key={`${l.decision_id}-${i}`}>
          <div>{l.text}</div>
          <div className="muted">
            {l.title} · {l.validated ? "validated" : "predicted"}
            {l.prediction_accuracy !== null
              ? ` · accuracy ${formatConfidence(l.prediction_accuracy)}`
              : ""}
          </div>
        </div>
      ))}
    </div>
  );
}
