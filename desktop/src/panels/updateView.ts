// Pure update-flow state, decoupled from the Tauri plugin so it unit-tests
// with no transport. UpdateSection owns the side effects; this owns the words.
export type UpdateState =
  | { kind: "idle" }
  | { kind: "checking" }
  | { kind: "none" }
  | { kind: "available"; version: string }
  | { kind: "installing" }
  | { kind: "error"; message: string };

export function updateStatusLabel(s: UpdateState): string {
  switch (s.kind) {
    case "idle":
      return "";
    case "checking":
      return "Checking for updates…";
    case "none":
      return "You're on the latest version.";
    case "available":
      return `Update available: ${s.version}`;
    case "installing":
      return "Downloading and installing…";
    case "error":
      return `Update check failed: ${s.message}`;
  }
}
