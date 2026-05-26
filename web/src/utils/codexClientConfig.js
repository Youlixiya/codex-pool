/** Default Codex model for config.toml and CC Switch deep link import. */
export const DEFAULT_CODEX_MODEL = "gpt-5.5";

/** Slug for Codex profile / codex-switch provider names. */
export function codexProfileSlug(name) {
  const slug = String(name || "default")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return slug || "default";
}

export function codexProviderName(keyName) {
  return `codex-pool-${codexProfileSlug(keyName)}`;
}

export function buildConfigToml({ baseUrl, profileName, model = DEFAULT_CODEX_MODEL }) {
  const base = baseUrl || "http://127.0.0.1:8790/v1";
  const profile = profileName || "codex-pool";
  return `model = "${model}"
model_provider = "${profile}"

[model_providers.${profile}]
name = "OpenAI"
base_url = "${base}"
wire_api = "responses"
`;
}

export function buildAuthJson(apiKey) {
  return JSON.stringify(
    {
      auth_mode: "apikey",
      OPENAI_API_KEY: apiKey || "sk-cp-你的完整API_Key",
    },
    null,
    2,
  );
}

/** codex-switch `codexs import` providers.json shape */
export function buildCodexSwitchProviders({ providerName, profileName, apiKey, baseUrl, note }) {
  const record = {
    profile: profileName,
    apiKey,
    baseUrl,
  };
  if (note) record.note = note;
  return { providers: { [providerName]: record } };
}

export function buildCodexSwitchAddCommand({
  providerName,
  profileName,
  apiKey,
  baseUrl,
  model = DEFAULT_CODEX_MODEL,
}) {
  const key = apiKey.replace(/"/g, '\\"');
  const url = baseUrl.replace(/"/g, '\\"');
  return [
    "codexs init",
    `codexs add ${providerName} --profile ${profileName} --api-key "${key}" \\`,
    `  --base-url "${url}" --create-profile --model ${model} \\`,
    `  --note "Codex Pool: ${providerName}"`,
    `codexs switch ${providerName}`,
  ].join("\n");
}

export function buildCodexSwitchImportCommands({ fileName, providerName }) {
  return [
    "npm install -g @minniexcode/codex-switch",
    "codexs init",
    `codexs import ~/${fileName} --merge`,
    `codexs switch ${providerName}`,
  ].join("\n");
}
