// Phase 4C — LLM Components gallery.
// StreamingText, ThinkingIndicator, TokenUsageBar, CostIndicator,
// ContextWindowViewer, PromptInspector, PromptDiff, PromptHistory,
// ConversationViewer — the UI vocabulary for LLM state, token accounting,
// and prompt management. Built from the token layer only (--ai-* tokens).
import { useState } from "react";
import type { CSSProperties } from "react";
import { Section, Specimen } from "../sg";
import "./phase4c-llm.css";

// Cast a record to CSSProperties so TS accepts CSS custom-property assignments.
const vars = (o: Record<string, string>): CSSProperties => o as CSSProperties;

/* ── helpers ────────────────────────────────────────────────────────────────── */

// Highlight {{variable}} placeholders in a prompt template body.
function renderPromptBody(text: string): React.ReactNode[] {
  return text.split(/({{[^}]+}})/g).map((part, i) =>
    part.startsWith("{{") ? (
      <span key={i} className="p4c-prompt-var">{part}</span>
    ) : (
      <span key={i}>{part}</span>
    )
  );
}

/* ═══════════════════════════════════════════════ 1. STREAMING TEXT ═══ */

function StreamingText({ text, done = false }: { text: string; done?: boolean }) {
  return (
    <span className="p4c-streaming-text" data-done={done ? "true" : undefined}>
      {text}
      {!done && <span className="p4c-streaming-text__cursor" aria-hidden="true" />}
    </span>
  );
}

/* ═══════════════════════════════════════════════ 2. THINKING INDICATOR ═══ */

function ThinkingIndicator({ label = "Thinking" }: { label?: string }) {
  return (
    <span className="p4c-thinking" role="status" aria-label={label}>
      <span className="p4c-thinking__dots" aria-hidden="true">
        <span className="p4c-thinking__dot" />
        <span className="p4c-thinking__dot" />
        <span className="p4c-thinking__dot" />
      </span>
      <span className="p4c-thinking__label">{label}</span>
    </span>
  );
}

/* ═══════════════════════════════════════════════ 3. TOKEN USAGE BAR ═══ */

type TokenUsage = { prompt: number; completion: number; limit: number };

function TokenUsageBar({ usage }: { usage: TokenUsage }) {
  const { prompt, completion, limit } = usage;
  const used = prompt + completion;
  const warn = used / limit > 0.8;

  return (
    <div className="p4c-token-bar" data-warn={warn ? "true" : undefined}>
      <div
        className="p4c-token-bar__track"
        role="img"
        aria-label={`Token usage: ${used.toLocaleString()} of ${limit.toLocaleString()}`}
      >
        <div
          className="p4c-token-bar__seg p4c-token-bar__seg--prompt"
          style={vars({ "--p4c-seg-w": `${(prompt / limit) * 100}%` })}
        />
        <div
          className="p4c-token-bar__seg p4c-token-bar__seg--completion"
          style={vars({ "--p4c-seg-w": `${(completion / limit) * 100}%` })}
        />
        <div className="p4c-token-bar__seg p4c-token-bar__seg--remain" />
      </div>
      <div className="p4c-token-bar__legend">
        <span className="p4c-token-bar__leg-item p4c-token-bar__leg-item--prompt">
          <span className="p4c-token-bar__leg-dot" aria-hidden="true" />
          Prompt
          <span className="p4c-token-bar__leg-val">{prompt.toLocaleString()}</span>
        </span>
        <span className="p4c-token-bar__leg-item p4c-token-bar__leg-item--completion">
          <span className="p4c-token-bar__leg-dot" aria-hidden="true" />
          Completion
          <span className="p4c-token-bar__leg-val">{completion.toLocaleString()}</span>
        </span>
        <span className="p4c-token-bar__leg-item p4c-token-bar__leg-item--remain">
          <span className="p4c-token-bar__leg-dot" aria-hidden="true" />
          Remaining
          <span className="p4c-token-bar__leg-val">{(limit - used).toLocaleString()}</span>
        </span>
        <span className="p4c-token-bar__total">
          {used.toLocaleString()} / {limit.toLocaleString()}
          {warn && <span className="p4c-token-bar__warn">Near limit</span>}
        </span>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════ 4. COST INDICATOR ═══ */

type CostData = { model: string; prompt: number; completion: number; total: number };

function CostBadge({ cost }: { cost: number }) {
  return <span className="p4c-cost-badge">${cost.toFixed(4)}</span>;
}

function CostPanel({ data }: { data: CostData }) {
  return (
    <div className="p4c-cost-panel">
      <div className="p4c-cost-panel__head">
        <span className="p4c-cost-panel__model">{data.model}</span>
        <span className="p4c-cost-panel__total">${data.total.toFixed(4)}</span>
      </div>
      <dl className="p4c-cost-panel__rows">
        <div className="p4c-cost-panel__row">
          <dt>Prompt tokens</dt>
          <dd>${data.prompt.toFixed(4)}</dd>
        </div>
        <div className="p4c-cost-panel__row">
          <dt>Completion tokens</dt>
          <dd>${data.completion.toFixed(4)}</dd>
        </div>
      </dl>
    </div>
  );
}

/* ═══════════════════════════════════════════════ 5. CONTEXT WINDOW VIEWER ═══ */

type CtxSegment = { label: string; tokens: number; colorVar: string };

function ContextWindowViewer({ segments, limit }: { segments: CtxSegment[]; limit: number }) {
  const used = segments.reduce((s, seg) => s + seg.tokens, 0);

  return (
    <div className="p4c-ctx-window">
      <div
        className="p4c-ctx-window__track"
        role="img"
        aria-label={`Context window: ${used.toLocaleString()} of ${limit.toLocaleString()} tokens used`}
      >
        {segments.map((seg) => (
          <div
            key={seg.label}
            className="p4c-ctx-window__seg"
            style={vars({
              "--p4c-ctx-w":     `${(seg.tokens / limit) * 100}%`,
              "--p4c-ctx-color": `var(${seg.colorVar})`,
            })}
          />
        ))}
        <div className="p4c-ctx-window__seg p4c-ctx-window__seg--avail" />
      </div>
      <div className="p4c-ctx-window__legend">
        {segments.map((seg) => (
          <span
            key={seg.label}
            className="p4c-ctx-window__leg-item"
            style={vars({ "--p4c-ctx-color": `var(${seg.colorVar})` })}
          >
            <span className="p4c-ctx-window__leg-dot" aria-hidden="true" />
            {seg.label}
            <span className="p4c-ctx-window__leg-val">{seg.tokens.toLocaleString()}</span>
          </span>
        ))}
        <span className="p4c-ctx-window__leg-item p4c-ctx-window__leg-item--avail">
          <span className="p4c-ctx-window__leg-dot" aria-hidden="true" />
          Available
          <span className="p4c-ctx-window__leg-val">{(limit - used).toLocaleString()}</span>
        </span>
        <span className="p4c-ctx-window__usage">
          {used.toLocaleString()} / {limit.toLocaleString()} tokens
        </span>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════ 6. PROMPT INSPECTOR ═══ */

type PromptDef = { name: string; version: number; body: string };

function PromptInspector({ prompt, initialOpen = false }: { prompt: PromptDef; initialOpen?: boolean }) {
  const [open, setOpen] = useState(initialOpen);
  return (
    <div className="p4c-prompt-inspector" data-open={open ? "true" : undefined}>
      <button
        className="p4c-prompt-inspector__toggle"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
      >
        <span className="p4c-prompt-inspector__chevron" aria-hidden="true" />
        <span className="p4c-prompt-inspector__name">{prompt.name}</span>
        <span className="p4c-prompt-inspector__meta">v{prompt.version}</span>
      </button>
      {open && (
        <pre className="p4c-prompt-inspector__body">
          <code>{renderPromptBody(prompt.body)}</code>
        </pre>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════ 7. PROMPT DIFF ═══ */

type DiffLine = { type: "added" | "removed" | "context"; text: string };

function PromptDiff({ lines, label }: { lines: DiffLine[]; label: string }) {
  return (
    <div className="p4c-diff" aria-label={label}>
      <div className="p4c-diff__header">{label}</div>
      <div className="p4c-diff__body">
        {lines.map((line, i) => (
          <div key={i} className={`p4c-diff__line p4c-diff__line--${line.type}`}>
            <span className="p4c-diff__gutter" aria-hidden="true">
              {line.type === "added" ? "+" : line.type === "removed" ? "-" : " "}
            </span>
            <span className="p4c-diff__text">{line.text || " "}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════ 8. PROMPT HISTORY ═══ */

type PromptVersion = { version: number; date: string; chars: number; delta?: number; active?: boolean };

function PromptHistory({ versions }: { versions: PromptVersion[] }) {
  return (
    <ol className="p4c-prompt-history">
      {versions.map((v) => (
        <li
          key={v.version}
          className="p4c-prompt-history__item"
          data-active={v.active ? "true" : undefined}
        >
          <span className="p4c-prompt-history__ver">v{v.version}</span>
          <span className="p4c-prompt-history__info">
            <span className="p4c-prompt-history__date">{v.date}</span>
            <span className="p4c-prompt-history__chars">
              {v.chars.toLocaleString()} chars
              {v.delta !== undefined && (
                <span
                  className="p4c-prompt-history__delta"
                  data-sign={v.delta >= 0 ? "pos" : "neg"}
                >
                  {v.delta >= 0 ? "+" : ""}{v.delta}
                </span>
              )}
            </span>
          </span>
          {v.active && <span className="p4c-prompt-history__badge">active</span>}
        </li>
      ))}
    </ol>
  );
}

/* ═══════════════════════════════════════════════ 9. CONVERSATION VIEWER ═══ */

type ConvTurn = { role: "system" | "user" | "assistant"; content: string; tokens?: number };

function ConversationViewer({ turns }: { turns: ConvTurn[] }) {
  return (
    <div className="p4c-conv" aria-label="Conversation transcript">
      <div className="p4c-conv__header">Conversation transcript</div>
      <ol className="p4c-conv__turns">
        {turns.map((turn, i) => (
          <li key={i} className={`p4c-conv__turn p4c-conv__turn--${turn.role}`}>
            <div className="p4c-conv__role-row">
              <span className="p4c-conv__role">{turn.role}</span>
              {turn.tokens !== undefined && (
                <span className="p4c-conv__tokens">{turn.tokens.toLocaleString()} tokens</span>
              )}
            </div>
            <pre className="p4c-conv__content"><code>{turn.content}</code></pre>
          </li>
        ))}
      </ol>
    </div>
  );
}

/* ═══════════════════════════════════════════════ GALLERY DATA ═══ */

const STREAMING_SAMPLE =
  "The analyst team has completed the initial evidence review. Customer research signals strong demand, with 73% of recent feedback citing workflow friction as a top concern.";

const PROMPT_DEF: PromptDef = {
  name: "strategist",
  version: 3,
  body: `You are the strategist for {{workspace}}. Your role is to synthesise the analyst team's findings into a single governed recommendation.

Initiative: {{initiative_title}}
Debate summary: {{debate_summary}}
Relevant lessons: {{lessons}}

Produce a recommendation with confidence score, rationale, and predicted outcomes.`,
};

const CTX_SEGMENTS: CtxSegment[] = [
  { label: "System",  tokens: 1840,  colorVar: "--ai-thinking" },
  { label: "History", tokens: 22400, colorVar: "--ai-analyst-analytics" },
  { label: "Input",   tokens: 4200,  colorVar: "--ai-streaming" },
];

const DIFF_LINES: DiffLine[] = [
  { type: "context",  text: "You are the strategist for {{workspace}}." },
  { type: "context",  text: "" },
  { type: "removed",  text: "Your role is to synthesise the analyst findings." },
  { type: "added",    text: "Your role is to synthesise the analyst team's findings into a" },
  { type: "added",    text: "single governed recommendation." },
  { type: "context",  text: "" },
  { type: "context",  text: "Initiative: {{initiative_title}}" },
  { type: "removed",  text: "Debate: {{debate_summary}}" },
  { type: "added",    text: "Debate summary: {{debate_summary}}" },
  { type: "context",  text: "Relevant lessons: {{lessons}}" },
];

const PROMPT_VERSIONS: PromptVersion[] = [
  { version: 3, date: "2026-06-30", chars: 412, delta: +42, active: true },
  { version: 2, date: "2026-06-28", chars: 370, delta: -18 },
  { version: 1, date: "2026-06-27", chars: 388 },
];

const CONV_TURNS: ConvTurn[] = [
  {
    role: "system",
    content:
      "You are the strategist for the default workspace.\n\nInitiative: Adopt usage-based pricing tier",
    tokens: 1840,
  },
  {
    role: "user",
    content:
      "Analyst reports: [customer: strong demand] [analytics: 31% activation drop at tier wall]\n\nDebate summary: Advocate pressed revenue upside; Skeptic flagged churn risk.\n\nLessons: 2 relevant lessons retrieved.",
    tokens: 3210,
  },
  {
    role: "assistant",
    content:
      '{\n  "recommendation": "Adopt",\n  "confidence": 0.82,\n  "rationale": "Strong customer signal and competitive pressure outweigh transition risk."\n}',
    tokens: 284,
  },
];

/* ═══════════════════════════════════════════════ GALLERY ═══ */

export function Phase4LLM() {
  const [streamDone, setStreamDone] = useState(false);

  return (
    <>
      <div className="sg-subband">
        <h3>4C · LLM Components</h3>
        <span>
          UI vocabulary for LLM state and prompt management — streaming output, thinking
          indicators, token accounting, cost display, context window inspection, prompt
          editing tools (inspector, diff, history), and conversation transcript view.
          Built from the token layer only; all LLM state uses --ai-* tokens.
        </span>
      </div>

      {/* 1. STREAMING TEXT ─────────────────────────────────────────────────── */}
      <Section
        id="p4c-streaming-text"
        title="Streaming text"
        desc="Text building progressively with a blinking cursor (--ai-streaming amber). The cursor disappears when streaming is complete. Used wherever token-by-token output is displayed."
      >
        <div className="sg-card p4c-stack">
          <Specimen label="streaming (cursor visible)">
            <div className="p4c-prose">
              <StreamingText text={STREAMING_SAMPLE.slice(0, 80)} />
            </div>
          </Specimen>
          <Specimen label="complete (cursor gone)">
            <div className="p4c-prose">
              <StreamingText text={STREAMING_SAMPLE} done />
            </div>
          </Specimen>
          <Specimen label="interactive toggle">
            <div className="p4c-row">
              <button className="p4c-btn" onClick={() => setStreamDone((v) => !v)}>
                {streamDone ? "Restart stream" : "Mark done"}
              </button>
              <div className="p4c-prose">
                <StreamingText
                  text="Strategist has drafted a recommendation with 82% confidence."
                  done={streamDone}
                />
              </div>
            </div>
          </Specimen>
        </div>
      </Section>

      {/* 2. THINKING INDICATOR ───────────────────────────────────────────────── */}
      <Section
        id="p4c-thinking"
        title="Thinking indicator"
        desc="Three pulsing dots in --ai-thinking (indigo), staggered, shown while the model is reasoning before streaming begins. Reduced motion parks dots at full opacity."
      >
        <div className="sg-card p4c-stack">
          <Specimen label="default">
            <ThinkingIndicator />
          </Specimen>
          <Specimen label="multiple labels">
            <div className="p4c-row">
              <ThinkingIndicator label="Reasoning" />
              <ThinkingIndicator label="Calling tool" />
              <ThinkingIndicator label="Retrieving lessons" />
            </div>
          </Specimen>
        </div>
      </Section>

      {/* 3. TOKEN USAGE BAR ──────────────────────────────────────────────────── */}
      <Section
        id="p4c-token-usage"
        title="Token usage bar"
        desc="Stacked bar showing prompt / completion / remaining token counts. Warns in amber (--ai-degraded) when usage exceeds 80% of the model's context limit."
      >
        <div className="sg-card p4c-stack">
          <Specimen label="normal (10.4 k / 200 k)">
            <TokenUsageBar usage={{ prompt: 8240, completion: 2180, limit: 200000 }} />
          </Specimen>
          <Specimen label="warn state (>80% used)">
            <TokenUsageBar usage={{ prompt: 142000, completion: 24000, limit: 200000 }} />
          </Specimen>
        </div>
      </Section>

      {/* 4. COST INDICATOR ───────────────────────────────────────────────────── */}
      <Section
        id="p4c-cost"
        title="Cost indicator"
        desc="Inline badge for compact cost readout and a block breakdown panel showing prompt / completion / total cost per model."
      >
        <div className="sg-card p4c-stack">
          <Specimen label="inline badge">
            <div className="p4c-row">
              <span style={{ font: "var(--text-body-s)", color: "var(--text-secondary)" }}>
                Run cost: <CostBadge cost={0.0901} />
              </span>
              <span style={{ font: "var(--text-body-s)", color: "var(--text-secondary)" }}>
                Node cost: <CostBadge cost={0.0021} />
              </span>
            </div>
          </Specimen>
          <Specimen label="breakdown panel">
            <CostPanel
              data={{ model: "claude-sonnet-4-6", prompt: 0.0247, completion: 0.0654, total: 0.0901 }}
            />
          </Specimen>
        </div>
      </Section>

      {/* 5. CONTEXT WINDOW VIEWER ─────────────────────────────────────────────── */}
      <Section
        id="p4c-context-window"
        title="Context window viewer"
        desc="Stacked bar with legend showing how the context window is allocated: system prompt, conversation history, current input, and remaining available space."
      >
        <div className="sg-card">
          <ContextWindowViewer segments={CTX_SEGMENTS} limit={200000} />
        </div>
      </Section>

      {/* 6. PROMPT INSPECTOR ─────────────────────────────────────────────────── */}
      <Section
        id="p4c-prompt-inspector"
        title="Prompt inspector"
        desc="Expandable panel showing a prompt template in monospace. Variables in {{double braces}} are highlighted in accent-text. Click the toggle to expand or collapse."
      >
        <div className="sg-card p4c-stack">
          <Specimen label="collapsed">
            <PromptInspector
              prompt={{
                name: "risk",
                version: 2,
                body: "Evaluate {{recommendation}} for risk factors across five dimensions: {{dimensions}}.",
              }}
            />
          </Specimen>
          <Specimen label="expanded">
            <PromptInspector prompt={PROMPT_DEF} initialOpen />
          </Specimen>
        </div>
      </Section>

      {/* 7. PROMPT DIFF ──────────────────────────────────────────────────────── */}
      <Section
        id="p4c-prompt-diff"
        title="Prompt diff"
        desc="Unified diff between two prompt versions. Added lines have a green tint (--border-success); removed lines have a red tint (--border-error). Context lines are neutral."
      >
        <div className="sg-card">
          <PromptDiff lines={DIFF_LINES} label="strategist · v2 to v3" />
        </div>
      </Section>

      {/* 8. PROMPT HISTORY ───────────────────────────────────────────────────── */}
      <Section
        id="p4c-prompt-history"
        title="Prompt history"
        desc="Version list for a prompt template: version number, date, character count, and a signed delta from the prior version. The active version is marked with a badge."
      >
        <div className="sg-card">
          <PromptHistory versions={PROMPT_VERSIONS} />
        </div>
      </Section>

      {/* 9. CONVERSATION VIEWER ──────────────────────────────────────────────── */}
      <Section
        id="p4c-conversation"
        title="Conversation viewer"
        desc="Inspection transcript of the raw messages sent to and received from the model. Roles are labeled system / user / assistant. Monospace body for structured payloads. NOT a chat UI."
      >
        <div className="sg-card">
          <ConversationViewer turns={CONV_TURNS} />
        </div>
      </Section>
    </>
  );
}
