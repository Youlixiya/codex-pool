<template>
  <div class="quota-compact">
    <div v-if="loading" class="muted">加载中…</div>
    <div v-else-if="error" class="error">无法加载</div>
    <template v-else-if="quota">
      <div v-if="quota.five_hour" class="row">
        <span class="label">5h</span>
        <el-progress
          :percentage="quota.five_hour.remaining_percent"
          :status="statusFromRemaining(quota.five_hour.remaining_percent)"
          :stroke-width="6"
          :show-text="false"
          class="bar"
        />
        <span class="value">剩余 {{ formatPct(quota.five_hour.remaining_percent) }}</span>
      </div>
      <div v-if="quota.weekly" class="row">
        <span class="label">周</span>
        <el-progress
          :percentage="quota.weekly.remaining_percent"
          :status="statusFromRemaining(quota.weekly.remaining_percent)"
          :stroke-width="6"
          :show-text="false"
          class="bar"
        />
        <span class="value">剩余 {{ formatPct(quota.weekly.remaining_percent) }}</span>
      </div>
    </template>
    <span v-else class="muted">—</span>
  </div>
</template>

<script setup>
defineProps({
  quota: { type: Object, default: null },
  loading: { type: Boolean, default: false },
  error: { type: Boolean, default: false },
});

function formatPct(n) {
  return `${Math.round(Number(n) || 0)}%`;
}

function statusFromRemaining(remaining) {
  if (remaining <= 5) return "exception";
  if (remaining <= 20) return "warning";
  return "success";
}
</script>

<style scoped>
.quota-compact {
  display: flex;
  flex-direction: column;
  gap: 8px;
  min-width: 168px;
}

.row {
  display: grid;
  grid-template-columns: 24px 1fr auto;
  align-items: center;
  gap: 8px;
}

.label {
  font-size: 12px;
  font-weight: 600;
  color: var(--cp-text-muted);
}

.value {
  font-size: 12px;
  font-weight: 500;
  color: var(--cp-text);
  white-space: nowrap;
}

.bar {
  min-width: 72px;
}

.muted {
  font-size: 13px;
  color: var(--cp-text-muted);
}

.error {
  font-size: 13px;
  color: var(--el-color-danger);
}
</style>
