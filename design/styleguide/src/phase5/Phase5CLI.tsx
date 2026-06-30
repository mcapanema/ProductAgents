import { useState } from "react";
import type { Density } from "../sg";
import { Section, Specimen } from "../sg";
import "./phase5b-cli.css";

/* ── Icons ──────────────────────────────────────────────────────────────────── */

type IconName = "copy" | "check" | "x" | "history" | "chevron-right" | "search";

const PATHS: Record<IconName, React.ReactNode> = {
  copy: <><rect x="9" y="9" width="11" height="11" rx="1.5" /><path d="M6 15H5a1.5 1.5 0 01-1.5-1.5V5A1.5 1.5 0 015 3.5h8.5A1.5 1.5 0 0115 5v1" /></>,
  check: <path d="M5 12.5l4.5 4.5L19 7" />,
  x: <path d="M6 6l12 12M18 6L6 18" />,
  history: <><circle cx="12" cy="13" r="8" /><path d="M12 9v4l3 1.8" /><path d="M9 2.5L6 5M15 2.5L18 5" /></>,
  "chevron-right": <path d="M9 6l6 6-6 6" />,
  search: <><circle cx="10.5" cy="10.5" r="6.5" /><path d="M19 19l-4-4" /></>,
};

function Icon({ name, size = "sm" }: { name: IconName; size?: "xs" | "sm" }) {
  return (
    <svg
      className={`p5b-ico p5b-ico--${size}`}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
    >
      {PATHS[name]}
    </svg>
  );
}

/* ── 1. Command Badge ──────────────────────────────────────────────────────── */

function CommandBadge({ children }: { children: string }) {
  return <code className="p5b-cmd-badge">{children}</code>;
}

/* ── 2. Exit Status ────────────────────────────────────────────────────────── */

function ExitStatus({ code }: { code: number }) {
  const ok = code === 0;
  return (
    <span className="p5b-exit-status" data-ok={ok}>
      <Icon name={ok ? "check" : "x"} size="xs" />
      exit {code}
    </span>
  );
}

/* ── 3. ANSI Renderer (simulated colorized CLI output) ───────────────────────── */

type AnsiToken = { text: string; tone?: "info" | "warn" | "error" | "done" | "dim" };

function AnsiRenderer({ tokens }: { tokens: AnsiToken[] }) {
  return (
    <span className="p5b-ansi">
      {tokens.map((t, i) => (
        <span key={i} className={t.tone ? `p5b-ansi--${t.tone}` : undefined}>{t.text}</span>
      ))}
    </span>
  );
}

const ANSI_SAMPLE: AnsiToken[] = [
  { text: "[1/9] ", tone: "dim" },
  { text: "evidence " },
  { text: "✓ collected", tone: "done" },
  { text: " (5 sources)\n", tone: "dim" },
  { text: "[2/9] ", tone: "dim" },
  { text: "analysts " },
  { text: "⚠ technical degraded", tone: "warn" },
  { text: ", 4/5 ok\n", tone: "dim" },
  { text: "[9/9] ", tone: "dim" },
  { text: "governance " },
  { text: "✗ blocked: awaiting approval", tone: "error" },
];

/* ── 4. Console Output ─────────────────────────────────────────────────────── */

interface ConsoleLine { prompt?: string; text: string; tone?: "info" | "warn" | "error" | "done" }

function ConsoleOutput({ lines }: { lines: ConsoleLine[] }) {
  return (
    <div className="p5b-console-output">
      {lines.map((l, i) => (
        <div key={i} className={`p5b-console-output__line${l.tone ? ` p5b-console-output__line--${l.tone}` : ""}`}>
          {l.prompt && <span className="p5b-console-output__prompt">{l.prompt}</span>}
          <span>{l.text}</span>
        </div>
      ))}
    </div>
  );
}

/* ── 5. Terminal (chrome wrapper) ──────────────────────────────────────────── */

function Terminal({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="p5b-terminal">
      <div className="p5b-terminal__bar">
        <span className="p5b-terminal__dots" aria-hidden="true">
          <span /><span /><span />
        </span>
        <span className="p5b-terminal__title">{title}</span>
      </div>
      <div className="p5b-terminal__body">{children}</div>
    </div>
  );
}

/* ── 6. Copy Output ────────────────────────────────────────────────────────── */

function CopyOutput({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      type="button"
      className="p5b-copy-output"
      aria-label={copied ? "Copied" : "Copy output"}
      onClick={() => {
        void navigator.clipboard.writeText(text);
        setCopied(true);
        window.setTimeout(() => setCopied(false), 1500);
      }}
    >
      <Icon name={copied ? "check" : "copy"} size="xs" />
      {copied ? "Copied" : "Copy"}
    </button>
  );
}

/* ── 7. Command History ────────────────────────────────────────────────────── */

interface HistoryEntry { command: string; time: string; exit: number }

const HISTORY: HistoryEntry[] = [
  { command: "productagents sync", time: "14:22:03", exit: 0 },
  { command: "productagents sessions list", time: "14:18:51", exit: 0 },
  { command: "productagents run evaluate_initiative \"Usage-based billing\" --evidence sample", time: "14:11:09", exit: 1 },
  { command: "productagents workspace show", time: "13:58:40", exit: 0 },
];

function CommandHistory() {
  return (
    <ol className="p5b-history" aria-label="command history">
      {HISTORY.map((h, i) => (
        <li key={i} className="p5b-history__row" tabIndex={0}>
          <Icon name="history" size="xs" />
          <code className="p5b-history__cmd">{h.command}</code>
          <span className="p5b-history__time">{h.time}</span>
          <ExitStatus code={h.exit} />
        </li>
      ))}
    </ol>
  );
}

/* ── 8. Command Suggestion ─────────────────────────────────────────────────── */

const SUGGESTIONS = [
  { cmd: "run evaluate_initiative", desc: "Headless decision run, streams events" },
  { cmd: "reflect", desc: "List past decisions / record an outcome" },
  { cmd: "sessions show", desc: "Replay a session's event timeline" },
];

function CommandSuggestion() {
  return (
    <div className="p5b-suggest">
      <div className="p5b-suggest__input">
        <Icon name="search" size="xs" />
        <span>productagents re</span>
        <span className="p5b-suggest__cursor" aria-hidden="true" />
      </div>
      <ul className="p5b-suggest__list" role="listbox">
        {SUGGESTIONS.map((s) => (
          <li key={s.cmd} className="p5b-suggest__item" role="option" aria-selected={s.cmd === "reflect"}>
            <code>{s.cmd}</code>
            <span className="p5b-suggest__desc">{s.desc}</span>
          </li>
        ))}
      </ul>
    </div>
  );
}

/* ── 9. Live Streaming Output ─────────────────────────────────────────────── */

function LiveStreamingOutput() {
  return (
    <div className="p5b-live-output" role="log" aria-live="polite">
      <span className="p5b-live-output__line">strategist: synthesizing recommendation from 5 analyst reports…</span>
      <span className="p5b-cursor" aria-hidden="true" />
    </div>
  );
}

/* ── Gallery ───────────────────────────────────────────────────────────────── */

export function Phase5CLI({ density }: { density: Density }) {
  return (
    <div data-density={density}>
      <div className="sg-intro">
        <h2>CLI components</h2>
        <p>
          Phase 5B — terminal chrome and command-output primitives for the
          <CommandBadge>productagents</CommandBadge> CLI: history, suggestions,
          streaming output, ANSI-style status coloring.
        </p>
      </div>

      <Section id="p5b-command-badge" title="Command Badge" desc="Inline monospace chip for a subcommand name.">
        <Specimen label="default">
          <div className="p5b-row">
            <CommandBadge>run</CommandBadge>
            <CommandBadge>sync</CommandBadge>
            <CommandBadge>sessions list</CommandBadge>
            <CommandBadge>reflect</CommandBadge>
          </div>
        </Specimen>
      </Section>

      <Section id="p5b-exit-status" title="Exit Status" desc="Process exit code, color+glyph+label (never color alone).">
        <Specimen label="default">
          <div className="p5b-row">
            <ExitStatus code={0} />
            <ExitStatus code={1} />
          </div>
        </Specimen>
      </Section>

      <Section id="p5b-ansi-renderer" title="ANSI Renderer" desc="Tokenized colorized text — maps simulated ANSI tones onto --ai-log-* tokens.">
        <Specimen label="default">
          <pre className="p5b-ansi-block"><AnsiRenderer tokens={ANSI_SAMPLE} /></pre>
        </Specimen>
      </Section>

      <Section id="p5b-console-output" title="Console Output" desc="Static block of prompt-prefixed output lines.">
        <Specimen label="default">
          <ConsoleOutput
            lines={[
              { prompt: "$", text: "productagents sync" },
              { text: "github · acme/web: 12 issues synced", tone: "done" },
              { text: "jira · GROWTH: rate limited, retrying", tone: "warn" },
              { text: "2 connectors synced, 1 degraded", tone: "info" },
            ]}
          />
        </Specimen>
      </Section>

      <Section id="p5b-terminal" title="Terminal" desc="Chrome wrapper around console output — title bar + traffic-light dots.">
        <Specimen label="default">
          <Terminal title="productagents — evaluate_initiative">
            <ConsoleOutput
              lines={[
                { prompt: "$", text: "productagents run evaluate_initiative \"Usage-based billing\"" },
                { text: "evidence collected (5 sources)", tone: "done" },
                { text: "analysts: 4/5 ok, technical degraded", tone: "warn" },
                { text: "awaiting human approval", tone: "info" },
              ]}
            />
          </Terminal>
        </Specimen>
      </Section>

      <Section id="p5b-copy-output" title="Copy Output" desc="Copy-to-clipboard affordance with a transient confirmed state.">
        <Specimen label="default">
          <CopyOutput text="productagents sync" />
        </Specimen>
      </Section>

      <Section id="p5b-command-history" title="Command History" desc="Prior invocations with timestamp and exit status, focusable rows for keyboard re-run.">
        <Specimen label="default">
          <CommandHistory />
        </Specimen>
      </Section>

      <Section id="p5b-command-suggestion" title="Command Suggestion" desc="Autocomplete dropdown for partial input.">
        <Specimen label="default">
          <CommandSuggestion />
        </Specimen>
      </Section>

      <Section id="p5b-live-streaming-output" title="Live Streaming Output" desc="In-progress line with a blinking terminal cursor.">
        <Specimen label="default">
          <LiveStreamingOutput />
        </Specimen>
      </Section>
    </div>
  );
}
