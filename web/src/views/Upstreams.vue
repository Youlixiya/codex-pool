<template>
  <div class="page">
    <div class="upstream-hero">
      <div class="hero-copy">
        <span class="hero-kicker">UPSTREAM ROUTING</span>
        <h2>上游接入配置</h2>
        <p>统一管理 ChatGPT 网页授权与 OpenAI 兼容中转，按优先级调度可用账号。</p>
      </div>
      <div class="hero-stats" aria-label="上游概览">
        <div class="stat-tile">
          <span class="stat-label">总上游</span>
          <strong>{{ totalUpstreams }}</strong>
        </div>
        <div class="stat-tile">
          <span class="stat-label">启用中</span>
          <strong>{{ enabledUpstreams }}</strong>
        </div>
        <div class="stat-tile">
          <span class="stat-label">已授权</span>
          <strong>{{ authorizedChatgptRows }}</strong>
        </div>
      </div>
    </div>

    <section v-loading="loading" class="group-section oauth-section">
      <header class="group-header">
        <div class="group-title">
          <span class="group-icon oauth" aria-hidden="true">
            <el-icon><User /></el-icon>
          </span>
          <div>
            <h2 class="group-name">ChatGPT 授权</h2>
            <p class="group-desc">网页 OAuth 登录，展示 5 小时与一周剩余额度</p>
          </div>
        </div>
        <div class="section-meta">
          <span class="meta-pill">{{ chatgptRows.length }} 个账号</span>
          <span class="meta-pill success">{{ authorizedChatgptRows }} 已授权</span>
        </div>
        <el-button type="primary" class="add-btn" @click="openDialog(null, 'chatgpt')">
          <el-icon><Plus /></el-icon>
          添加授权账号
        </el-button>
      </header>

      <div class="table-shell">
        <el-table
          :data="chatgptRows"
          empty-text="暂无授权账号，点击右上角添加"
          class="group-table"
        >
          <el-table-column label="名称" min-width="170">
            <template #default="{ row }">
              <div class="name-cell">
                <span class="name-mark oauth"><el-icon><User /></el-icon></span>
                <span>
                  <strong>{{ row.name }}</strong>
                  <small>{{ row.auth_file ? "OAuth credential" : "等待授权" }}</small>
                </span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="剩余额度" min-width="300">
            <template #default="{ row }">
              <ChatgptQuotaCompact
                v-if="row.auth_file"
                :quota="rowQuota[row.id]?.quota"
                :loading="rowQuota[row.id]?.loading"
                :error="rowQuota[row.id]?.error"
              />
              <span v-else class="empty-state">未授权</span>
            </template>
          </el-table-column>
          <el-table-column label="套餐" width="112">
            <template #default="{ row }">
              <span v-if="rowQuota[row.id]?.quota?.plan_type" class="plan-chip">
                {{ rowQuota[row.id].quota.plan_type }}
              </span>
              <span v-else class="cell-muted">—</span>
            </template>
          </el-table-column>
          <el-table-column label="优先级" width="94" align="center">
            <template #default="{ row }">
              <span class="priority-badge">{{ row.priority }}</span>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="92" align="center">
            <template #default="{ row }">
              <span :class="['status-pill', row.enabled ? 'is-on' : 'is-off']">
                {{ row.enabled ? "启用" : "停用" }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="220" fixed="right">
            <template #default="{ row }">
              <div class="action-cluster">
                <el-button
                  v-if="row.auth_file"
                  link
                  type="primary"
                  class="action-link"
                  @click="refreshRowQuota(row)"
                >
                  <el-icon><Refresh /></el-icon>
                  刷新
                </el-button>
                <el-button link type="primary" class="action-link" @click="openDialog(row)">
                  <el-icon><EditPen /></el-icon>
                  编辑
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

    <section class="group-section apikey-section">
      <header class="group-header">
        <div class="group-title">
          <span class="group-icon apikey" aria-hidden="true">
            <el-icon><Key /></el-icon>
          </span>
          <div>
            <h2 class="group-name">API Key 中转</h2>
            <p class="group-desc">OpenAI 兼容中转，使用 Base URL + API Key</p>
          </div>
        </div>
        <div class="section-meta">
          <span class="meta-pill">{{ openaiRows.length }} 个端点</span>
          <span class="meta-pill success">{{ enabledOpenaiRows }} 启用</span>
        </div>
        <el-button class="add-btn add-btn-secondary" @click="openDialog(null, 'openai')">
          <el-icon><Plus /></el-icon>
          添加中转
        </el-button>
      </header>

      <div class="table-shell">
        <el-table
          :data="openaiRows"
          empty-text="暂无中转账号"
          class="group-table"
        >
          <el-table-column label="名称" min-width="170">
            <template #default="{ row }">
              <div class="name-cell">
                <span class="name-mark apikey"><el-icon><Key /></el-icon></span>
                <span>
                  <strong>{{ row.name }}</strong>
                  <small>OpenAI compatible</small>
                </span>
              </div>
            </template>
          </el-table-column>
          <el-table-column label="Base URL" min-width="260" show-overflow-tooltip>
            <template #default="{ row }">
              <span class="url-cell">{{ row.base_url || "—" }}</span>
            </template>
          </el-table-column>
          <el-table-column label="API Key" min-width="150">
            <template #default="{ row }">
              <span class="key-mask">{{ row.api_key_masked || "—" }}</span>
            </template>
          </el-table-column>
          <el-table-column label="优先级" width="94" align="center">
            <template #default="{ row }">
              <span class="priority-badge">{{ row.priority }}</span>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="92" align="center">
            <template #default="{ row }">
              <span :class="['status-pill', row.enabled ? 'is-on' : 'is-off']">
                {{ row.enabled ? "启用" : "停用" }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="260" fixed="right">
            <template #default="{ row }">
              <div class="action-cluster">
                <el-button
                  link
                  type="success"
                  class="action-link"
                  :loading="rowTesting[row.id]"
                  @click="testConnection(row)"
                >
                  <el-icon v-if="!rowTesting[row.id]"><Connection /></el-icon>
                  测试连接
                </el-button>
                <el-button link type="primary" class="action-link" @click="openDialog(row)">
                  <el-icon><EditPen /></el-icon>
                  编辑
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

    <el-dialog
      v-model="visible"
      :title="form.id ? '编辑上游' : '添加上游'"
      width="580px"
      align-center
      @closed="onDialogClosed"
    >
      <el-form label-position="top">
        <el-form-item label="名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="类型">
          <el-select v-model="form.type" style="width: 100%" @change="onTypeChange">
            <el-option label="openai (中转)" value="openai" />
            <el-option label="chatgpt (OAuth)" value="chatgpt" />
          </el-select>
        </el-form-item>

        <template v-if="form.type === 'openai'">
          <el-form-item label="Base URL"><el-input v-model="form.base_url" placeholder="https://api.openai.com/v1" /></el-form-item>
          <el-form-item label="API Key"><el-input v-model="form.api_key" show-password /></el-form-item>
        </template>

        <template v-else>
          <el-form-item label="ChatGPT 授权">
            <div class="oauth-row">
              <el-button
                type="primary"
                :loading="oauthLoading"
                :disabled="!form.name.trim()"
                @click="startOAuth"
              >
                {{ oauthAuthorized ? "重新授权" : "打开网页授权" }}
              </el-button>
              <span v-if="oauthAuthorized" class="oauth-ok">
                <el-icon><CircleCheck /></el-icon>
                已授权{{ oauthEmail ? `（${oauthEmail}）` : "" }}
              </span>
            </div>
            <p v-if="!form.name.trim()" class="oauth-hint">请先填写名称再授权</p>
            <p v-else class="oauth-hint">将在新窗口打开 OpenAI 登录页，完成后自动回填凭证路径</p>
            <el-alert
              v-if="oauthRemoteSetup"
              type="warning"
              :closable="false"
              show-icon
              class="oauth-remote-alert"
              :title="oauthRemoteSetup.message"
            >
              <p class="oauth-tunnel-label">在本机终端执行端口转发后，再点击「打开网页授权」：</p>
              <code class="oauth-tunnel-cmd">{{ oauthRemoteSetup.ssh_tunnel_command }}</code>
            </el-alert>
          </el-form-item>

          <el-form-item v-if="form.auth_file" label="剩余额度">
            <div class="quota-toolbar">
              <ChatgptQuotaPanel :quota="dialogQuota" :loading="quotaLoading" :error="quotaError" />
              <el-button link type="primary" :loading="quotaLoading" class="refresh-link" @click="loadDialogQuota">
                刷新
              </el-button>
            </div>
          </el-form-item>

          <el-form-item label="Auth 文件（高级）">
            <el-input
              v-model="form.auth_file"
              placeholder="也可手动填写 ~/.codex/auth.json 路径"
              @blur="onAuthFileBlur"
            />
          </el-form-item>
        </template>

        <el-form-item label="优先级"><el-input-number v-model="form.priority" :min="1" style="width: 100%" /></el-form-item>
        <el-form-item label="启用"><el-switch v-model="form.enabled" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="visible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from "vue";
import {
  Plus,
  CircleCheck,
  User,
  Key,
  Refresh,
  EditPen,
  Delete,
  Connection,
} from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import ChatgptQuotaPanel from "../components/ChatgptQuotaPanel.vue";
import ChatgptQuotaCompact from "../components/ChatgptQuotaCompact.vue";
import {
  createUpstream,
  deleteUpstream,
  listUpstreams,
  startChatgptOAuth,
  getChatgptOAuthStatus,
  getChatgptQuota,
  getUpstreamQuota,
  testUpstreamConnection,
  updateUpstream,
} from "../api";

const rows = ref([]);
const loading = ref(false);
const visible = ref(false);
const saving = ref(false);
const oauthLoading = ref(false);
const oauthAuthorized = ref(false);
const oauthEmail = ref("");
const oauthRemoteSetup = ref(null);
const dialogQuota = ref(null);
const quotaLoading = ref(false);
const quotaError = ref("");
const rowQuota = reactive({});
const rowTesting = reactive({});
let oauthSessionId = null;
let oauthPollTimer = null;
let oauthPopup = null;

const chatgptRows = computed(() => rows.value.filter((r) => r.type === "chatgpt"));
const openaiRows = computed(() => rows.value.filter((r) => r.type === "openai"));
const totalUpstreams = computed(() => rows.value.length);
const enabledUpstreams = computed(() => rows.value.filter((r) => r.enabled).length);
const authorizedChatgptRows = computed(() => chatgptRows.value.filter((r) => r.auth_file).length);
const enabledOpenaiRows = computed(() => openaiRows.value.filter((r) => r.enabled).length);

const form = reactive({
  id: null,
  name: "",
  type: "openai",
  base_url: "",
  api_key: "",
  auth_file: "",
  priority: 1,
  enabled: true,
});

function resetOAuth() {
  stopOAuthPoll();
  oauthLoading.value = false;
  oauthSessionId = null;
  oauthEmail.value = "";
  oauthRemoteSetup.value = null;
  if (!form.auth_file) {
    oauthAuthorized.value = false;
  }
}

function resetQuota() {
  dialogQuota.value = null;
  quotaError.value = "";
  quotaLoading.value = false;
}

function onDialogClosed() {
  resetOAuth();
  resetQuota();
}

function stopOAuthPoll() {
  if (oauthPollTimer) {
    clearInterval(oauthPollTimer);
    oauthPollTimer = null;
  }
}

function onOAuthMessage(event) {
  if (event.data?.type === "codex-pool-oauth-done") {
    stopOAuthPoll();
    if (oauthSessionId) {
      pollOAuthOnce();
    }
  }
}

async function loadDialogQuota() {
  if (!form.auth_file || form.type !== "chatgpt") return;
  quotaLoading.value = true;
  quotaError.value = "";
  try {
    const { data } = await getChatgptQuota(form.auth_file);
    dialogQuota.value = data;
    if (data.email) oauthEmail.value = data.email;
  } catch (err) {
    dialogQuota.value = null;
    quotaError.value = err.response?.data?.detail || "无法获取额度";
  } finally {
    quotaLoading.value = false;
  }
}

function onAuthFileBlur() {
  if (form.type === "chatgpt" && form.auth_file) {
    oauthAuthorized.value = true;
    loadDialogQuota();
  }
}

async function loadAllQuotas() {
  const targets = chatgptRows.value.filter((r) => r.auth_file);
  await Promise.all(targets.map((row) => refreshRowQuota(row, { silent: true })));
}

async function refreshRowQuota(row, opts = {}) {
  const silent = opts.silent;
  rowQuota[row.id] = { loading: true, quota: rowQuota[row.id]?.quota ?? null, error: null };
  try {
    const { data } = await getUpstreamQuota(row.id);
    rowQuota[row.id] = { loading: false, quota: data, error: null };
    if (!silent) ElMessage.success("额度已更新");
  } catch {
    rowQuota[row.id] = { loading: false, quota: null, error: true };
    if (!silent) ElMessage.error("无法获取额度");
  }
}

async function pollOAuthOnce() {
  if (!oauthSessionId) return false;
  try {
    const { data } = await getChatgptOAuthStatus(oauthSessionId);
    if (data.status === "completed") {
      form.auth_file = data.auth_file || form.auth_file;
      oauthAuthorized.value = true;
      oauthEmail.value = data.email || "";
      oauthLoading.value = false;
      stopOAuthPoll();
      if (data.quota) {
        dialogQuota.value = data.quota;
      } else {
        await loadDialogQuota();
      }
      ElMessage.success("ChatGPT 授权成功");
      return true;
    }
    if (data.status === "failed") {
      oauthLoading.value = false;
      stopOAuthPoll();
      ElMessage.error(data.error || "授权失败");
      return true;
    }
  } catch {
    oauthLoading.value = false;
    stopOAuthPoll();
  }
  return false;
}

function startOAuthPoll() {
  stopOAuthPoll();
  oauthPollTimer = setInterval(async () => {
    const done = await pollOAuthOnce();
    if (done && oauthPopup && !oauthPopup.closed) {
      oauthPopup.close();
    }
  }, 1500);
}

async function startOAuth() {
  if (!form.name.trim()) {
    ElMessage.warning("请先填写上游名称");
    return;
  }
  resetOAuth();
  resetQuota();
  oauthLoading.value = true;
  try {
    const { data } = await startChatgptOAuth({ upstream_name: form.name.trim() });
    oauthSessionId = data.session_id;
    oauthRemoteSetup.value = data.remote_setup || null;
    if (data.remote_setup) {
      ElMessage.warning("远程访问需先配置 SSH 端口转发，见下方说明");
    }
    oauthPopup = window.open(data.authorization_url, "chatgpt-oauth", "width=520,height=720");
    if (!oauthPopup) {
      ElMessage.warning("请允许弹窗，或复制链接在浏览器打开：" + data.authorization_url);
    }
    startOAuthPoll();
  } catch (err) {
    oauthLoading.value = false;
    const msg = err.response?.data?.detail || err.message || "无法启动授权";
    ElMessage.error(typeof msg === "string" ? msg : "无法启动授权");
  }
}

function onTypeChange() {
  if (form.type === "openai") {
    resetOAuth();
    resetQuota();
  }
}

async function load() {
  loading.value = true;
  try {
    const { data } = await listUpstreams();
    rows.value = data;
    await loadAllQuotas();
  } finally {
    loading.value = false;
  }
}

function openDialog(row, defaultType) {
  resetOAuth();
  resetQuota();
  if (row) {
    Object.assign(form, {
      id: row.id,
      name: row.name,
      type: row.type,
      base_url: row.base_url || "",
      api_key: "",
      auth_file: row.auth_file || "",
      priority: row.priority,
      enabled: row.enabled,
    });
    oauthAuthorized.value = Boolean(row.auth_file && row.type === "chatgpt");
    if (row.type === "chatgpt" && row.auth_file) {
      if (rowQuota[row.id]?.quota) {
        dialogQuota.value = rowQuota[row.id].quota;
      } else {
        loadDialogQuota();
      }
    }
  } else {
    Object.assign(form, {
      id: null,
      name: "",
      type: defaultType || "openai",
      base_url: "",
      api_key: "",
      auth_file: "",
      priority: 1,
      enabled: true,
    });
  }
  visible.value = true;
}

async function save() {
  if (form.type === "chatgpt" && !form.auth_file) {
    ElMessage.warning("请先完成 ChatGPT 网页授权，或手动填写 Auth 文件路径");
    return;
  }
  saving.value = true;
  try {
    const payload = {
      name: form.name,
      type: form.type,
      base_url: form.type === "openai" ? form.base_url || null : null,
      api_key: form.type === "openai" ? form.api_key || null : null,
      auth_file: form.type === "chatgpt" ? form.auth_file || null : null,
      priority: form.priority,
      enabled: form.enabled,
    };
    if (form.id) await updateUpstream(form.id, payload);
    else await createUpstream(payload);
    ElMessage.success("已保存");
    visible.value = false;
    await load();
  } finally {
    saving.value = false;
  }
}

async function testConnection(row) {
  if (rowTesting[row.id]) return;
  rowTesting[row.id] = true;
  try {
    const { data } = await testUpstreamConnection(row.id);
    if (data.ok) {
      ElMessage.success(data.message || "连接成功");
    } else {
      ElMessage.error(data.message || "连接失败");
    }
  } catch (err) {
    const detail = err.response?.data?.detail;
    ElMessage.error(typeof detail === "string" ? detail : "测试失败");
  } finally {
    rowTesting[row.id] = false;
  }
}

async function remove(row) {
  await ElMessageBox.confirm(`删除上游 ${row.name}?`, "确认");
  await deleteUpstream(row.id);
  ElMessage.success("已删除");
  delete rowQuota[row.id];
  delete rowTesting[row.id];
  await load();
}

onMounted(() => {
  load();
  window.addEventListener("message", onOAuthMessage);
});

onUnmounted(() => {
  window.removeEventListener("message", onOAuthMessage);
  stopOAuthPoll();
});
</script>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding-bottom: 24px;
}

.upstream-hero {
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

.oauth-section {
  border-top: 3px solid #f59e0b;
}

.apikey-section {
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

.group-icon.oauth {
  background: #fff7ed;
  color: #d97706;
}

.group-icon.apikey {
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

.add-btn-secondary {
  border-color: #bae6fd;
  background: #f4fdff;
  color: #0369a1;
  cursor: pointer;
}

.add-btn-secondary:hover {
  border-color: #7dd3fc;
  background: #ecfbff;
  color: #0284c7;
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

.name-mark.oauth {
  background: #fff7ed;
  color: #d97706;
}

.name-mark.apikey {
  background: #ecfeff;
  color: #0891b2;
}

.plan-chip,
.priority-badge,
.status-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-height: 28px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 800;
  white-space: nowrap;
}

.plan-chip {
  padding: 0 11px;
  border: 1px solid #fed7aa;
  background: #fff7ed;
  color: #c2410c;
}

.priority-badge {
  min-width: 34px;
  padding: 0 10px;
  border: 1px solid #dbeafe;
  background: #eff6ff;
  color: #2563eb;
  font-family: "Fira Code", monospace;
}

.status-pill {
  padding: 0 10px;
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

.url-cell,
.key-mask {
  display: inline-flex;
  align-items: center;
  max-width: 100%;
  min-height: 30px;
  padding: 0 10px;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #f8fafc;
  color: #334155;
  font-family: "Fira Code", monospace;
  font-size: 12px;
  font-weight: 600;
}

.url-cell {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.action-cluster {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 12px;
  flex-wrap: nowrap;
  white-space: nowrap;
}

.action-link,
.refresh-link {
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

.cell-muted {
  color: var(--cp-text-muted);
  font-size: 13px;
}

.empty-state {
  display: inline-flex;
  align-items: center;
  min-height: 28px;
  padding: 0 10px;
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  background: #f8fafc;
  color: #64748b;
  font-size: 12px;
  font-weight: 700;
}

.oauth-row {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.oauth-ok {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  color: var(--el-color-success);
}

.oauth-hint {
  margin: 8px 0 0;
  font-size: 12px;
  color: var(--cp-text-muted);
}

.oauth-remote-alert {
  margin-top: 12px;
}

.oauth-tunnel-label {
  margin: 0 0 6px;
  font-size: 12px;
}

.oauth-tunnel-cmd {
  display: block;
  padding: 8px 10px;
  border-radius: 6px;
  background: #0f172a;
  color: #e2e8f0;
  font-family: "Fira Code", monospace;
  font-size: 12px;
  word-break: break-all;
}

.quota-toolbar {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

@media (max-width: 1024px) {
  .upstream-hero {
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
  .upstream-hero {
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
