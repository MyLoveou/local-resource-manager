<template>
  <button
    v-if="summary.pending > 0"
    type="button"
    class="suggestion-badge"
    :title="`${summary.highConfidence} 条高置信建议`"
    @click="open = true"
  >
    待审阅 {{ summary.pending }}
  </button>
  <SuggestionReview v-model:show="open" @changed="refresh" />
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref, watch } from 'vue'
import SuggestionReview from '@/components/SuggestionReview/index.vue'
import { getSuggestionSummary } from '@/infrastructure/http'
import type { SuggestionSummary } from '@/domain/smartImport'

const refreshIntervalMs = 30_000

const summary = ref<SuggestionSummary>({ pending: 0, highConfidence: 0, jobs: 0 })
const open = ref(false)
let timer: ReturnType<typeof setInterval> | null = null

async function refresh(): Promise<void> {
  try {
    summary.value = await getSuggestionSummary()
  } catch {
    // 后端起不来时不打扰用户
  }
}

function onFocus(): void {
  void refresh()
}

function onVisibility(): void {
  if (document.visibilityState === 'visible') void refresh()
}

// 关闭审阅面板后立刻对齐角标，不必等下一轮轮询
watch(open, (value) => {
  if (!value) void refresh()
})

onMounted(() => {
  void refresh()
  timer = setInterval(() => void refresh(), refreshIntervalMs)
  window.addEventListener('focus', onFocus)
  document.addEventListener('visibilitychange', onVisibility)
})

onUnmounted(() => {
  if (timer !== null) clearInterval(timer)
  window.removeEventListener('focus', onFocus)
  document.removeEventListener('visibilitychange', onVisibility)
})
</script>

<style scoped lang="less">
.suggestion-badge {
  position: absolute;
  right: 16px;
  bottom: 16px;
  z-index: 30;
  padding: 6px 12px;
  border: 1px solid var(--sm-color-primary);
  border-radius: 999px;
  background: var(--sm-color-bg-surface);
  color: var(--sm-color-text);
  font-size: 12px;
  cursor: pointer;
  box-shadow: 0 2px 8px rgb(0 0 0 / 12%);

  &:hover {
    background: var(--sm-color-primary);
    color: #fff;
  }
}
</style>
