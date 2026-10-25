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
import { onMounted, onUnmounted, ref } from 'vue'
import SuggestionReview from '@/components/SuggestionReview/index.vue'
import { getSuggestionSummary } from '@/infrastructure/http'
import type { SuggestionSummary } from '@/domain/smartImport'

const refreshIntervalMs = 60_000

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

onMounted(() => {
  void refresh()
  timer = setInterval(() => void refresh(), refreshIntervalMs)
})

onUnmounted(() => {
  if (timer !== null) clearInterval(timer)
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
