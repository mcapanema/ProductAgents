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

// Field-name shapes that mean "this is a secret value" by convention. Mirrors
// the server-side check (ConnectorService.config_save / _is_secret_shaped).
const SECRET_NAMES = new Set(["token", "password", "secret"]);
const SECRET_SUFFIXES = ["_token", "_key", "_secret"];

function isSecretShaped(name: string): boolean {
  return SECRET_NAMES.has(name) || SECRET_SUFFIXES.some((suffix) => name.endsWith(suffix));
}

type SchemaProp = NonNullable<ConnectorSchema["properties"]>[string];

function isStringShaped(prop: SchemaProp): boolean {
  return prop.type === "string" || Boolean(prop.anyOf?.some((p) => p.type === "string"));
}

/** Flat, typed schema properties -> form fields. `enabled` gets its own toggle.
 *
 * Secret-shaped string properties (name `token`/`password`/`secret`, or ending
 * in `_token`/`_key`/`_secret` — including optional `anyOf [string, null]`
 * shapes, which is how a `str | None` field serializes) are never rendered
 * raw: they're synthesized into a `<name>_env` secretRef field instead, so the
 * value never round-trips through the form. Non-secret anyOf-string-or-null
 * properties keep the previous behavior (skipped, same as any other untyped
 * property). */
export function fieldsFromSchema(schema: ConnectorSchema | null): ConnectorField[] {
  if (!schema?.properties) return [];
  const required = new Set(schema.required ?? []);
  const fields: ConnectorField[] = [];
  for (const [name, prop] of Object.entries(schema.properties)) {
    if (name === "enabled") continue;
    if (isSecretShaped(name) && isStringShaped(prop)) {
      fields.push({
        name: `${name}_env`,
        kind: "string",
        secretRef: true,
        required: required.has(name),
      });
      continue;
    }
    if (prop.type !== undefined && KINDS[prop.type]) {
      fields.push({
        name,
        kind: KINDS[prop.type],
        secretRef: false,
        required: required.has(name),
      });
    }
  }
  return fields;
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
