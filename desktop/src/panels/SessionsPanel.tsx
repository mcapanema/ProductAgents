import { useEffect, useState } from "react";
import { useIpc } from "../app/IpcProvider";
import type { IpcEvent, SessionSummary } from "../ipc/types";
import { deriveStages } from "./runTimeline";
import { StageTimeline } from "./StageTimeline";
import { RawEvents } from "./RawEvents";

export function SessionsPanel() {
  const ipc = useIpc();
  const [list, setList] = useState<SessionSummary[]>([]);
  const [events, setEvents] = useState<IpcEvent[] | null>(null);

  useEffect(() => {
    if (ipc) ipc.sessionsList().then(setList).catch(() => setList([]));
  }, [ipc]);

  async function open(id: string) {
    if (!ipc) return;
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
      {list.length === 0 && <p className="muted">No sessions recorded yet.</p>}
      <div className="row" style={{ alignItems: "flex-start", gap: 24 }}>
        <div style={{ flex: "0 0 320px" }}>
          {list.map((s) => (
            <div className="list-item" key={s.id} onClick={() => open(s.id)}>
              <div>{s.workflow}</div>
              <div className="muted">{s.status} · {s.created_at}</div>
            </div>
          ))}
        </div>
        {events && (
          <div style={{ flex: 1 }}>
            <StageTimeline stages={deriveStages(events)} />
            <RawEvents events={events} />
          </div>
        )}
      </div>
    </div>
  );
}
