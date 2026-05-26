import { computed } from "vue";

/**
 * Codex CLI / OpenAI-compatible base URL from how the user opened the admin UI
 * (intranet IP, public IP, or domain — protocol + host + port included).
 */
export function useApiEndpoint() {
  const origin =
    typeof window !== "undefined" && window.location?.origin
      ? window.location.origin
      : "";

  const apiBaseUrl = computed(() => (origin ? `${origin}/v1` : ""));

  const codexConfigSnippet = computed(() => {
    const base = apiBaseUrl.value;
    if (!base) return "";
    return `[model_providers.codex-pool]
name = "OpenAI"
base_url = "${base}"
wire_api = "responses"`;
  });

  return { origin, apiBaseUrl, codexConfigSnippet };
}
