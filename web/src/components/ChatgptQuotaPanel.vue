<template>
  <div v-loading="loading" class="quota-panel">
    <div v-if="error" class="quota-error">{{ error }}</div>
    <template v-else-if="quota">
      <div class="quota-meta">
        <el-tag v-if="quota.plan_type" size="small" effect="light">{{ quota.plan_type }}</el-tag>
        <span v-if="quota.email" class="quota-email">{{ quota.email }}</span>
        <el-tag v-if="quota.limit_reached" type="danger" size="small">已达上限</el-tag>
      </div>
      <div v-if="quota.five_hour" class="quota-item">
        <div class="quota-head">
          <span>5 小时额度</span>
          <span class="quota-remain">剩余 {{ formatPct(quota.five_hour.remaining_percent) }}</span>
        </div>
        <el-progress
          :percentage="quota.five_hour.remaining_percent"
          :status="statusFromRemaining(quota.five_hour.remaining_percent)"
          :stroke-width="10"
        />
        <p v-if="quota.five_hour.reset_after_seconds" class="quota-reset">
          约 {{ formatReset(quota.five_hour.reset_after_seconds) }} 后重置
        </p>
      </div>
      <div v-if="quota.weekly" class="quota-item">
        <div class="quota-head">
          <span>一周额度</span>
          <span class="quota-remain">剩余 {{ formatPct(quota.weekly.remaining_percent) }}</span>
        </div>
        <el-progress
          :percentage="quota.weekly.remaining_percent"
          :status="statusFromRemaining(quota.weekly.remaining_percent)"
          :stroke-width="10"
        />
        <p v-if="quota.weekly.reset_after_seconds" class="quota-reset">
          约 {{ formatReset(quota.weekly.reset_after_seconds) }} 后重置
        </p>
      </div>
    </template>
  </div>
</template>

<script setup>
defineProps({
  quota: { type: Object, default: null },
  loading: { type: Boolean, default: false },
  error: { type: String, default: "" },
});

function formatPct(n) {
  return `${Math.round(Number(n) || 0)}%`;
}

function formatReset(seconds) {
  const s = Math.max(0, Number(seconds) || 0);
  const days = Math.floor(s / 86400);
  const hours = Math.floor((s % 86400) / 3600);
  const mins = Math.floor((s % 3600) / 60);
  if (days > 0) return `${days} 天 ${hours} 小时`;
  if (hours > 0) return `${hours} 小时 ${mins} 分钟`;
  return `${mins} 分钟`;
}

function statusFromRemaining(remaining) {
  if (remaining <= 5) return "exception";
  if (remaining <= 20) return "warning";
  return "success";
}
</script>

<style scoped>
.quota-panel {
  min-height: 48px;
}

.quota-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.quota-email {
  font-size: 13px;
  color: var(--cp-text-muted);
}

.quota-item + .quota-item {
  margin-top: 14px;
}

.quota-head {
  display: flex;
  justify-content: space-between;
  gap: 8px;
  font-size: 13px;
  margin-bottom: 6px;
}

.quota-head span:first-child {
  color: var(--cp-text);
  font-weight: 500;
}

.quota-remain {
  font-weight: 600;
  color: var(--el-color-primary);
}

.quota-reset {
  margin: 4px 0 0;
  font-size: 12px;
  color: var(--cp-text-muted);
}

.quota-error {
  font-size: 13px;
  color: var(--el-color-danger);
}
</style>
