// Phase 10C — System & recovery patterns gallery.
// Error recovery, permission requests, and notification strategy. Every demo
// is a real, working example (state + keyboard handling), not a static mock.
// The Notification-strategy pattern is a decision matrix, not new chrome — it
// deliberately reuses the actual `.fbk-*` toast/banner/inline classes from
// Phase 3E's feedback module (imported below) rather than re-declaring them,
// per this task's brief. Error recovery and Permission requests are genuinely
// new interactions, so their chrome is local (`.p10c-*`), matching the
// self-containment convention every other Phase 10 module follows.
import { useEffect, useId, useRef, useState } from "react";
import type { Density } from "../sg";
import { Section, Specimen } from "../sg";
import "../phase3/phase3e-feedback.css";
import "./phase10c-system-patterns.css";

/* ── Inline Phosphor-style icons (SVG only). Unlike sibling Phase 10 modules,
 * this file spans two icon-sizing contexts (local `.p10c-ico` chrome and
 * reused `.fbk-ico` chrome), so `Icon` takes a full className instead of
 * auto-prefixing one. ─────────────────────────────────────────────────── */
type IconName = "check" | "warning" | "error" | "info" | "x" | "retry" | "lock" | "help";

const ICONS: Record<IconName, string> = {
  check: "M5 13l4 4L19 7",
  warning: "M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z M12 9v4 M12 17h.01",
  error: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z M9.5 9l5 5 M14.5 9l-5 5",
  info: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z M12 16v-4 M12 8h.01",
  x: "M18 6 6 18 M6 6l12 12",
  retry: "M21 12a9 9 0 1 1-3-6.7 M21 3v6h-6",
  lock: "M6 10V7a6 6 0 1 1 12 0v3 M5 10h14v10H5z",
  help: "M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18Z M9.5 9a2.5 2.5 0 1 1 3.2 2.4c-.7.3-1.2.9-1.2 1.6v.3 M12 17h.01",
};

function Icon({ name, className }: { name: IconName; className: string }) {
  return (
    <svg className={className} viewBox="0 0 24 24" fill="none" stroke="currentColor"
      strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">
      <path d={ICONS[name]} />
    </svg>
  );
}

function Spinner() {
  return (
    <svg className="p10c-spinner" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <circle className="p10c-spinner__track" cx={12} cy={12} r={10} />
      <circle className="p10c-spinner__arc" cx={12} cy={12} r={10} pathLength={100} />
    </svg>
  );
}

/* ── useOverlay: Esc-to-close + initial focus + Tab focus-trap + focus restore.
 * Mirrors Phase 10A/10B's hook of the same name; kept local per the per-phase
 * self-containment convention every prior phase module follows. */
function useOverlay(active: boolean, onClose: () => void) {
  const ref = useRef<HTMLDivElement>(null);
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;

  useEffect(() => {
    if (!active) return;
    const panel = ref.current;
    const restore = document.activeElement as HTMLElement | null;
    const focusables = () =>
      panel
        ? Array.from(panel.querySelectorAll<HTMLElement>('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'))
        : [];
    focusables()[0]?.focus();

    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onCloseRef.current();
        return;
      }
      if (e.key !== "Tab") return;
      const items = focusables();
      if (items.length === 0) return;
      const first = items[0];
      const last = items[items.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      restore?.focus();
    };
  }, [active]);

  return ref;
}

/* ════════════════════════════════════════════════ 1. ERROR RECOVERY ══════ */

// ponytail: deterministic outcomes (first attempt fails, every retry
// succeeds) rather than randomised failure — the point of the demo is the
// recovery *shape* (real cause → retry → next action), not a flaky simulation.
function RetryDemo() {
  const [phase, setPhase] = useState<"idle" | "running" | "error" | "success">("idle");
  const [attempt, setAttempt] = useState(0);
  const timer = useRef<number | undefined>(undefined);

  function start() {
    setPhase("running");
    const attemptAtClick = attempt;
    timer.current = window.setTimeout(() => {
      setAttempt((a) => a + 1);
      setPhase(attemptAtClick === 0 ? "error" : "success");
    }, 1000);
  }
  useEffect(() => () => window.clearTimeout(timer.current), []);

  const cause = "The model provider rate-limited the request (HTTP 429) before the strategist could respond.";

  return (
    <div className="p10c-stage" style={{ alignItems: "stretch" }}>
      <button type="button" className="p10c-btn p10c-btn--primary" disabled={phase === "running"} onClick={start}>
        {phase === "running" ? (<><Spinner /> Running evaluation…</>) : attempt === 0 ? "Run evaluation" : "Run again"}
      </button>
      {phase === "error" && (
        <div className="p10c-error-card" role="alert">
          <Icon name="error" className="p10c-ico p10c-error-card__icon" />
          <div className="p10c-error-card__body">
            <p className="p10c-error-card__title">Run failed</p>
            <p className="p10c-error-card__cause">{cause}</p>
            <div className="p10c-error-card__actions">
              <button type="button" className="p10c-btn p10c-btn--secondary" onClick={start}>
                <Icon name="retry" className="p10c-ico p10c-ico--sm" /> Retry
              </button>
            </div>
          </div>
        </div>
      )}
      {phase === "success" && (
        <p className="p10c-status" data-tone="success" role="status">
          <Icon name="check" className="p10c-ico p10c-ico--sm" /> Recommendation recorded — DR-2051.
        </p>
      )}
    </div>
  );
}

type SyncItem = { id: number; label: string; ok: boolean; cause?: string };
const SYNC_ITEMS: SyncItem[] = [
  { id: 1, label: "Issue #478 — Export button is hard to find", ok: true },
  { id: 2, label: "Issue #482 — malformed webhook payload", ok: false, cause: "Payload missing the required `action` field; GitHub webhook schema mismatch." },
  { id: 3, label: "Issue #486 — API rate limit too low", ok: true },
  { id: 4, label: "Issue #490 — connector timed out", ok: false, cause: "Request exceeded the 30s connector timeout while paginating comments." },
  { id: 5, label: "Issue #493 — add dark mode", ok: true },
];

function SyncRetryDemo() {
  const [status, setStatus] = useState<Record<number, "pending" | "ok" | "failed">>(
    () => Object.fromEntries(SYNC_ITEMS.map((i) => [i.id, "pending"])),
  );
  const [phase, setPhase] = useState<"idle" | "running" | "done">("idle");
  const timers = useRef<number[]>([]);
  useEffect(() => () => timers.current.forEach((t) => window.clearTimeout(t)), []);

  function runSync(ids: number[], forceOk: boolean) {
    setPhase("running");
    ids.forEach((id, i) => {
      const item = SYNC_ITEMS.find((x) => x.id === id)!;
      timers.current.push(
        window.setTimeout(() => {
          setStatus((prev) => ({ ...prev, [id]: forceOk || item.ok ? "ok" : "failed" }));
        }, 260 * (i + 1)),
      );
    });
    timers.current.push(window.setTimeout(() => setPhase("done"), 260 * ids.length + 150));
  }

  const failed = SYNC_ITEMS.filter((i) => status[i.id] === "failed");
  const succeededCount = SYNC_ITEMS.filter((i) => status[i.id] === "ok").length;

  return (
    <div className="p10c-stage" style={{ alignItems: "stretch" }}>
      <div className="p10c-row">
        <button
          type="button"
          className="p10c-btn p10c-btn--primary"
          disabled={phase === "running"}
          onClick={() => runSync(SYNC_ITEMS.map((i) => i.id), false)}
        >
          {phase === "running" ? (<><Spinner /> Syncing…</>) : "Sync connector"}
        </button>
        {phase === "done" && (
          <span className="p10c-status" role="status">
            {succeededCount} of {SYNC_ITEMS.length} synced{failed.length > 0 ? `, ${failed.length} failed.` : "."}
          </span>
        )}
      </div>
      <ul className="p10c-item-list">
        {SYNC_ITEMS.map((item) => {
          const s = status[item.id];
          return (
            <li key={item.id} className="p10c-item-row" data-state={s}>
              <span className="p10c-item-row__icon" aria-hidden="true">
                {s === "ok" && <Icon name="check" className="p10c-ico p10c-ico--sm" />}
                {s === "failed" && <Icon name="error" className="p10c-ico p10c-ico--sm" />}
                {s === "pending" && <span className="p10c-item-row__dot" />}
              </span>
              <div className="p10c-item-row__body">
                <span className="p10c-item-row__label">{item.label}</span>
                {s === "failed" && <span className="p10c-item-row__cause">{item.cause}</span>}
              </div>
            </li>
          );
        })}
      </ul>
      {phase === "done" && failed.length > 0 && (
        <button type="button" className="p10c-btn p10c-btn--secondary" onClick={() => runSync(failed.map((i) => i.id), true)}>
          <Icon name="retry" className="p10c-ico p10c-ico--sm" /> Retry failed ({failed.length})
        </button>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════ 2. PERMISSION REQUESTS ══ */

const APPROVAL = {
  title: "Approve the Q3 pricing experiment rollout?",
  rationale: [
    "Evidence: usage data from 3 pilot cohorts shows +14% conversion with no churn increase.",
    "Debate: the skeptic's main objection (support-ticket volume) was addressed by adding an in-app FAQ.",
    "Judge: recommendation scored 0.86 on evidence grounding and 0.79 on rationale coherence — both above threshold.",
  ],
  consequence:
    "Approving submits this decision to the DecisionStore and notifies #pricing. Rejecting discards the recommendation — nothing is recorded. Either way, the analyst reports and debate transcript stay available for review.",
};

function ApprovalDialogDemo() {
  const [open, setOpen] = useState(false);
  const [outcome, setOutcome] = useState<null | "approved" | "rejected" | "info">(null);
  const [asking, setAsking] = useState(false);
  const [question, setQuestion] = useState("");
  const ref = useOverlay(open, () => setOpen(false));
  const titleId = useId();

  function close(next: "approved" | "rejected" | "info") {
    setOutcome(next);
    setOpen(false);
    setAsking(false);
    setQuestion("");
  }

  return (
    <div className="p10c-stage">
      <button type="button" className="p10c-btn p10c-btn--primary" onClick={() => { setOpen(true); setOutcome(null); }}>
        Request approval…
      </button>
      {outcome && (
        <p className="p10c-status" role="status" data-tone={outcome === "approved" ? "success" : undefined}>
          {outcome === "approved" && <><Icon name="check" className="p10c-ico p10c-ico--sm" /> Approved — recorded to DecisionStore as DR-2051.</>}
          {outcome === "rejected" && "Rejected — recommendation discarded, nothing recorded."}
          {outcome === "info" && "More info requested — the strategist will respond before this decision is re-opened."}
        </p>
      )}
      {open && (
        <>
          <div className="p10c-scrim" onClick={() => setOpen(false)} />
          <div ref={ref} className="p10c-modal" role="alertdialog" aria-modal="true" aria-labelledby={titleId} tabIndex={-1}>
            <div className="p10c-head">
              <span className="p10c-medallion" aria-hidden="true"><Icon name="lock" className="p10c-ico" /></span>
              <div className="p10c-titles">
                <h4 id={titleId}>{APPROVAL.title}</h4>
                <p>Governance step — human_approval</p>
              </div>
            </div>
            <div className="p10c-body">
              <ul className="p10c-rationale">
                {APPROVAL.rationale.map((r) => <li key={r}>{r}</li>)}
              </ul>
              <div className="p10c-consequence">
                <Icon name="info" className="p10c-ico p10c-ico--sm" />
                <span>{APPROVAL.consequence}</span>
              </div>
              {asking && (
                <div className="p10c-info-panel">
                  <label className="p10c-label" htmlFor={`${titleId}-q`}>What do you need clarified?</label>
                  <textarea
                    id={`${titleId}-q`}
                    className="p10c-textarea"
                    rows={2}
                    value={question}
                    onChange={(e) => setQuestion(e.target.value)}
                  />
                </div>
              )}
            </div>
            <div className="p10c-foot">
              {asking ? (
                <>
                  <button type="button" className="p10c-btn p10c-btn--ghost" onClick={() => setAsking(false)}>Back</button>
                  <button type="button" className="p10c-btn p10c-btn--primary" disabled={!question.trim()} onClick={() => close("info")}>
                    Send question
                  </button>
                </>
              ) : (
                <>
                  <button type="button" className="p10c-btn p10c-btn--ghost" onClick={() => setAsking(true)}>
                    <Icon name="help" className="p10c-ico p10c-ico--sm" /> Request more info
                  </button>
                  <button type="button" className="p10c-btn p10c-btn--secondary" onClick={() => close("rejected")}>Reject</button>
                  <button type="button" className="p10c-btn p10c-btn--primary" onClick={() => close("approved")}>Approve</button>
                </>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════ 3. NOTIFICATION STRATEGY ═ */

function NotificationMatrix() {
  return (
    <table className="p10c-matrix">
      <caption className="p10c-sr-only">Notification pattern comparison</caption>
      <thead>
        <tr><th>Pattern</th><th>Blocking?</th><th>Lifetime</th><th>Scope</th></tr>
      </thead>
      <tbody>
        <tr><th scope="row">Toast</th><td>No</td><td>Auto-dismiss (~6s) or manual close</td><td>Global — app-wide event</td></tr>
        <tr><th scope="row">Banner</th><td>No</td><td>Persists until dismissed or resolved</td><td>Page or section</td></tr>
        <tr><th scope="row">Inline message</th><td>No</td><td>Persists while the condition holds</td><td>One field or row</td></tr>
        <tr><th scope="row">Blocking dialog</th><td>Yes</td><td>Until a decision is made</td><td>The whole task/flow</td></tr>
      </tbody>
    </table>
  );
}

function ToastSpecimen() {
  const [toasts, setToasts] = useState<{ id: number }[]>([]);
  const seq = useRef(0);
  const timers = useRef<number[]>([]);
  useEffect(() => () => timers.current.forEach((t) => window.clearTimeout(t)), []);

  function fire() {
    const id = ++seq.current;
    setToasts((t) => [...t, { id }]);
    timers.current.push(window.setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 6000));
  }
  function dismiss(id: number) {
    setToasts((t) => t.filter((x) => x.id !== id));
  }

  return (
    <div className="p10c-stage" style={{ alignItems: "stretch" }}>
      <button type="button" className="fbk-btn fbk-btn--primary" onClick={fire}>Fire toast</button>
      <div className="fbk-toast-region" role="status" aria-live="polite" aria-relevant="additions">
        {toasts.map((t) => (
          <div key={t.id} className="fbk-toast fbk-k-success">
            <span className="fbk-toast__icon"><Icon name="check" className="fbk-ico fbk-ico--inline" /></span>
            <div className="fbk-toast__body">
              <p className="fbk-toast__title">Connector synced</p>
              <p className="fbk-toast__text">GitHub: 14 new issues → CustomerFeedback.</p>
            </div>
            <button type="button" className="fbk-close" aria-label="Dismiss notification" onClick={() => dismiss(t.id)}>
              <Icon name="x" className="fbk-ico fbk-ico--inline" />
            </button>
            <span className="fbk-toast__timer" aria-hidden="true" />
          </div>
        ))}
      </div>
    </div>
  );
}

function BannerSpecimen() {
  const [visible, setVisible] = useState(true);
  return (
    <div className="p10c-stage" style={{ alignItems: "stretch" }}>
      {visible ? (
        <div className="fbk-banner fbk-k-warning" role="alert">
          <span className="fbk-banner__icon"><Icon name="warning" className="fbk-ico" /></span>
          <span className="fbk-banner__text">
            <b>Run degraded.</b> <span>Two analysts fell back to scenario evidence — read the report before approving.</span>
          </span>
          <span className="fbk-banner__actions">
            <button type="button" className="fbk-act" onClick={() => setVisible(false)}>Dismiss</button>
          </span>
        </div>
      ) : (
        <button type="button" className="fbk-btn fbk-btn--secondary" onClick={() => setVisible(true)}>Restore banner</button>
      )}
    </div>
  );
}

function InlineSpecimen() {
  const [valid, setValid] = useState(false);
  const fieldId = useId();
  const msgId = useId();
  return (
    <div className="p10c-stage" style={{ alignItems: "stretch" }}>
      <label className="p10c-label" htmlFor={fieldId}>Connector token</label>
      <input
        id={fieldId}
        className="p10c-input"
        type="text"
        readOnly
        value={valid ? "ghp_••••live" : "ghp_••••invalid"}
        aria-invalid={!valid}
        aria-describedby={msgId}
      />
      <span id={msgId} className={valid ? "fbk-inline fbk-k-success" : "fbk-inline fbk-k-error"}>
        <span className="fbk-inline__icon"><Icon name={valid ? "check" : "error"} className="fbk-ico fbk-ico--inline" /></span>
        {valid ? "Token verified — connector reconnected." : "Token rejected — reconnect the GitHub connector."}
      </span>
      {!valid && (
        <button type="button" className="fbk-btn fbk-btn--secondary" onClick={() => setValid(true)}>
          Reconnect
        </button>
      )}
    </div>
  );
}

function BlockingDialogSpecimen() {
  const [open, setOpen] = useState(false);
  const [result, setResult] = useState<null | "discarded" | "kept">(null);
  const ref = useOverlay(open, () => setOpen(false));
  const titleId = useId();

  return (
    <div className="p10c-stage">
      <button type="button" className="p10c-btn p10c-btn--secondary" onClick={() => { setOpen(true); setResult(null); }}>
        Navigate away with unsaved changes
      </button>
      {result && (
        <p className="p10c-status" role="status">
          {result === "discarded" ? "Changes discarded." : "Stayed on the page — nothing lost."}
        </p>
      )}
      {open && (
        <>
          <div className="p10c-scrim" onClick={() => setOpen(false)} />
          <div ref={ref} className="p10c-modal" role="alertdialog" aria-modal="true" aria-labelledby={titleId} tabIndex={-1}>
            <div className="p10c-head">
              <span className="p10c-medallion p10c-medallion--warning" aria-hidden="true"><Icon name="warning" className="p10c-ico" /></span>
              <div className="p10c-titles">
                <h4 id={titleId}>Discard unsaved changes?</h4>
                <p>This debate-transcript edit hasn&apos;t been saved.</p>
              </div>
            </div>
            <div className="p10c-foot">
              <button type="button" className="p10c-btn p10c-btn--ghost" onClick={() => { setOpen(false); setResult("kept"); }}>
                Keep editing
              </button>
              <button type="button" className="p10c-btn p10c-btn--danger" onClick={() => { setOpen(false); setResult("discarded"); }}>
                Discard
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

/* ── Gallery ─────────────────────────────────────────────────────────────── */
export function Phase10CSystemPatterns({ density }: { density: Density }) {
  void density;
  return (
    <>
      <Section
        id="p10c-error-recovery"
        title="Error recovery"
        desc="Nodes degrade, never crash — the UI mirrors that: a failed operation always shows the real cause and a next action, never a dead end."
      >
        <Specimen label="single operation — real cause + retry"><RetryDemo /></Specimen>
        <Specimen label="partial success — retry only what failed"><SyncRetryDemo /></Specimen>
      </Section>

      <Section
        id="p10c-permission-requests"
        title="Permission requests"
        desc="The UI shape behind human_approval and governance: show the consequence and rationale before the decision, then let the user approve, reject, or ask for more information."
      >
        <Specimen label="governance approval"><ApprovalDialogDemo /></Specimen>
      </Section>

      <Section
        id="p10c-notification-strategy"
        title="Notification strategy"
        desc="Toast, banner, inline message, or blocking dialog — chosen by how urgent, how long-lived, and how scoped the message is. Reuses Phase 3E's feedback chrome; this pattern is the decision, not new visuals."
      >
        <Specimen label="comparison"><NotificationMatrix /></Specimen>
        <Specimen label="toast — transient, global"><ToastSpecimen /></Specimen>
        <Specimen label="banner — persistent, page-level"><BannerSpecimen /></Specimen>
        <Specimen label="inline — scoped to one field"><InlineSpecimen /></Specimen>
        <Specimen label="blocking dialog — requires a decision"><BlockingDialogSpecimen /></Specimen>
      </Section>
    </>
  );
}
