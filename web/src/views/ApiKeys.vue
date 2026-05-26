<template>
  <div class="page">
    <div class="apikeys-hero">
      <div class="hero-copy">
        <span class="hero-kicker">CLIENT ACCESS</span>
        <h2>API 密钥管理</h2>
        <p>为 Codex、Cursor 等客户端签发密钥，统一接入本服务的 OpenAI 兼容端点。</p>
        <ApiEndpointBar class="hero-endpoint" embedded />
      </div>
      <div class="hero-stats" aria-label="密钥概览">
        <div class="stat-tile">
          <span class="stat-label">总密钥</span>
          <strong>{{ totalKeys }}</strong>
        </div>
        <div class="stat-tile">
          <span class="stat-label">启用中</span>
          <strong>{{ enabledKeys }}</strong>
        </div>
        <div class="stat-tile">
          <span class="stat-label">已停用</span>
          <strong>{{ disabledKeys }}</strong>
        </div>
      </div>
    </div>

    <section v-loading="loading" class="group-section keys-section">
      <header class="group-header">
        <div class="group-title">
          <span class="group-icon keys" aria-hidden="true">
            <el-icon><Key /></el-icon>
          </span>
          <div>
            <h2 class="group-name">客户端密钥</h2>
            <p class="group-desc">管理客户端访问 Codex Pool 的 API 密钥</p>
          </div>
        </div>
        <div class="section-meta">
          <span class="meta-pill">{{ keys.length }} 个密钥</span>
          <span class="meta-pill success">{{ enabledKeys }} 启用</span>
        </div>
        <el-button type="primary" class="add-btn" @click="openCreate">
          <el-icon><Plus /></el-icon>
          创建 API Key
        </el-button>
      </header>

      <div class="table-shell">
        <el-table :data="keys" empty-text="暂无 API Key，点击右上角创建" class="group-table">
          <el-table-column label="名称" min-width="170">
            <template #default="{ row }">
              <div class="name-cell">
                <span class="name-mark keys"><el-icon><Key /></el-icon></span>
                <span>
                  <strong>{{ row.name }}</strong>
                  <small>Client API key</small>
                </span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="Key 前缀" min-width="200">
            <template #default="{ row }">
              <span class="key-mask">{{ row.key_prefix || "—" }}</span>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="92" align="center">
            <template #default="{ row }">
              <button
                type="button"
                :class="['status-pill', row.enabled ? 'is-on' : 'is-off']"
                :title="row.enabled ? '点击停用' : '点击启用'"
                @click="toggle(row)"
              >
                {{ row.enabled ? "启用" : "停用" }}
              </button>
            </template>
          </el-table-column>
          <el-table-column label="创建时间" min-width="168">
            <template #default="{ row }">
              <span class="time-cell">{{ formatDate(row.created_at) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="320" fixed="right">
            <template #default="{ row }">
              <div class="action-cluster">
                <el-button
                  link
                  type="primary"
                  class="action-link"
                  :loading="resolving && actionRowId === row.id"
                  @click="copyKey(row)"
                >
                  <el-icon><CopyDocument /></el-icon>
                  复制
                </el-button>
                <el-button
                  link
                  type="primary"
                  class="action-link"
                  :loading="resolving && actionRowId === row.id"
                  @click="openConfigGuide(row)"
                >
                  <el-icon><Setting /></el-icon>
                  配置
                </el-button>
                <el-button
                  link
                  type="primary"
                  class="action-link"
                  :loading="resolving && actionRowId === row.id"
                  @click="importToCcSwitch(row)"
                >
                  <el-icon><Upload /></el-icon>
                  CC Switch
                </el-button>
                <el-button link type="danger" class="action-link" @click="remove(row)">
                  <el-icon><Delete /></el-icon>
                  删除
                </el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </section>

    <el-dialog v-model="showCreate" title="新建 API Key" width="480px" align-center>
      <el-form label-position="top">
        <el-form-item label="名称">
          <el-input v-model="newName" placeholder="例如：MacBook Codex" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" @click="create">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showSecret" title="API Key 已创建" width="560px" align-center>
      <el-alert
        type="success"
        :closable="false"
        show-icon
        title="密钥已保存，可随时在列表中「复制」或导入 CC Switch。"
        class="hint-alert"
      />
      <el-input class="mt" v-model="createdKey" readonly>
        <template #append>
          <el-button @click="copyText(createdKey)">复制</el-button>
        </template>
      </el-input>
      <div class="secret-actions">
        <el-button @click="openConfigGuideFromSecret">配置说明</el-button>
        <el-button type="primary" @click="importToCcSwitchFromSecret">打开 CC Switch 导入</el-button>
      </div>
    </el-dialog>

    <CodexConfigGuideDialog
      v-model="guideVisible"
      :key-name="activeKeyName"
      :api-key="activeApiKey"
      :loading="guideLoading"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from "vue";
import { Plus, Key, CopyDocument, Setting, Upload, Delete } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import ApiEndpointBar from "../components/ApiEndpointBar.vue";
import CodexConfigGuideDialog from "../components/CodexConfigGuideDialog.vue";
import { createApiKey, deleteApiKey, listApiKeys, updateApiKey } from "../api";
import { useApiEndpoint } from "../composables/useApiEndpoint";
import { useApiKeySecret } from "../composables/useApiKeySecret";
import { removeCachedApiKey } from "../utils/apiKeyCache";
import { buildCcSwitchCodexImportUrl, openCcSwitchImport } from "../utils/ccSwitchDeepLink";

const keys = ref([]);
const loading = ref(false);
const showCreate = ref(false);
const showSecret = ref(false);
const newName = ref("");
const createdKey = ref("");
const createdKeyId = ref(null);
const guideVisible = ref(false);
const guideLoading = ref(false);
const activeKeyName = ref("default");
const activeApiKey = ref("");
const actionRowId = ref(null);

const totalKeys = computed(() => keys.value.length);
const enabledKeys = computed(() => keys.value.filter((k) => k.enabled).length);
const disabledKeys = computed(() => keys.value.filter((k) => !k.enabled).length);

const { apiBaseUrl } = useApiEndpoint();
const { resolving, resolveApiKey, cacheApiKey } = useApiKeySecret();

function formatDate(value) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

async function load() {
  loading.value = true;
  try {
    const { data } = await listApiKeys();
    keys.value = data;
  } finally {
    loading.value = false;
  }
}

function openCreate() {
  newName.value = "";
  showCreate.value = true;
}

async function create() {
  const { data } = await createApiKey(newName.value);
  createdKey.value = data.key;
  createdKeyId.value = data.id;
  cacheApiKey(data.id, data.key);
  showCreate.value = false;
  showSecret.value = true;
  await load();
}

async function toggle(row) {
  row.enabled = !row.enabled;
  try {
    await updateApiKey(row.id, { enabled: row.enabled });
  } catch {
    row.enabled = !row.enabled;
  }
}

async function remove(row) {
  await ElMessageBox.confirm(`删除 ${row.name}?`, "确认");
  await deleteApiKey(row.id);
  removeCachedApiKey(row.id);
  ElMessage.success("已删除");
  await load();
}

function copyText(text) {
  if (!text) return;
  navigator.clipboard.writeText(text);
  ElMessage.success("已复制");
}

async function copyKey(row) {
  actionRowId.value = row.id;
  const key = await resolveApiKey(row);
  actionRowId.value = null;
  if (key) copyText(key);
}

async function openConfigGuide(row) {
  actionRowId.value = row.id;
  guideLoading.value = true;
  activeKeyName.value = row.name;
  activeApiKey.value = await resolveApiKey(row);
  guideLoading.value = false;
  actionRowId.value = null;
  guideVisible.value = true;
}

async function importToCcSwitch(row) {
  actionRowId.value = row.id;
  const key = await resolveApiKey(row);
  actionRowId.value = null;
  if (!key) return;
  if (!apiBaseUrl.value) {
    ElMessage.error("无法解析 API 端点地址");
    return;
  }
  const url = buildCcSwitchCodexImportUrl({
    name: row.name,
    endpoint: apiBaseUrl.value,
    apiKey: key,
    enabled: true,
  });
  openCcSwitchImport(url);
  ElMessage.success("正在打开 CC Switch 并导入配置…");
}

function openConfigGuideFromSecret() {
  activeKeyName.value = newName.value || "default";
  activeApiKey.value = createdKey.value;
  guideVisible.value = true;
}

function importToCcSwitchFromSecret() {
  if (!createdKey.value) return;
  if (!apiBaseUrl.value) {
    ElMessage.error("无法解析 API 端点地址");
    return;
  }
  const url = buildCcSwitchCodexImportUrl({
    name: newName.value || "Codex Pool",
    endpoint: apiBaseUrl.value,
    apiKey: createdKey.value,
    enabled: true,
  });
  openCcSwitchImport(url);
  ElMessage.success("正在打开 CC Switch 并导入配置…");
}

onMounted(load);
</script>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding-bottom: 24px;
}

.apikeys-hero {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: center;
  gap: 24px;
  padding: 22px 24px;
  border: 1px solid #dbe7f3;
  border-radius: 8px;
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.96), rgba(248, 252, 255, 0.92)),
    radial-gradient(circle at 0 0, rgba(56, 189, 248, 0.18), transparent 34%),
    radial-gradient(circle at 100% 0, rgba(139, 92, 246, 0.12), transparent 30%);
  box-shadow: 0 14px 34px rgba(15, 23, 42, 0.07);
}

.hero-copy {
  min-width: 0;
}

.hero-kicker {
  display: inline-flex;
  align-items: center;
  height: 24px;
  padding: 0 9px;
  border: 1px solid #cfe8f6;
  border-radius: 999px;
  background: #f4fbff;
  color: #0369a1;
  font-size: 11px;
  font-weight: 800;
}

.hero-copy h2 {
  margin: 10px 0 6px;
  color: var(--cp-text);
  font-size: 24px;
  line-height: 1.25;
}

.hero-copy p {
  margin: 0;
  font-size: 14px;
  color: var(--cp-text-muted);
}

.hero-endpoint {
  margin-top: 14px;
}

.hero-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(88px, 1fr));
  gap: 10px;
}

.stat-tile {
  min-width: 88px;
  padding: 12px 14px;
  border: 1px solid #dcecf7;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.78);
}

.stat-label {
  display: block;
  color: var(--cp-text-subtle);
  font-size: 12px;
  font-weight: 700;
}

.stat-tile strong {
  display: block;
  margin-top: 5px;
  color: #0f172a;
  font-size: 24px;
  line-height: 1;
}

.group-section {
  padding: 0;
  overflow: hidden;
  border: 1px solid #dde6f0;
  border-radius: 8px;
  background: #ffffff;
  box-shadow: 0 10px 26px rgba(15, 23, 42, 0.06);
}

.keys-section {
  border-top: 3px solid #38bdf8;
}

.group-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 20px;
  border-bottom: 1px solid #edf2f7;
  background: linear-gradient(180deg, #ffffff, #fbfdff);
}

.group-title {
  display: flex;
  align-items: center;
  gap: 14px;
  flex: 1 1 auto;
  min-width: 0;
}

.group-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 8px;
  flex-shrink: 0;
  box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.68);
}

.group-icon.keys {
  background: #ecfeff;
  color: #0891b2;
}

.group-name {
  margin: 0;
  font-size: 17px;
  font-weight: 800;
  color: var(--cp-text);
}

.group-desc {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--cp-text-muted);
}

.section-meta {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
  margin-left: auto;
}

.meta-pill {
  display: inline-flex;
  align-items: center;
  height: 28px;
  padding: 0 10px;
  border: 1px solid #e2e8f0;
  border-radius: 999px;
  background: #f8fafc;
  color: #475569;
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
}

.meta-pill.success {
  border-color: #bbf7d0;
  background: #f0fdf4;
  color: #15803d;
}

.add-btn {
  flex-shrink: 0;
  cursor: pointer;
  font-weight: 700;
}

.add-btn :deep(.el-icon) {
  font-size: 15px;
}

.table-shell {
  overflow-x: auto;
}

.group-table {
  --el-table-border-color: transparent;
  --el-table-header-bg-color: #f8fafc;
  width: 100%;
}

.group-table :deep(.el-table__header th) {
  height: 46px;
  background: #f8fafc !important;
  color: #64748b;
  font-size: 12px;
  font-weight: 800;
}

.group-table :deep(.el-table__row td) {
  height: 68px;
  border-bottom-color: #edf2f7;
}

.group-table :deep(.el-table__row:hover td) {
  background: #f8fcff !important;
}

.group-table :deep(.el-table__cell) {
  padding: 10px 0;
}

.group-table :deep(.el-table__inner-wrapper::before) {
  display: none;
}

.group-table :deep(.el-table__fixed-right) {
  box-shadow: -8px 0 18px rgba(15, 23, 42, 0.04);
}

.name-cell {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  max-width: 100%;
  min-width: 0;
}

.name-cell strong,
.name-cell small {
  display: block;
  min-width: 0;
}

.name-cell strong {
  color: #0f172a;
  font-size: 14px;
  font-weight: 800;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.name-cell small {
  margin-top: 3px;
  color: #64748b;
  font-size: 12px;
  font-weight: 600;
}

.name-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border-radius: 8px;
  flex-shrink: 0;
}

.name-mark.keys {
  background: #ecfeff;
  color: #0891b2;
}

.key-mask,
.time-cell {
  display: inline-flex;
  align-items: center;
  max-width: 100%;
  min-height: 30px;
  padding: 0 10px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #f8fafc;
  color: #334155;
  font-size: 12px;
  font-weight: 600;
}

.key-mask {
  font-family: "Fira Code", monospace;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.time-cell {
  font-variant-numeric: tabular-nums;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 28px;
  padding: 0 10px;
  border-radius: 999px;
  border: none;
  font-size: 12px;
  font-weight: 800;
  white-space: nowrap;
  cursor: pointer;
  font-family: inherit;
  transition: opacity 0.15s ease, transform 0.15s ease;
}

.status-pill:hover {
  opacity: 0.88;
}

.status-pill:active {
  transform: scale(0.97);
}

.status-pill.is-on {
  border: 1px solid #bbf7d0;
  background: #f0fdf4;
  color: #15803d;
}

.status-pill.is-off {
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  color: #64748b;
}

.action-cluster {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 12px;
  flex-wrap: nowrap;
  white-space: nowrap;
}

.action-link {
  cursor: pointer;
  font-weight: 700;
}

.action-cluster :deep(.el-button) {
  margin-left: 0;
  padding: 0;
}

.action-link :deep(.el-icon) {
  margin-right: 3px;
}

.secret-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  margin-top: 16px;
}

.hint-alert {
  margin-bottom: 12px;
}

.mt {
  margin-top: 12px;
}

@media (max-width: 1024px) {
  .apikeys-hero {
    grid-template-columns: 1fr;
  }

  .hero-stats {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .group-header {
    align-items: flex-start;
    flex-wrap: wrap;
  }

  .section-meta {
    order: 3;
    width: 100%;
    justify-content: flex-start;
    margin-left: 54px;
  }
}

@media (max-width: 640px) {
  .apikeys-hero {
    padding: 18px;
  }

  .hero-copy h2 {
    font-size: 21px;
  }

  .hero-stats {
    grid-template-columns: 1fr;
  }

  .group-header {
    padding: 16px;
  }

  .group-title {
    width: 100%;
  }

  .section-meta {
    margin-left: 0;
  }

  .add-btn {
    width: 100%;
  }
}
</style>
