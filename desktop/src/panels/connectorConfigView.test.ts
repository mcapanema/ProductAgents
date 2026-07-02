import { it, expect } from "vitest";
import { blockFromFields, fieldsFromSchema } from "./connectorConfigView";
import type { ConnectorConfigEntry } from "../ipc/types";

const schema = {
  properties: {
    enabled: { type: "boolean" },
    owner: { type: "string" },
    repo: { type: "string" },
    token_env: { type: "string" },
    weird: {},
  },
  required: ["owner", "repo"],
};

it("fieldsFromSchema flattens typed fields, marks secret refs, skips enabled/unknown", () => {
  const fields = fieldsFromSchema(schema);
  expect(fields.map((f) => f.name)).toEqual(["owner", "repo", "token_env"]);
  expect(fields.find((f) => f.name === "token_env")?.secretRef).toBe(true);
  expect(fields.find((f) => f.name === "owner")?.required).toBe(true);
});

it("fieldsFromSchema of null is empty", () => {
  expect(fieldsFromSchema(null)).toEqual([]);
});

it("blockFromFields merges edits over config, sets enabled, drops blanks", () => {
  const entry = {
    connector: "github", installed: true,
    config: { owner: "acme", repo: "widgets", token_env: "GH" },
    schema, problems: [],
  } as ConnectorConfigEntry;
  const block = blockFromFields(entry, { repo: "gadgets", token_env: "" }, false);
  expect(block).toEqual({ owner: "acme", repo: "gadgets", enabled: false });
});
