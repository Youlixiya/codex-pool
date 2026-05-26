import { DEFAULT_CODEX_MODEL } from "./codexClientConfig";

/**
 * CC Switch (farion1231/cc-switch) deep link — ccswitch://v1/import
 * @see https://github.com/farion1231/cc-switch
 */
export function buildCcSwitchCodexImportUrl({
  name,
  endpoint,
  apiKey,
  model = DEFAULT_CODEX_MODEL,
  enabled = true,
}) {
  const params = new URLSearchParams();
  params.set("resource", "provider");
  params.set("app", "codex");
  params.set("name", name);
  if (endpoint) params.set("endpoint", endpoint);
  if (apiKey) params.set("apiKey", apiKey);
  params.set("model", model);
  params.set("enabled", enabled ? "true" : "false");
  params.set("notes", "Codex Pool");
  return `ccswitch://v1/import?${params.toString()}`;
}

export function openCcSwitchImport(url) {
  window.location.href = url;
}
