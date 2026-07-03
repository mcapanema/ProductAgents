/** The variables the pipeline substitutes into prompts (reference chips). */
export const KNOWN_VARIABLES = [
  "confidence",
  "critique",
  "debate",
  "evidence",
  "expected_outcomes",
  "focus",
  "history",
  "initiative",
  "lessons",
  "outcome_note",
  "persona",
  "portfolio",
  "recommendation",
  "reports",
  "risks",
  "role",
];

const VAR_RE = /\$\{?([a-zA-Z_][a-zA-Z0-9_]*)\}?/g;

export function extractVariables(text: string): string[] {
  const seen = new Set<string>();
  const out: string[] = [];
  for (const m of text.matchAll(VAR_RE)) {
    if (!seen.has(m[1])) { seen.add(m[1]); out.push(m[1]); }
  }
  return out;
}

export type DiffLine = { type: "same" | "add" | "del"; text: string };

/**
 * Minimal LCS line diff — enough for a readable prompt-edit preview.
 * ponytail: O(n·m) table over prompt-sized text (tens of lines); fine.
 */
export function lineDiff(oldText: string, newText: string): DiffLine[] {
  const a = oldText.split("\n");
  const b = newText.split("\n");
  const n = a.length, m = b.length;
  const lcs: number[][] = Array.from({ length: n + 1 }, () => new Array(m + 1).fill(0));
  for (let i = n - 1; i >= 0; i--)
    for (let j = m - 1; j >= 0; j--)
      lcs[i][j] = a[i] === b[j] ? lcs[i + 1][j + 1] + 1 : Math.max(lcs[i + 1][j], lcs[i][j + 1]);
  const out: DiffLine[] = [];
  let i = 0, j = 0;
  while (i < n && j < m) {
    if (a[i] === b[j]) { out.push({ type: "same", text: a[i] }); i++; j++; }
    else if (lcs[i + 1][j] >= lcs[i][j + 1]) { out.push({ type: "del", text: a[i] }); i++; }
    else { out.push({ type: "add", text: b[j] }); j++; }
  }
  while (i < n) out.push({ type: "del", text: a[i++] });
  while (j < m) out.push({ type: "add", text: b[j++] });
  return out;
}

export function isDirty(draft: string, original: string): boolean {
  return draft !== original;
}
