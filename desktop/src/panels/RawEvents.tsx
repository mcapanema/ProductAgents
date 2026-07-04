import type { IpcEvent } from "../ipc/types";

export function RawEvents({ events }: { events: IpcEvent[] }) {
  if (!events.length) return null;

  return (
    <details className="run-raw">
      <summary>Raw Events ({events.length})</summary>
      <div className="event">
        {events.map((evt, idx) => (
          <div key={idx}>
            <strong>{evt.type}</strong>
            <pre>{JSON.stringify(evt.payload, null, 2)}</pre>
          </div>
        ))}
      </div>
    </details>
  );
}
