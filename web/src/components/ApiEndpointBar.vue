<template>
  <div
    class="api-endpoint-bar"
    :class="{ 'api-endpoint-bar--embedded': embedded }"
    role="region"
    aria-label="API 端点"
  >
    <span class="api-endpoint-bar__label">API 端点</span>
    <span class="api-endpoint-bar__badge">默认</span>
    <span class="api-endpoint-bar__sep" aria-hidden="true">|</span>
    <code class="api-endpoint-bar__url" :title="apiBaseUrl">{{ apiBaseUrl }}</code>
    <div class="api-endpoint-bar__actions">
      <button
        type="button"
        class="icon-btn"
        title="复制端点地址"
        :disabled="!apiBaseUrl"
        @click="copyEndpoint"
      >
        <el-icon><CopyDocument /></el-icon>
      </button>
      <button
        type="button"
        class="icon-btn"
        title="检测连通性"
        :disabled="!origin || testing"
        @click="testConnection"
      >
        <el-icon :class="{ spin: testing }"><Lightning /></el-icon>
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref } from "vue";
import { CopyDocument, Lightning } from "@element-plus/icons-vue";
import { ElMessage } from "element-plus";
import { useApiEndpoint } from "../composables/useApiEndpoint";

defineProps({
  embedded: {
    type: Boolean,
    default: false,
  },
});

const { origin, apiBaseUrl } = useApiEndpoint();
const testing = ref(false);

async function copyEndpoint() {
  const url = apiBaseUrl.value;
  if (!url) return;
  try {
    await navigator.clipboard.writeText(url);
    ElMessage.success("已复制 API 端点");
  } catch {
    ElMessage.error("复制失败，请手动选择复制");
  }
}

async function testConnection() {
  if (!origin || testing.value) return;
  testing.value = true;
  try {
    const res = await fetch(`${origin}/healthz`, { method: "GET" });
    if (!res.ok) throw new Error(String(res.status));
    ElMessage.success("服务可达");
  } catch {
    ElMessage.error("无法连接当前地址，请检查网络或反向代理");
  } finally {
    testing.value = false;
  }
}
</script>

<style scoped>
.api-endpoint-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  padding: 12px 16px;
  margin-bottom: 16px;
  background: #ffffff;
  border: 1px solid #dcecf7;
  border-radius: 8px;
  box-shadow: 0 4px 14px rgba(15, 23, 42, 0.04);
}

.api-endpoint-bar--embedded {
  margin-bottom: 0;
  background: rgba(255, 255, 255, 0.82);
}

.api-endpoint-bar__label {
  font-size: 13px;
  font-weight: 800;
  color: #0f172a;
  flex-shrink: 0;
}

.api-endpoint-bar__badge {
  flex-shrink: 0;
  padding: 2px 8px;
  font-size: 11px;
  font-weight: 800;
  color: #15803d;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 999px;
}

.api-endpoint-bar__sep {
  color: #cbd5e1;
  user-select: none;
}

.api-endpoint-bar__url {
  flex: 1;
  min-width: 0;
  font-family: "Fira Code", ui-monospace, monospace;
  font-size: 13px;
  font-weight: 600;
  color: #334155;
  word-break: break-all;
}

.api-endpoint-bar__actions {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-left: auto;
  flex-shrink: 0;
}

.icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  padding: 0;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #f8fafc;
  color: #64748b;
  cursor: pointer;
  transition: color 0.15s ease, background 0.15s ease, border-color 0.15s ease;
}

.icon-btn:hover:not(:disabled) {
  color: #0284c7;
  border-color: #bae6fd;
  background: #ecfeff;
}

.icon-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.icon-btn .spin {
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
