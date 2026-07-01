// desktop/src/ui/tokens.ts
// Typed accessors for the "Instrument" design tokens — the app's public token
// API. Token VALUES live in the CSS source of truth (design/tokens/*.css,
// re-exported via ./tokens.css); this module exposes the typed NAMES + read
// helpers so consumers get autocomplete without hardcoding var() strings.

/** Semantic tokens the app resolves at runtime (e.g. to seed AntD's theme). */
export const RUNTIME_TOKENS = [
  "--accent",
  "--surface-raised",
  "--bg-primary",
  "--text-primary",
  "--text-secondary",
  "--border-default",
  "--text-error",
  "--text-success",
  "--text-warning",
  "--text-info",
  "--font-sans",
  "--radius-field",
  "--control-md",
] as const;

export type RuntimeToken = (typeof RUNTIME_TOKENS)[number];

/** A CSS custom-property name. Loose by design — the full token set lives in CSS. */
export type TokenName = `--${string}`;

/** `var(--x)` reference, for inline styles / CSS-in-JS. */
export function tokenVar(name: TokenName): string {
  return `var(${name})`;
}

/** Resolved computed value of one token from :root ("" if unset). */
export function readToken(name: TokenName): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

/** Batch-read tokens in a single getComputedStyle pass (one reflow read). */
export function readTokens<T extends readonly TokenName[]>(
  names: T,
): Record<T[number], string> {
  const cs = getComputedStyle(document.documentElement);
  const out = {} as Record<T[number], string>;
  for (const name of names) {
    out[name as T[number]] = cs.getPropertyValue(name).trim();
  }
  return out;
}
