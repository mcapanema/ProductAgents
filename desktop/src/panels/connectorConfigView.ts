import type { ConnectorConfigEntry, ConnectorSchema } from "../ipc/types";

export interface ConnectorField {
  name: string;
  kind: "string" | "number" | "boolean";
  secretRef: boolean;
  required: boolean;
}

const KINDS: Record<string, ConnectorField["kind"]> = {
  string: "string",
  number: "number",
  integer: "number",
  boolean: "boolean",
};

/** Flat, typed schema properties -> form fields. `enabled` gets its own toggle. */
export function fieldsFromSchema(schema: ConnectorSchema | null): ConnectorField[] {
  if (!schema?.properties) return [];
  const required = new Set(schema.required ?? []);
  return Object.entries(schema.properties)
    .filter(([name, prop]) => name !== "enabled" && prop.type !== undefined && KINDS[prop.type!])
    .map(([name, prop]) => ({
      name,
      kind: KINDS[prop.type!],
      secretRef: name.endsWith("_env"),
      required: required.has(name),
    }));
}

/** The raw block to save: config + edits + enabled, blanks dropped. */
export function blockFromFields(
  entry: ConnectorConfigEntry,
  edits: Record<string, unknown>,
  enabled: boolean,
): Record<string, unknown> {
  const merged: Record<string, unknown> = { ...entry.config, ...edits, enabled };
  for (const [key, value] of Object.entries(merged)) {
    if (value === "" || value === undefined || value === null) delete merged[key];
  }
  return merged;
}
