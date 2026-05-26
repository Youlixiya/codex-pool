<template>
  <div class="dashboard" v-loading="loading">
    <div class="stat-grid">
      <div v-for="card in cards" :key="card.title" class="stat-card" :class="{ 'is-wide-value': card.wide }">
        <div class="stat-icon" :class="card.accent" aria-hidden="true">
          <component :is="card.icon" />
        </div>
        <div class="stat-body">
          <div class="label">{{ card.title }}</div>
          <div class="value" :class="{ money: card.money }">{{ card.value }}</div>
          <div class="hint">{{ card.hint }}</div>
        </div>
      </div>
    </div>

    <el-card class="section-card platform-card">
      <template #header>
        <div class="section-header">
          <span class="card-header-title">按上游拆分</span>
          <span class="section-sub">{{ platforms.length }} 个平台</span>
        </div>
      </template>
      <div v-if="platforms.length === 0" class="empty-block">
        暂无平台用量
      </div>
      <div v-else class="platform-list">
        <div v-for="p in platforms" :key="p.platform" class="platform-row">
          <div class="platform-name">{{ p.platform }}</div>
          <div class="platform-metrics">
            <span>{{ p.requests }} 次</span>
            <span>{{ p.input_tokens + p.output_tokens }} Token</span>
            <span class="cost">${{ formatMoney(p.cost_usd) }}</span>
          </div>
        </div>
      </div>
    </el-card>

    <div class="toolbar">
      <div class="toolbar-left">
        <span class="toolbar-label">时间范围:</span>
        <el-select v-model="days" size="default" style="width: 120px" @change="loadTrend">
          <el-option :value="7" label="近 7 天" />
          <el-option :value="14" label="近 14 天" />
          <el-option :value="30" label="近 30 天" />
        </el-select>
        <el-button :loading="loading" @click="refresh">
          <el-icon class="btn-icon"><Refresh /></el-icon>
          刷新
        </el-button>
      </div>
      <div class="toolbar-right">
        <span class="toolbar-label">粒度:</span>
        <el-select model-value="day" size="default" style="width: 116px">
          <el-option value="day" label="按天" />
        </el-select>
      </div>
    </div>

    <el-row :gutter="32" class="charts-row">
      <el-col :xs="24" :lg="12">
        <el-card class="section-card">
          <template #header>
            <span class="card-header-title">模型分布</span>
          </template>
          <el-table :data="models" empty-text="暂无数据" stripe size="small">
            <el-table-column prop="model" label="模型" min-width="120" show-overflow-tooltip />
            <el-table-column prop="requests" label="请求" width="72" align="right" />
            <el-table-column label="Token" min-width="120">
              <template #default="{ row }">
                <span class="token-pair">{{ row.input_tokens }} / {{ row.output_tokens }}</span>
              </template>
            </el-table-column>
            <el-table-column label="费用 ($)" width="88" align="right">
              <template #default="{ row }">${{ formatMoney(row.cost_usd) }}</template>
            </el-table-column>
          </el-table>
          <div v-if="models.length === 0" class="chart-empty">暂无数据</div>
        </el-card>
      </el-col>
      <el-col :xs="24" :lg="12">
        <el-card class="section-card trend-card">
          <template #header>
            <span class="card-header-title">Token 使用趋势</span>
          </template>
          <div v-if="trend.length === 0 || maxTrendTokens === 0" class="empty-block compact">
            <p>暂无数据</p>
          </div>
          <div v-else class="trend-chart" role="img" :aria-label="trendAriaLabel">
            <el-tooltip
              v-for="point in trend"
              :key="point.date"
              placement="top"
              effect="light"
              :show-after="120"
            >
              <template #content>
                <div class="trend-tooltip">
                  <div class="trend-tooltip-title">{{ point.date }}</div>
                  <div class="trend-tooltip-row">
                    <span>请求次数</span>
                    <strong>{{ point.requests.toLocaleString() }}</strong>
                  </div>
                  <div class="trend-tooltip-row">
                    <span>输入 Token</span>
                    <strong>{{ point.input_tokens.toLocaleString() }}</strong>
                  </div>
                  <div class="trend-tooltip-row">
                    <span>输出 Token</span>
                    <strong>{{ point.output_tokens.toLocaleString() }}</strong>
                  </div>
                  <div class="trend-tooltip-row total">
                    <span>合计 Token</span>
                    <strong>{{ (point.input_tokens + point.output_tokens).toLocaleString() }}</strong>
                  </div>
                  <div class="trend-tooltip-row">
                    <span>费用</span>
                    <strong>${{ formatMoney(point.cost_usd) }}</strong>
                  </div>
                </div>
              </template>
              <div class="trend-bar-wrap">
                <div
                  class="trend-bar"
                  :style="{ height: barHeight(point) }"
                />
                <span class="trend-label">{{ shortDate(point.date) }}</span>
              </div>
            </el-tooltip>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-alert
      v-if="loadError"
      class="mt"
      type="warning"
      :title="loadError"
      show-icon
      :closable="false"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from "vue";
import {
  Coin,
  DataLine,
  Key,
  Refresh,
  Timer,
  TrendCharts,
} from "@element-plus/icons-vue";
import {
  dashboardStats,
  modelUsage,
  platformUsage,
  usageTrend,
} from "../api";

const stats = ref(null);
const models = ref([]);
const platforms = ref([]);
const trend = ref([]);
const days = ref(7);
const loading = ref(true);
const loadError = ref("");
let refreshTimer = null;

const emptyStats = {
  balance_usd: 0,
  api_keys_enabled: 0,
  api_keys_total: 0,
  today_requests: 0,
  today_cost_usd: 0,
  today_input_tokens: 0,
  today_output_tokens: 0,
  total_input_tokens: 0,
  total_output_tokens: 0,
  rpm: 0,
  tpm: 0,
  avg_latency_ms: 0,
};

function formatMoney(v) {
  return Number(v || 0).toFixed(4);
}

const cards = computed(() => {
  const s = stats.value || emptyStats;
  const totalTokens = Number(s.total_input_tokens) + Number(s.total_output_tokens);
  const todayTokens = Number(s.today_input_tokens) + Number(s.today_output_tokens);
  return [
    {
      title: "API 密钥",
      value: String(s.api_keys_total),
      hint: `${s.api_keys_enabled} 启用`,
      icon: Key,
      accent: "accent-key",
    },
    {
      title: "今日请求",
      value: String(s.today_requests),
      hint: `总计: ${s.today_requests}`,
      icon: TrendCharts,
      accent: "accent-request",
    },
    {
      title: "今日消费",
      value: `$${Number(s.today_cost_usd).toFixed(4)} / $0.0000`,
      hint: `总计: $${Number(s.today_cost_usd).toFixed(4)} / $0.0000`,
      icon: Coin,
      accent: "accent-cost",
      money: true,
      wide: true,
    },
    {
      title: "今日 Token",
      value: todayTokens.toLocaleString(),
      hint: `输入: ${s.today_input_tokens} / 输出: ${s.today_output_tokens}`,
      icon: DataLine,
      accent: "accent-token",
    },
    {
      title: "累计 Token",
      value: totalTokens.toLocaleString(),
      hint: `输入: ${s.total_input_tokens} / 输出: ${s.total_output_tokens}`,
      icon: DataLine,
      accent: "accent-total",
    },
    {
      title: "性能指标",
      value: `${s.rpm} RPM`,
      hint: `${s.tpm} TPM`,
      icon: Timer,
      accent: "accent-violet",
    },
  ];
});

const maxTrendTokens = computed(() =>
  Math.max(0, ...trend.value.map((p) => p.input_tokens + p.output_tokens))
);

const trendAriaLabel = computed(() => {
  if (!trend.value.length) return "无趋势数据";
  const last = trend.value[trend.value.length - 1];
  return `近 ${days.value} 天 Token 趋势，最近一天 ${last.input_tokens + last.output_tokens} tokens`;
});

function shortDate(iso) {
  if (!iso) return "";
  const parts = iso.split("-");
  return parts.length >= 3 ? `${parts[1]}/${parts[2]}` : iso;
}

function barHeight(point) {
  const tokens = point.input_tokens + point.output_tokens;
  if (!maxTrendTokens.value) return "4px";
  const pct = Math.max(4, Math.round((tokens / maxTrendTokens.value) * 100));
  return `${pct}%`;
}

async function loadTrend() {
  const t = await usageTrend(days.value);
  trend.value = t.data;
}

async function refresh() {
  loading.value = true;
  loadError.value = "";
  try {
    const [s, m, p] = await Promise.all([
      dashboardStats(),
      modelUsage(),
      platformUsage(),
    ]);
    stats.value = s.data;
    models.value = m.data;
    platforms.value = p.data;
    await loadTrend();
  } catch (e) {
    loadError.value =
      e?.response?.data?.detail || e?.message || "加载仪表盘失败，请确认后端已启动并已登录";
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  refresh();
  refreshTimer = window.setInterval(refresh, 60000);
});

onUnmounted(() => {
  if (refreshTimer) clearInterval(refreshTimer);
});
</script>

<style scoped>
.dashboard {
  padding-bottom: 24px;
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  margin-bottom: 18px;
}

.stat-card {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 14px 16px;
  min-height: 86px;
  background: #ffffff;
  border: 1px solid var(--cp-glass-edge);
  border-radius: 8px;
  box-shadow: var(--cp-shadow-sm);
  transition: box-shadow var(--cp-transition), border-color var(--cp-transition);
  cursor: default;
}

.stat-card:hover {
  box-shadow: var(--cp-shadow);
  border-color: #d1d5db;
}

.stat-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 38px;
  height: 38px;
  border-radius: 8px;
  flex-shrink: 0;
  font-size: 20px;
}

.accent-key {
  background: #dbeafe;
  color: #2563eb;
}

.accent-request {
  background: #e0f2fe;
  color: #0284c7;
}

.accent-cost {
  background: #f3e8ff;
  color: #9333ea;
}

.accent-token {
  background: #fef3c7;
  color: #f59e0b;
}

.accent-total {
  background: #e0e7ff;
  color: #4f46e5;
}

.accent-violet {
  background: #ede9fe;
  color: #7c3aed;
}

.stat-body {
  min-width: 0;
  flex: 1;
}

.label {
  color: var(--cp-text-subtle);
  font-size: 12px;
  font-weight: 700;
}

.value {
  font-size: 20px;
  font-weight: 800;
  margin: 5px 0 3px;
  color: var(--cp-text);
  line-height: 1.2;
  word-break: break-word;
}

.value.money {
  color: #0ea5e9;
  font-size: 19px;
}

.stat-card.is-wide-value .value {
  font-size: clamp(14px, 1.35vw, 18px);
  white-space: nowrap;
}

.hint {
  color: var(--cp-text-subtle);
  font-size: 12px;
  line-height: 1.35;
}

.stat-card.is-wide-value .hint {
  font-size: 11px;
}

.platform-card {
  margin-bottom: 18px;
}

.section-card :deep(.el-card__header) {
  padding: 16px 18px 8px;
  border-bottom: 0;
}

.section-card :deep(.el-card__body) {
  padding: 8px 18px 18px;
}

.section-header {
  display: flex;
  flex-direction: row;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
}

.card-header-title {
  font-size: 16px;
  font-weight: 800;
  color: var(--cp-text);
}

.section-sub {
  font-size: 13px;
  color: var(--cp-text-subtle);
  font-weight: 500;
}

.empty-block {
  text-align: center;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 76px;
  border: 1px dashed #cbd5e1;
  border-radius: 8px;
  padding: 24px 16px;
  color: var(--cp-text-subtle);
  font-size: 14px;
}

.empty-block.compact {
  min-height: 180px;
  border: 0;
  padding: 36px 16px;
}

.empty-block p {
  margin: 0 0 6px;
  font-weight: 500;
  color: var(--cp-text-muted);
}

.empty-block span {
  font-size: 12px;
}

.platform-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.platform-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  padding: 12px 14px;
  border-radius: 8px;
  background: #f8fafc;
  border: 1px solid var(--cp-glass-edge);
  transition: background var(--cp-transition);
}

.platform-row:hover {
  background: #f0f9ff;
}

.platform-name {
  font-weight: 600;
  color: var(--cp-text);
}

.platform-metrics {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  font-size: 13px;
  color: var(--cp-text-muted);
}

.platform-metrics .cost {
  font-family: "Fira Code", monospace;
  color: #0ea5e9;
  font-weight: 600;
}

.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 18px;
  padding: 14px 18px;
  background: #ffffff;
  border: 1px solid var(--cp-glass-edge);
  border-radius: 8px;
  box-shadow: var(--cp-shadow-sm);
}

.toolbar-left,
.toolbar-right {
  display: flex;
  align-items: center;
  gap: 12px;
}

.toolbar-label {
  font-size: 14px;
  font-weight: 800;
  color: var(--cp-text-muted);
}

.btn-icon {
  margin-right: 4px;
}

.charts-row .el-col {
  margin-bottom: 16px;
}

.charts-row :deep(.el-card) {
  min-height: 232px;
}

.token-pair {
  font-family: "Fira Code", monospace;
  font-size: 12px;
  color: var(--cp-text-muted);
}

.trend-card :deep(.el-card__body) {
  min-height: 184px;
}

.trend-chart {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 6px;
  height: 158px;
  padding: 8px 4px 0;
}

.trend-chart :deep(.el-tooltip__trigger) {
  flex: 1;
  display: flex;
  min-width: 0;
  height: 100%;
}

.trend-bar-wrap {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  height: 100%;
  min-width: 0;
  cursor: pointer;
}

.trend-bar-wrap:hover .trend-bar {
  filter: brightness(1.05);
  box-shadow: 0 4px 12px rgba(14, 165, 233, 0.25);
}

.trend-bar {
  width: 100%;
  max-width: 36px;
  margin-top: auto;
  border-radius: 8px 8px 2px 2px;
  background: linear-gradient(180deg, #7dd3fc 0%, #0ea5e9 100%);
  min-height: 4px;
  transition: height 0.35s ease;
}

.trend-label {
  margin-top: 8px;
  font-size: 11px;
  color: var(--cp-text-subtle);
  white-space: nowrap;
}

.trend-tooltip {
  min-width: 168px;
  font-size: 12px;
  line-height: 1.5;
}

.trend-tooltip-title {
  font-weight: 800;
  color: var(--cp-text);
  margin-bottom: 8px;
  padding-bottom: 6px;
  border-bottom: 1px solid var(--cp-glass-edge);
}

.trend-tooltip-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  color: var(--cp-text-muted);
}

.trend-tooltip-row + .trend-tooltip-row {
  margin-top: 4px;
}

.trend-tooltip-row strong {
  color: var(--cp-text);
  font-family: "Fira Code", monospace;
  font-weight: 700;
}

.trend-tooltip-row.total strong {
  color: #0ea5e9;
}

.chart-empty {
  display: none;
}

@media (max-width: 768px) {
  .stat-grid {
    grid-template-columns: 1fr;
    gap: 16px;
  }

  .value {
    font-size: 22px;
  }

  .platform-row {
    flex-direction: column;
    align-items: flex-start;
  }

  .toolbar-left,
  .toolbar-right {
    width: 100%;
    flex-wrap: wrap;
  }
}

@media (min-width: 769px) and (max-width: 1120px) {
  .stat-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}
</style>
