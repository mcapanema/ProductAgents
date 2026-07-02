import type { ConfigSetParams, ConfigStatus } from "../ipc/types";

export const LOG_LEVELS = ["DEBUG", "INFO", "WARNING", "ERROR"] as const;

export interface SettingsForm {
  model: string;
  provider: string;
  apiKey: string;
  debateRounds: number;
  judgeThreshold: number;
  judgeMaxRetries: number;
  maxRetries: number;
  logLevel: string;
  githubRepo: string;
  githubToken: string;
}

/** Seed the form from a config.get status. Secrets are never echoed. */
export function formFromStatus(s: ConfigStatus): SettingsForm {
  return {
    model: s.model,
    provider: s.provider,
    apiKey: "",
    debateRounds: s.settings.debate_rounds,
    judgeThreshold: s.settings.judge_threshold,
    judgeMaxRetries: s.settings.judge_max_retries,
    maxRetries: s.settings.max_retries,
    logLevel: s.settings.log_level,
    githubRepo: s.settings.github_repo,
    githubToken: "",
  };
}

/** Build the config.set payload; a `provider:` model prefix wins over the dropdown. */
export function paramsFromForm(f: SettingsForm): ConfigSetParams {
  const provider = f.model.includes(":") ? f.model.split(":")[0] : f.provider;
  const params: ConfigSetParams = {
    model: f.model,
    provider,
    settings: {
      debate_rounds: f.debateRounds,
      judge_threshold: f.judgeThreshold,
      judge_max_retries: f.judgeMaxRetries,
      max_retries: f.maxRetries,
      log_level: f.logLevel,
      github_repo: f.githubRepo,
    },
  };
  if (f.apiKey) params.api_key = f.apiKey;
  if (f.githubToken) params.settings!.github_token = f.githubToken;
  return params;
}
