import { useState, memo } from "react";
import type { IpcEvent } from "../ipc/types";

function RawEventsComponent({ events }: { events: IpcEvent[] }) {
  const [open, setOpen] = useState(false);

  if (!events.length) return null;

  return (
    <details className="run-raw" onToggle={(e) => setOpen(e.currentTarget.open)}>
      <summary>Raw Events ({events.length})</summary>
      <div className="event">
        {events.map((evt, idx) => (
          <div key={idx}>
            <strong>{evt.type}</strong>
            {open && <pre>{JSON.stringify(evt.payload, null, 2)}</pre>}
          </div>
        ))}
      </div>
    </details>
  );
}

export const RawEvents = memo(RawEventsComponent);
