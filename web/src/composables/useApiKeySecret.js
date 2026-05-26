import { ref } from "vue";
import { ElMessage } from "element-plus";
import { revealApiKey } from "../api";
import { cacheApiKey, getCachedApiKey } from "../utils/apiKeyCache";

export function useApiKeySecret() {
  const resolving = ref(false);

  async function resolveApiKey(row, { quiet = false } = {}) {
    if (!row?.id) return "";
    const cached = getCachedApiKey(row.id);
    if (cached) return cached;

    if (!row.has_secret) {
      if (!quiet) {
        ElMessage.warning("此 Key 为旧数据无完整密钥记录，请删除后重新创建");
      }
      return "";
    }

    resolving.value = true;
    try {
      const { data } = await revealApiKey(row.id);
      if (data?.key) {
        cacheApiKey(row.id, data.key);
        return data.key;
      }
    } catch (err) {
      if (!quiet) {
        const detail = err.response?.data?.detail;
        ElMessage.error(typeof detail === "string" ? detail : "无法读取 API Key");
      }
    } finally {
      resolving.value = false;
    }
    return "";
  }

  return { resolving, resolveApiKey, cacheApiKey };
}
