<template>
  <div class="scrape-cands" role="listbox">
    <template v-for="group in groups" :key="group.source">
      <div class="scrape-cands__group">
        {{ group.label }} · {{ group.items.length }}
      </div>
      <button
        v-for="(item, index) in group.items"
        :key="item.id ?? `${item.jobId}-${item.url}-${index}`"
        type="button"
        class="scrape-cands__item"
        :class="{ 'scrape-cands__item--picked': pickedId === item.id }"
        role="option"
        :aria-selected="pickedId === item.id"
        @click="$emit('pick', item.id ?? null)"
      >
        <img
          v-if="thumbSrc(item.thumbnailUrl)"
          class="scrape-cands__thumb"
          :src="thumbSrc(item.thumbnailUrl)"
          alt=""
          referrerpolicy="no-referrer"
        />
        <div>
          <div class="scrape-cands__title">{{ item.title }}</div>
          <div class="scrape-cands__src">{{ item.source }}</div>
        </div>
      </button>
    </template>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { scrapeImageSrc } from '@/infrastructure/http/scrape'
import type { Candidate } from '@/domain'

const props = defineProps<{
  candidates: Candidate[]
  pickedId: number | null
}>()

defineEmits<{
  pick: [number | null]
}>()

/** 渠道显示名；每渠道的结果单独成组，互不混合。 */
const SOURCE_LABEL: Record<string, string> = {
  bangumi: 'Bangumi',
  mikan: '蜜柑',
  bilibili: 'B 站',
  tmdb: 'TMDB',
  og: '网页',
}

const groups = computed(() => {
  const order: string[] = []
  const buckets = new Map<string, Candidate[]>()
  for (const item of props.candidates) {
    const source = item.source || 'other'
    if (!buckets.has(source)) {
      buckets.set(source, [])
      order.push(source)
    }
    buckets.get(source)!.push(item)
  }
  return order.map((source) => ({
    source,
    label: SOURCE_LABEL[source] ?? source,
    items: buckets.get(source)!,
  }))
})

function thumbSrc(url: string | null | undefined): string | undefined {
  if (!url) return undefined
  try {
    const parsed = new URL(url)
    if (parsed.protocol === 'https:' || parsed.protocol === 'http:') return scrapeImageSrc(url)
  } catch {
    return undefined
  }
  return undefined
}
</script>

<style scoped lang="less">
.scrape-cands {
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 240px;
  flex-shrink: 0;
  max-height: 100%;
  min-height: 0;
  overflow: auto;
  padding: 2px;
}

.scrape-cands__group {
  margin-top: 4px;
  font-size: 11px;
  font-weight: 600;
  color: var(--sm-color-text-muted);
}

.scrape-cands__item {
  display: flex;
  gap: 8px;
  text-align: left;
  border: 1px solid var(--sm-color-border);
  background: var(--sm-color-bg-surface);
  color: var(--sm-color-text);
  border-radius: var(--sm-radius-control);
  padding: 6px;
  cursor: pointer;
}

.scrape-cands__item--picked {
  outline: 2px solid var(--sm-color-primary);
  outline-offset: -2px;
}

.scrape-cands__thumb {
  width: 48px;
  height: 72px;
  object-fit: cover;
  background: var(--sm-color-bg-muted, #eee);
  flex-shrink: 0;
}

.scrape-cands__title {
  font-size: 13px;
}

.scrape-cands__src {
  font-size: 11px;
  color: var(--sm-color-text-muted);
}
</style>
