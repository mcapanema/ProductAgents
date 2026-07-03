import { useEffect, useState } from "react";
import { useIpc } from "../app/IpcProvider";
import type { IpcEvent, SessionSummary } from "../ipc/types";
import { deriveStages } from "./runTimeline";
import { StageTimeline } from "./StageTimeline";
import { RawEvents } from "./RawEvents";
import { EmptyState } from "../ui/EmptyState";

export function SessionsPanel() {
  const ipc = useIpc();
  const [list, setList] = useState<SessionSummary[]>([]);
  const [events, setEvents] = useState<IpcEvent[] | null>(null);
  const [openId, setOpenId] = useState<string | null>(null);

  useEffect(() => {
    if (ipc) ipc.sessionsList().then(setList).catch(() => setList([]));
  }, [ipc]);

  async function open(id: string) {
    if (!ipc) return;
    setOpenId(id);
    try {
      const detail = await ipc.sessionsShow(id);
      setEvents(detail.events);
    } catch {
      setEvents(null);
    }
  }

  return (
    <div>
      <h1>Sessions</h1>
      <p className="page-desc">Every persisted pipeline run and its event timeline.</p>
      {list.length === 0 ? (
        <EmptyState
          title="No sessions recorded yet"
          description="Run a decision from the Run tab; each run is persisted here with its full event timeline."
        />
      ) : (
        <div className="master-detail">
          <div className="master-detail__list">
            {list.map((s) => (
              <div
                className={`list-item${openId === s.id ? " is-selected" : ""}`}
                key={s.id}
                onClick={() => open(s.id)}
              >
                <div>{s.workflow}</div>
                <div className="muted">{s.status} · {s.created_at}</div>
              </div>
            ))}
          </div>
          {events && (
            <div className="master-detail__detail">
              <StageTimeline stages={deriveStages(events)} />
              <RawEvents events={events} />
            </div>
          )}
        </div>
      )}
    </div>
  );
}
