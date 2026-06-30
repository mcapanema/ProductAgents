// Category: FOUNDATION — the raw, theme-agnostic primitive values (Phase 1).
// Color ramps, type scale, spacing, radius, sizes, elevation, motion.
import { Section, useResolvedVars } from "./sg";
import type { Theme } from "./sg";

const NEUTRAL_STEPS = [50, 100, 200, 300, 400, 450, 500, 600, 700, 800, 850, 900, 950];
const SIGNAL_STEPS = [50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950];
const RAMPS: { name: string; label: string; steps: number[] }[] = [
  { name: "slate", label: "cool graphite — dark grounds + cross-theme ink/border", steps: NEUTRAL_STEPS },
  { name: "sand", label: "warm neutral — light grounds", steps: NEUTRAL_STEPS },
  { name: "indigo", label: "primary — interactive accent (buttons / links / focus)", steps: SIGNAL_STEPS },
  { name: "amber", label: "signal — live / running / attention", steps: SIGNAL_STEPS },
  { name: "teal", label: "resolved — measured / settled / done", steps: SIGNAL_STEPS },
  { name: "red", label: "danger", steps: SIGNAL_STEPS },
  { name: "green", label: "success", steps: SIGNAL_STEPS },
  { name: "blue", label: "info", steps: SIGNAL_STEPS },
];

function Ramp({ name, label, steps, theme }: { name: string; label: string; steps: number[]; theme: Theme }) {
  const vars = useResolvedVars(steps.map((s) => `--c-${name}-${s}`), theme);
  return (
    <div className="sg-ramp">
      <div className="sg-ramp-head">
        <b>{name}</b>
        <span>{label}</span>
      </div>
      <div className="sg-ramp-steps">
        {steps.map((s) => (
          <div
            key={s}
            className="sg-step"
            style={{ background: `var(--c-${name}-${s})`, color: s <= 400 ? "#14171c" : "#f1f6fd" }}
            title={`--c-${name}-${s}: ${vars[`--c-${name}-${s}`] ?? ""}`}
          >
            <code>{s}</code>
          </div>
        ))}
      </div>
    </div>
  );
}

// Theme role tokens (resolved per theme). Glyph + label carry meaning, not color alone.
const ROLES = [
  ["--bg", "canvas"], ["--panel", "panel"], ["--elevated", "elevated"], ["--well", "well"],
  ["--field", "field"], ["--hairline", "hairline"], ["--structural", "structural"], ["--focus", "focus"],
  ["--ink", "ink"], ["--muted", "muted"], ["--primary", "primary"], ["--signal", "signal ●"], ["--resolved", "resolved ✓"],
  ["--danger", "danger ✕"], ["--success", "success ✓"], ["--info", "info ◆"],
] as const;

function Roles({ theme }: { theme: Theme }) {
  const vars = useResolvedVars(ROLES.map((r) => r[0]), theme);
  return (
    <div className="sg-swatches">
      {ROLES.map(([v, name]) => (
        <div className="sg-swatch" key={v}>
          <div className="chip" style={{ background: `var(${v})` }} />
          <b>{name}</b>
          <code>{vars[v]}</code>
        </div>
      ))}
    </div>
  );
}

const TYPE_SIZES = [
  ["5xl", "Display"], ["4xl", "—"], ["3xl", "—"], ["2xl", "—"], ["xl", "Heading"],
  ["lg", "—"], ["md", "—"], ["base", "Body"], ["sm", "Caption"], ["xs", "Label"],
] as const;
const SPACE_STEPS = [2, 4, 6, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80, 96];
const RADII = ["none", "xs", "sm", "md", "lg", "xl", "2xl", "full"];
const SHADOWS = ["xs", "sm", "md", "lg", "xl"];
const ICON_SIZES = [["xs", 14], ["sm", 16], ["md", 20], ["lg", 24], ["xl", 32]] as const;
const MOTION = [
  ["fast", "--dur-fast", "--ease-standard"],
  ["normal", "--dur-normal", "--ease-decelerate"],
  ["slow", "--dur-slow", "--ease-emphasis"],
] as const;

export function Foundation({ theme }: { theme: Theme }) {
  return (
    <>
      <div className="sg-intro">
        <h2>Foundation primitives</h2>
        <p>
          The raw, theme-agnostic values everything derives from — verified, on-grid, and
          consumed only through semantic roles. Color ramps are OKLCH-derived with hexes pinned
          and gated by <code>contrast.py</code>; every signal pairs with a glyph or label so
          color is never the only channel.
        </p>
      </div>

      <Section id="color" title="Color ramps" desc="Two neutral ramps, the indigo primary, and five signal ramps. Step 500 is the saturated anchor. Hover a step for its token + hex.">
        <div className="sg-card">
          {RAMPS.map((r) => <Ramp key={r.name} {...r} theme={theme} />)}
        </div>
      </Section>

      <Section id="roles" title="Theme roles (scaffold)" desc="How primitives map to surface / text / border / signal roles in the active theme. Phase 2 expands this into the full semantic set.">
        <div className="sg-card"><Roles theme={theme} /></div>
      </Section>

      <Section id="type" title="Type scale" desc="IBM Plex Sans (UI/body) and IBM Plex Mono (data/traces). 1.20 minor-third scale, 16px base.">
        <div className="sg-card sg-type">
          {TYPE_SIZES.map(([sz, role]) => (
            <div className="sg-type-row" key={sz}>
              <span className="meta">{role !== "—" ? `${role} · ` : ""}{sz}</span>
              <span className="sample" style={{ fontSize: `var(--fs-${sz})`, fontWeight: "var(--fw-semibold)", letterSpacing: "var(--ls-tight)" }}>
                Reasoning, made legible.
              </span>
            </div>
          ))}
          <div className="sg-type-row">
            <span className="meta">weights</span>
            <div className="sg-weights">
              <span style={{ fontWeight: 400 }}>Regular 400</span>
              <span style={{ fontWeight: 500 }}>Medium 500</span>
              <span style={{ fontWeight: 600 }}>Semibold 600</span>
              <span style={{ fontWeight: 700 }}>Bold 700</span>
            </div>
          </div>
          <div className="sg-type-row">
            <span className="meta">mono · tabular</span>
            <div className="sg-mono-figures">confidence 0.78 · 1,204 tok · $0.0123 · 0123456789</div>
          </div>
        </div>
      </Section>

      <Section id="space" title="Spacing scale" desc="4px base grid. Density rescales role tokens in Phase 2 — these primitives stay fixed.">
        <div className="sg-card sg-scale">
          {SPACE_STEPS.map((s) => (
            <div className="sg-scale-row" key={s}>
              <span className="meta">space-{s}</span>
              <div className="sg-bar-fill" style={{ width: `var(--space-${s})` }} />
            </div>
          ))}
        </div>
      </Section>

      <Section id="radius" title="Radius" desc="Restrained corners — a precision instrument, not a soft consumer app.">
        <div className="sg-card sg-sizes">
          {RADII.map((r) => (
            <div className="sg-size-demo" key={r}>
              <div className="sg-radius-demo" style={{ borderRadius: `var(--radius-${r})` }} />
              <code>{r}</code>
            </div>
          ))}
        </div>
      </Section>

      <Section id="sizes" title="Icon & control sizes" desc="Fixed pixel sizes for icons, avatars, and control heights (≥44px touch target where touch applies).">
        <div className="sg-card sg-sizes">
          {ICON_SIZES.map(([name, px]) => (
            <div className="sg-size-demo" key={name}>
              <div className="sg-size-box" style={{ width: `var(--icon-${name})`, height: `var(--icon-${name})` }} />
              <code>icon-{name} · {px}</code>
            </div>
          ))}
        </div>
      </Section>

      <Section id="elevation" title="Elevation" desc="Shadows tuned for the dark canvas: deep, low-spread. Best judged in the dark theme.">
        <div className="sg-card sg-elevations">
          {SHADOWS.map((s) => (
            <div className="sg-elevation" key={s} style={{ boxShadow: `var(--shadow-${s})` }}>
              <code>shadow-{s}</code>
            </div>
          ))}
        </div>
      </Section>

      <Section id="motion" title="Motion" desc="Brisk and mechanical durations + easings. Reduced-motion parks the dot at rest.">
        <div className="sg-card sg-motion">
          {MOTION.map(([name, dur, ease]) => (
            <div className="sg-motion-row" key={name}>
              <span className="meta">{name} · {dur.replace("--dur-", "")}</span>
              <div className="sg-motion-track">
                <div
                  className="sg-motion-dot"
                  style={{ animationDuration: `var(${dur})`, ["--_ease" as string]: `var(${ease})` }}
                />
              </div>
            </div>
          ))}
        </div>
      </Section>
    </>
  );
}
