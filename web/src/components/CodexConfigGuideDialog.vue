<template>
  <el-dialog
    v-model="visible"
    title="Codex 客户端配置说明"
    width="640px"
    align-center
    class="codex-guide-dialog"
    @closed="emit('closed')"
  >
    <div v-if="loading" v-loading="true" class="guide-loading" />
    <template v-else>
      <p class="intro">
        将 Codex CLI 指向本池的 <code>/v1</code> 端点。需同时配置
        <code>config.toml</code> 与 <code>auth.json</code>（默认目录
        <code>~/.codex/</code>，可通过 <code>CODEX_HOME</code> 修改）。
      </p>

      <el-alert
        v-if="!apiKey"
        type="warning"
        :closable="false"
        show-icon
        title="无法读取此 Key 的完整内容（可能为旧数据）。请删除后重新创建。"
        class="hint-alert"
      />

      <section class="block">
        <div class="block-head">
          <h3>1. config.toml</h3>
          <el-button size="small" @click="copy(configToml, 'config.toml')">复制</el-button>
        </div>
        <p class="path">路径：<code>~/.codex/config.toml</code></p>
        <pre class="code-block">{{ configToml }}</pre>
      </section>

      <section class="block">
        <div class="block-head">
          <h3>2. auth.json</h3>
          <el-button size="small" @click="copy(authJson, 'auth.json')">复制</el-button>
        </div>
        <p class="path">路径：<code>~/.codex/auth.json</code></p>
        <p class="note">
          将下方完整 API Key 写入 <code>OPENAI_API_KEY</code>，Codex 从该文件读取凭证，无需环境变量。
          也可在列表点击「CC Switch」一键导入到 CC Switch 应用。
        </p>
        <pre class="code-block">{{ authJson }}</pre>
      </section>

      <p class="footer-note">保存两个文件后，在终端运行 <code>codex</code> 即可。</p>
    </template>

    <template #footer>
      <el-button type="primary" @click="visible = false">知道了</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed } from "vue";
import { ElMessage } from "element-plus";
import { useApiEndpoint } from "../composables/useApiEndpoint";
import { buildAuthJson, buildConfigToml, codexProviderName } from "../utils/codexClientConfig";

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  keyName: { type: String, default: "default" },
  apiKey: { type: String, default: "" },
  loading: { type: Boolean, default: false },
});

const emit = defineEmits(["update:modelValue", "closed"]);

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit("update:modelValue", v),
});

const { apiBaseUrl } = useApiEndpoint();
const profileName = computed(() => codexProviderName(props.keyName));

const configToml = computed(() =>
  buildConfigToml({
    baseUrl: apiBaseUrl.value,
    profileName: profileName.value,
  }),
);

const authJson = computed(() => buildAuthJson(props.apiKey));

async function copy(text, label) {
  try {
    await navigator.clipboard.writeText(text);
    ElMessage.success(`已复制 ${label}`);
  } catch {
    ElMessage.error("复制失败");
  }
}
</script>

<style scoped>
.guide-loading {
  min-height: 200px;
}

.intro {
  margin: 0 0 16px;
  font-size: 14px;
  color: var(--cp-text-muted);
  line-height: 1.6;
}

.intro code,
.path code,
.note code {
  font-family: "Fira Code", ui-monospace, monospace;
  font-size: 12px;
}

.hint-alert {
  margin-bottom: 16px;
}

.block {
  margin-bottom: 18px;
}

.block-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 6px;
}

.block-head h3 {
  margin: 0;
  font-size: 15px;
  font-weight: 700;
  color: var(--cp-text);
}

.path {
  margin: 0 0 8px;
  font-size: 13px;
  color: var(--cp-text-muted);
}

.note {
  margin: 0 0 8px;
  font-size: 13px;
  color: var(--cp-text-muted);
  line-height: 1.5;
}

.footer-note {
  margin: 0;
  font-size: 13px;
  color: var(--cp-text-muted);
}

.footer-note code {
  font-family: "Fira Code", ui-monospace, monospace;
  font-size: 12px;
}

.code-block {
  margin: 0;
  padding: 12px 14px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #f8fafc;
  color: #0f172a;
  font-family: "Fira Code", ui-monospace, monospace;
  font-size: 12px;
  line-height: 1.55;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
