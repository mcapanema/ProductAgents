import { it, expect } from "vitest";
import { blockFromFields, fieldsFromSchema } from "./connectorConfigView";
import type { ConnectorConfigEntry } from "../ipc/types";

// Real GitHubConfig shape (owner: str, repo: str, token: str | None = None) —
// pydantic serializes the optional field as `anyOf [string, null]`. No real
// connector schema declares a `*_env` property; the form synthesizes it.
const schema = {
  properties: {
    enabled: { type: "boolean" },
    owner: { type: "string" },
    repo: { type: "string" },
    token: { anyOf: [{ type: "string" }, { type: "null" }], title: "Token" },
    weird: {},
  },
  required: ["owner", "repo"],
};

it("fieldsFromSchema flattens typed fields, synthesizes secret refs, skips enabled/unknown", () => {
  const fields = fieldsFromSchema(schema);
  expect(fields.map((f) => f.name)).toEqual(["owner", "repo", "token_env"]);
  const tokenEnv = fields.find((f) => f.name === "token_env");
  expect(tokenEnv?.secretRef).toBe(true);
  expect(tokenEnv?.required).toBe(false); // token itself is optional
  expect(fields.find((f) => f.name === "owner")?.required).toBe(true);
});

it("fieldsFromSchema synthesizes a required secretRef for a required raw secret field", () => {
  // Real JiraConfig shape: base_url/email/token required, project optional.
  const jiraSchema = {
    properties: {
      base_url: { type: "string" },
      email: { type: "string" },
      token: { type: "string" },
      project: { anyOf: [{ type: "string" }, { type: "null" }] },
    },
    required: ["base_url", "email", "token"],
  };
  const fields = fieldsFromSchema(jiraSchema);
  // project stays skipped: non-secret-shaped anyOf-string-or-null keeps prior behavior.
  expect(fields.map((f) => f.name)).toEqual(["base_url", "email", "token_env"]);
  expect(fields.find((f) => f.name === "token_env")?.required).toBe(true);
});

it("fieldsFromSchema of null is empty", () => {
  expect(fieldsFromSchema(null)).toEqual([]);
});

it("blockFromFields merges edits over config, sets enabled, drops blanks", () => {
  // entry.config reflects what's actually stored in the DB: the *_env
  // convention, not the raw schema field name.
  const entry = {
    connector: "github", installed: true,
    config: { owner: "acme", repo: "widgets", token_env: "GH" },
    schema, problems: [],
  } as ConnectorConfigEntry;
  const block = blockFromFields(entry, { repo: "gadgets", token_env: "" }, false);
  expect(block).toEqual({ owner: "acme", repo: "gadgets", enabled: false });
});
