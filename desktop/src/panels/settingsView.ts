import type { ConfigSetParams, ConfigStatus, SettingOrigin } from "../ipc/types";

export interface SettingsForm {
  model: string;
  provider: string;
  apiKey: string;
  debateRounds: number;
  judgeThreshold: number;
  judgeMaxRetries: number;
  maxRetries: number;
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
    },
  };
  if (f.apiKey) params.api_key = f.apiKey;
  return params;
}

/** Origin hint shown under a field's description; only env/override tiers are called out. */
export function originHint(
  origins: Record<string, SettingOrigin> | undefined,
  key: string,
): string | null {
  const origin = origins?.[key];
  if (origin === "env") return "Overridden by environment";
  if (origin === "override") return "Set by --set override";
  return null;
}
