// Phase 3E — Feedback gallery. Alerts, toasts, banners, inline messages,
// progress (linear + circular), spinners, skeletons, status states, loading
// overlay. Built from the token layer only; copy grounded in ProductAgents.
import { useEffect, useRef, useState } from "react";
import { Section, Specimen } from "../sg";

type Kind = "success" | "warning" | "error" | "info";

/* ── Inline SVG icons (Phosphor-style: 24-grid, currentColor stroke) ──────── */
type IconName = Kind | "close" | "offline" | "empty";

function Glyph({ name, inline }: { name: IconName; inline?: boolean }) {
  return (
    <svg
      className={inline ? "fbk-ico fbk-ico--inline" : "fbk-ico"}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {name === "success" && (
        <>
          <circle cx={12} cy={12} r={9} />
          <path d="M8.25 12.5l2.5 2.5 5-5.5" />
        </>
      )}
      {name === "warning" && (
        <>
          <path d="M12 4.5 20.5 19.5H3.5Z" />
          <line x1={12} y1={10} x2={12} y2={14} />
          <path d="M12 17v.01" />
        </>
      )}
      {name === "error" && (
        <>
          <circle cx={12} cy={12} r={9} />
          <line x1={9} y1={9} x2={15} y2={15} />
          <line x1={15} y1={9} x2={9} y2={15} />
        </>
      )}
      {name === "info" && (
        <>
          <circle cx={12} cy={12} r={9} />
          <line x1={12} y1={11.5} x2={12} y2={16} />
          <path d="M12 8v.01" />
        </>
      )}
      {name === "close" && (
        <>
          <line x1={6} y1={6} x2={18} y2={18} />
          <line x1={18} y1={6} x2={6} y2={18} />
        </>
      )}
      {name === "offline" && (
        <>
          <circle cx={12} cy={12} r={9} />
          <line x1={5.6} y1={5.6} x2={18.4} y2={18.4} />
        </>
      )}
      {name === "empty" && (
        <>
          <rect x={3} y={4} width={18} height={16} rx={2} />
          <path d="M3 14h4l2 3h6l2-3h4" />
        </>
      )}
    </svg>
  );
}

const ICON_FOR: Record<Kind, IconName> = {
  success: "success",
  warning: "warning",
  error: "error",
  info: "info",
};
// Error/warning interrupt → role=alert; success/info are passive → role=status.
const ROLE_FOR: Record<Kind, "alert" | "status"> = {
  success: "status",
  warning: "alert",
  error: "alert",
  info: "status",
};

/* ── Alert ────────────────────────────────────────────────────────────────── */
function Alert(props: {
  kind: Kind;
  title: string;
  text: string;
  action?: string;
  onDismiss?: () => void;
}) {
  return (
    <div className={`fbk-alert fbk-k-${props.kind}`} role={ROLE_FOR[props.kind]}>
      <span className="fbk-alert__icon">
        <Glyph name={ICON_FOR[props.kind]} />
      </span>
      <div className="fbk-alert__body">
        <p className="fbk-alert__title">{props.title}</p>
        <p className="fbk-alert__text">{props.text}</p>
        {props.action && (
          <div className="fbk-alert__actions">
            <button type="button" className="fbk-act">
              {props.action}
            </button>
          </div>
        )}
      </div>
      {props.onDismiss && (
        <button type="button" className="fbk-close" aria-label="Dismiss alert" onClick={props.onDismiss}>
          <Glyph name="close" inline />
        </button>
      )}
    </div>
  );
}

/* ── Toast ────────────────────────────────────────────────────────────────── */
type Toast = { id: number; kind: Kind; title: string; text: string };
const TOAST_DWELL_MS = 6000; // matches --fbk-toast-dwell

let toastSeq = 0;
const TOAST_SAMPLES: Omit<Toast, "id">[] = [
  { kind: "success", title: "Decision recorded", text: "Saved to the DecisionStore as DR-2048." },
  { kind: "info", title: "Connector synced", text: "GitHub: 14 new issues → CustomerFeedback." },
  { kind: "warning", title: "Run degraded", text: "Two analysts fell back to scenario evidence." },
  { kind: "error", title: "Provider rate-limited", text: "Run aborted — retry in a moment." },
];

/* ── Linear progress ──────────────────────────────────────────────────────── */
function ProgressBar(props: { label: string; value?: number; indeterminate?: boolean }) {
  const determinate = !props.indeterminate;
  return (
    <div
      className="fbk-progress"
      role="progressbar"
      aria-label={props.label}
      aria-valuenow={determinate ? props.value : undefined}
      aria-valuemin={determinate ? 0 : undefined}
      aria-valuemax={determinate ? 100 : undefined}
    >
      <div className="fbk-progress__head">
        <span className="fbk-progress__label">{props.label}</span>
        <span className="fbk-progress__val">{determinate ? `${props.value}%` : "working…"}</span>
      </div>
      <div className={`fbk-progress__track${props.indeterminate ? " fbk-progress__track--indeterminate" : ""}`}>
        <div
          className="fbk-progress__fill"
          style={determinate ? ({ "--fbk-value": props.value } as React.CSSProperties) : undefined}
        />
      </div>
    </div>
  );
}

/* ── Circular progress ring ───────────────────────────────────────────────── */
function Ring({ value }: { value: number }) {
  return (
    <div
      className="fbk-ring"
      role="progressbar"
      aria-label="Pipeline progress"
      aria-valuenow={value}
      aria-valuemin={0}
      aria-valuemax={100}
    >
      <svg className="fbk-ring__svg" viewBox="0 0 24 24" aria-hidden="true">
        <circle className="fbk-ring__track" cx={12} cy={12} r={10} pathLength={100} />
        <circle
          className="fbk-ring__value"
          cx={12}
          cy={12}
          r={10}
          pathLength={100}
          style={{ "--fbk-value": value } as React.CSSProperties}
        />
      </svg>
      <span className="fbk-ring__num">{value}</span>
    </div>
  );
}

/* ── Spinner ──────────────────────────────────────────────────────────────── */
function Spinner({ size, label }: { size?: "sm" | "lg"; label: string }) {
  return (
    <span className={`fbk-spinner${size ? ` fbk-spinner--${size}` : ""}`} role="status" aria-label={label}>
      <svg className="fbk-spinner__svg" viewBox="0 0 24 24" aria-hidden="true">
        <circle className="fbk-spinner__track" cx={12} cy={12} r={10} pathLength={100} />
        <circle className="fbk-spinner__arc" cx={12} cy={12} r={10} pathLength={100} />
      </svg>
    </span>
  );
}

/* ── Status state (empty / error / success / warning) ─────────────────────── */
function StatusState(props: {
  kind: Kind | "neutral";
  icon: IconName;
  title: string;
  text: string;
  primary: string;
  secondary?: string;
}) {
  const k = props.kind === "neutral" ? "fbk-state--neutral" : `fbk-k-${props.kind}`;
  return (
    <div className={`fbk-state ${k}`} role={props.kind === "error" ? "alert" : "status"}>
      <span className="fbk-state__icon">
        <Glyph name={props.icon} />
      </span>
      <p className="fbk-state__title">{props.title}</p>
      <p className="fbk-state__text">{props.text}</p>
      <div className="fbk-state__actions">
        {props.secondary && (
          <button type="button" className="fbk-btn fbk-btn--secondary">
            {props.secondary}
          </button>
        )}
        <button type="button" className="fbk-btn fbk-btn--primary">
          {props.primary}
        </button>
      </div>
    </div>
  );
}

export function Phase3Feedback() {
  // Live: dismissible alert
  const [alertOpen, setAlertOpen] = useState(true);

  // Live: toast stack (auto-dismiss + manual close)
  const [toasts, setToasts] = useState<Toast[]>([]);
  const timers = useRef<Map<number, ReturnType<typeof setTimeout>>>(new Map());
  const dismissToast = (id: number) => {
    setToasts((t) => t.filter((x) => x.id !== id));
    const handle = timers.current.get(id);
    if (handle) {
      clearTimeout(handle);
      timers.current.delete(id);
    }
  };
  const fireToast = () => {
    const sample = TOAST_SAMPLES[toastSeq % TOAST_SAMPLES.length];
    const id = ++toastSeq;
    setToasts((t) => [...t, { id, ...sample }]);
    timers.current.set(id, setTimeout(() => dismissToast(id), TOAST_DWELL_MS));
  };
  useEffect(() => {
    const map = timers.current;
    return () => map.forEach((h) => clearTimeout(h));
  }, []);

  // Live: progress value driving both the linear bar and the ring
  const [pct, setPct] = useState(64);
  const clamp = (n: number) => Math.max(0, Math.min(100, n));

  // Live: loading overlay over a contained region
  const [loading, setLoading] = useState(false);
  const fireLoading = () => {
    setLoading(true);
    setTimeout(() => setLoading(false), 2200);
  };

  return (
    <>
      <div className="sg-subband">
        <h3>3E · Feedback</h3>
        <span>State, progress &amp; messaging — colour always paired with an icon + label, every motion with a reduced-motion fallback.</span>
      </div>

      <Section id="fbk-alert" title="Alert" desc="Tinted ground + icon + title + body + optional action and dismiss. Error/warning use role=alert; success/info role=status. Icon anchors to the title line.">
        <div className="sg-card fbk-stack">
          <Alert kind="success" title="Decision recorded" text="Saved to the DecisionStore as DR-2048 — predicted outcomes attached." action="View decision" />
          <Alert kind="info" title="Connector synced" text="GitHub returned 14 new issues, normalised to CustomerFeedback." />
          <Alert kind="warning" title="Run degraded" text="Two analysts fell back to scenario evidence; confidence is reported lower as a result." action="Open run report" />
          <Alert kind="error" title="Run aborted" text="The model provider rate-limited the request before the strategist could respond." action="Retry run" />
          <Specimen label="dismissible">
            {alertOpen ? (
              <Alert kind="info" title="Reflection captured" text="Outcome note compared against the original prediction." onDismiss={() => setAlertOpen(false)} />
            ) : (
              <button type="button" className="fbk-btn fbk-btn--secondary" onClick={() => setAlertOpen(true)}>
                Restore alert
              </button>
            )}
          </Specimen>
        </div>
      </Section>

      <Section id="fbk-banner" title="Banner" desc="Full-width, page-level status. Sits flush across a region with an accented left edge — for run-wide or app-wide conditions.">
        <div className="sg-card fbk-stack">
          <div className="fbk-banner fbk-k-warning" role="alert">
            <span className="fbk-banner__icon"><Glyph name="warning" /></span>
            <span className="fbk-banner__text">
              <b>Run degraded.</b> <span>Three of five analysts completed with caveats — read the report before approving.</span>
            </span>
            <span className="fbk-banner__actions">
              <button type="button" className="fbk-act">Dismiss</button>
            </span>
          </div>
          <div className="fbk-banner fbk-k-error" role="status">
            <span className="fbk-banner__icon"><Glyph name="offline" /></span>
            <span className="fbk-banner__text">
              <b>Offline.</b> <span>Can&apos;t reach the platform sidecar. Showing the last synced state; live runs are paused.</span>
            </span>
            <span className="fbk-banner__actions">
              <button type="button" className="fbk-act">Reconnect</button>
            </span>
          </div>
        </div>
      </Section>

      <Section id="fbk-inline" title="Inline message" desc="Compact, form-adjacent. Icon + one line — for field validation and helper feedback next to an input.">
        <div className="sg-card fbk-stack">
          <Specimen label="error">
            <span className="fbk-inline fbk-k-error">
              <span className="fbk-inline__icon"><Glyph name="error" inline /></span>
              Enter a valid model id, e.g. anthropic:claude-sonnet-4-6
            </span>
          </Specimen>
          <Specimen label="success">
            <span className="fbk-inline fbk-k-success">
              <span className="fbk-inline__icon"><Glyph name="success" inline /></span>
              API key verified — provider reachable.
            </span>
          </Specimen>
          <Specimen label="warning">
            <span className="fbk-inline fbk-k-warning">
              <span className="fbk-inline__icon"><Glyph name="warning" inline /></span>
              This model may not support tool calling; structured output can degrade.
            </span>
          </Specimen>
          <Specimen label="info">
            <span className="fbk-inline fbk-k-info">
              <span className="fbk-inline__icon"><Glyph name="info" inline /></span>
              Debate rounds default to 2 when left blank.
            </span>
          </Specimen>
        </div>
      </Section>

      <Section id="fbk-toast" title="Toast" desc="Transient, stacks bottom-up, auto-dismisses on a timer bar (role=status / aria-live). Fire a few; each closes itself after the dwell or via its close button.">
        <div className="sg-card fbk-stack">
          <div className="fbk-row">
            <button type="button" className="fbk-btn fbk-btn--primary" onClick={fireToast}>Fire toast</button>
            <button type="button" className="fbk-btn fbk-btn--secondary" onClick={() => setToasts([])}>Clear all</button>
          </div>
          <div className="fbk-toast-region" role="status" aria-live="polite" aria-relevant="additions">
            {toasts.map((t) => (
              <div key={t.id} className={`fbk-toast fbk-k-${t.kind}`}>
                <span className="fbk-toast__icon"><Glyph name={ICON_FOR[t.kind]} inline /></span>
                <div className="fbk-toast__body">
                  <p className="fbk-toast__title">{t.title}</p>
                  <p className="fbk-toast__text">{t.text}</p>
                </div>
                <button type="button" className="fbk-close" aria-label="Dismiss notification" onClick={() => dismissToast(t.id)}>
                  <Glyph name="close" inline />
                </button>
                <span className="fbk-toast__timer" aria-hidden="true" />
              </div>
            ))}
          </div>
        </div>
      </Section>

      <Section id="fbk-progress" title="Progress — linear" desc="Determinate (measured value, indigo) and indeterminate (unknown duration, amber = live). The numeric reading is always shown alongside.">
        <div className="sg-card fbk-stack">
          <ProgressBar label="Evidence collection" value={pct} />
          <div className="fbk-row">
            <button type="button" className="fbk-btn fbk-btn--secondary" onClick={() => setPct((p) => clamp(p - 10))}>−10%</button>
            <button type="button" className="fbk-btn fbk-btn--secondary" onClick={() => setPct((p) => clamp(p + 10))}>+10%</button>
          </div>
          <ProgressBar label="Strategist drafting recommendation" indeterminate />
        </div>
      </Section>

      <Section id="fbk-circular" title="Progress — circular &amp; spinner" desc="Determinate ring carries its numeric reading at the centre; the spinner (amber = loading) is for unknown-duration waits, in three sizes.">
        <div className="sg-card">
          <div className="fbk-row" style={{ gap: "var(--space-32)" }}>
            <div className="fbk-spinner-cell">
              <Ring value={pct} />
              <code>determinate</code>
            </div>
            <div className="fbk-spinner-row">
              <div className="fbk-spinner-cell"><Spinner size="sm" label="Loading" /><code>sm</code></div>
              <div className="fbk-spinner-cell"><Spinner label="Loading" /><code>md</code></div>
              <div className="fbk-spinner-cell"><Spinner size="lg" label="Loading" /><code>lg</code></div>
            </div>
          </div>
        </div>
      </Section>

      <Section id="fbk-skeleton" title="Skeleton" desc="Placeholder shapes with a travelling sheen while content loads — text lines, avatar, and a card. Reduced-motion replaces the shimmer with a flat fill.">
        <div className="sg-card fbk-grid-2">
          <div className="fbk-skel-stack">
            <div className="fbk-skel fbk-skel--text fbk-skel--w-60" />
            <div className="fbk-skel fbk-skel--text fbk-skel--w-80" />
            <div className="fbk-skel fbk-skel--text fbk-skel--w-40" />
          </div>
          <div className="fbk-skel-card">
            <div className="fbk-skel-card__head">
              <div className="fbk-skel fbk-skel--avatar" />
              <div className="fbk-skel-card__lines">
                <div className="fbk-skel fbk-skel--text fbk-skel--w-60" />
                <div className="fbk-skel fbk-skel--text fbk-skel--w-40" />
              </div>
            </div>
            <div className="fbk-skel fbk-skel--line fbk-skel--w-80" />
            <div className="fbk-skel fbk-skel--line fbk-skel--w-60" />
          </div>
        </div>
      </Section>

      <Section id="fbk-states" title="Status states" desc="Full-block states: hero icon + heading + description + action. Empty (neutral), success, warning, error — each distinct beyond hue.">
        <div className="sg-card fbk-grid-2">
          <StatusState
            kind="neutral"
            icon="empty"
            title="No sessions yet"
            text="Run an evaluation to begin — completed runs appear here like a git log of decisions."
            primary="New run"
            secondary="Import scenario"
          />
          <StatusState
            kind="success"
            icon="success"
            title="Decision approved"
            text="The recommendation cleared governance and was recorded with predicted outcomes."
            primary="Open decision"
          />
          <StatusState
            kind="warning"
            icon="warning"
            title="Completed with caveats"
            text="The run finished, but two analysts degraded to scenario evidence. Review before relying on it."
            primary="Review report"
            secondary="Re-run"
          />
          <StatusState
            kind="error"
            icon="error"
            title="Run failed"
            text="The provider returned an authentication error. Check the API key in Settings and try again."
            primary="Open settings"
            secondary="Retry"
          />
        </div>
      </Section>

      <Section id="fbk-overlay" title="Loading overlay" desc="Scrim + spinner over a contained region (not the whole page). The content beneath dims and is inert while the work runs.">
        <div className="sg-card">
          <div className="fbk-row" style={{ marginBottom: "var(--space-16)" }}>
            <button type="button" className="fbk-btn fbk-btn--primary" onClick={fireLoading}>Run evaluation</button>
          </div>
          <div className="fbk-region">
            <div className="fbk-region__content" data-loading={loading} aria-hidden={loading}>
              <p className="fbk-progress__label" style={{ color: "var(--text-primary)" }}>Initiative · Add SSO to the free tier</p>
              <p className="fbk-alert__text">Five analysts, one debate, a judge, and a risk pass turn this into a governed decision.</p>
              <p className="fbk-alert__text">Recall surfaces lessons from comparable past initiatives.</p>
            </div>
            {loading && (
              <div className="fbk-overlay">
                <Spinner size="lg" label="Running evaluation" />
                <span className="fbk-overlay__label">Running evaluation…</span>
              </div>
            )}
          </div>
        </div>
      </Section>
    </>
  );
}
