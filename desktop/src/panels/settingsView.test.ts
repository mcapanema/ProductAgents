import { describe, it, expect } from "vitest";
import { formFromStatus, paramsFromForm, LOG_LEVELS } from "./settingsView";
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
    log_level: "DEBUG",
    github_repo: "acme/widgets",
    github_token_present: true,
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
    expect(form.logLevel).toBe("DEBUG");
    expect(form.githubRepo).toBe("acme/widgets");
    expect(form.apiKey).toBe("");
    expect(form.githubToken).toBe("");
  });
});

describe("paramsFromForm", () => {
  it("derives provider from the model prefix and omits blank secrets", () => {
    const params = paramsFromForm({ ...formFromStatus(status), model: "openai:gpt-4o" });
    expect(params.provider).toBe("openai");
    expect(params.api_key).toBeUndefined();
    expect(params.settings?.github_token).toBeUndefined();
    expect(params.settings?.debate_rounds).toBe(3);
    expect(params.settings?.github_repo).toBe("acme/widgets");
  });

  it("keeps the selected provider for a bare model id and passes typed secrets", () => {
    const form = { ...formFromStatus(status), model: "bare-model", apiKey: "sk-x", githubToken: "ghp-y" };
    const params = paramsFromForm(form);
    expect(params.provider).toBe("anthropic");
    expect(params.api_key).toBe("sk-x");
    expect(params.settings?.github_token).toBe("ghp-y");
  });
});

it("LOG_LEVELS matches the backend vocabulary", () => {
  expect(LOG_LEVELS).toEqual(["DEBUG", "INFO", "WARNING", "ERROR"]);
});
