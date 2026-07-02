import { describe, it, expect } from "vitest";
import { formFromStatus, paramsFromForm, originHint } from "./settingsView";
import type { ConfigStatus } from "../ipc/types";

const status: ConfigStatus = {
  model: "anthropic:claude-sonnet-4-6",
  provider: "anthropic",
  key_var: "ANTHROPIC_API_KEY",
  key_present: true,
  problems: [],
  settings: {
    debate_rounds: 3,
    judge_threshold: 0.8,
    judge_max_retries: 2,
    max_retries: 4,
  },
  origins: {
    model: "db",
    debate_rounds: "db",
    judge_threshold: "db",
    judge_max_retries: "db",
    max_retries: "db",
  },
  providers: [],
};

describe("formFromStatus", () => {
  it("maps settings into form fields and never echoes secrets", () => {
    const form = formFromStatus(status);
    expect(form.debateRounds).toBe(3);
    expect(form.judgeThreshold).toBe(0.8);
    expect(form.judgeMaxRetries).toBe(2);
    expect(form.maxRetries).toBe(4);
    expect(form.apiKey).toBe("");
  });
});

describe("paramsFromForm", () => {
  it("derives provider from the model prefix and omits blank secrets", () => {
    const params = paramsFromForm({ ...formFromStatus(status), model: "openai:gpt-4o" });
    expect(params.provider).toBe("openai");
    expect(params.api_key).toBeUndefined();
    expect(params.settings?.debate_rounds).toBe(3);
  });

  it("keeps the selected provider for a bare model id and passes typed secrets", () => {
    const form = { ...formFromStatus(status), model: "bare-model", apiKey: "sk-x" };
    const params = paramsFromForm(form);
    expect(params.provider).toBe("anthropic");
    expect(params.api_key).toBe("sk-x");
  });
});

it("originHint labels env and override tiers only", () => {
  const origins = { debate_rounds: "env", model: "override", max_retries: "db" } as const;
  expect(originHint(origins, "debate_rounds")).toMatch(/environment/i);
  expect(originHint(origins, "model")).toMatch(/--set/);
  expect(originHint(origins, "max_retries")).toBeNull();
  expect(originHint(undefined, "model")).toBeNull();
});
