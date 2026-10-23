<template>
  <section v-if="insight" class="ai-insight">
    <div class="ai-insight__row">
      <strong>AI 检索解读</strong>
      <n-tag size="small" :bordered="false">{{ sourceLabel }}</n-tag>
    </div>
    <p class="ai-insight__strategy">{{ insight.strategy }}</p>

    <div class="ai-insight__grid">
      <div v-if="insight.source === 'text'" class="ai-insight__item">
        <span>原始查询</span>
        <p>{{ insight.raw || '—' }}</p>
      </div>
      <div
        v-if="insight.source === 'text' && insight.semanticText && insight.semanticText !== insight.raw"
        class="ai-insight__item"
      >
        <span>交给 CLIP 的语义</span>
        <p>{{ insight.semanticText }}</p>
      </div>
      <template v-else-if="insight.source !== 'text'">
        <div class="ai-insight__item">
          <span>图片识别</span>
          <p>{{ insight.caption || '尚未生成 VLM 文案' }}</p>
        </div>
        <div class="ai-insight__item">
          <span>人数（YOLO） / 方向</span>
          <p>{{ peopleText }}</p>
        </div>
      </template>
      <div class="ai-insight__item">
        <span>硬条件</span>
        <p>{{ insight.filters.join('、') || '无' }}</p>
      </div>
    </div>

    <div v-if="insight.labels.length" class="ai-insight__chips">
      <span>{{ insight.source === 'image' ? 'CLIP 标签' : '标签条件' }}</span>
      <n-tag v-for="label in insight.labels" :key="label" size="small" :bordered="false">
        {{ label }}
      </n-tag>
    </div>
    <div v-if="insight.tags.length" class="ai-insight__chips">
      <span>图片标签</span>
      <n-tag v-for="tag in insight.tags" :key="tag" size="small" :bordered="false">
        {{ tag }}
      </n-tag>
    </div>

    <p v-for="note in insight.notes" :key="note" class="ai-insight__note">{{ note }}</p>
    <p class="ai-insight__foot">这里展示的是检索依据，不是模型内部思维链。</p>
  </section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { NTag } from 'naive-ui'
import type { AIQueryInsight } from '@/infrastructure/http'

const props = defineProps<{
  insight: AIQueryInsight | null
}>()

const sourceLabel = computed(() =>
  props.insight?.source === 'image' ? '图片查询' : '文字查询',
)

const peopleText = computed(() => {
  const count = props.insight?.personCount
  const orientation = props.insight?.orientation || '未知'
  return `${count ?? '未知'} 人 · ${orientation}`
})
</script>

<style scoped lang="less">
.ai-insight {
  margin-top: 14px;
  padding: 14px;
  border: 1px solid var(--sm-color-border);
  border-radius: 12px;
  background: var(--sm-color-bg-surface);
}

.ai-insight__row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.ai-insight__strategy {
  margin: 8px 0 0;
  color: var(--sm-color-text-muted);
  font-size: 12px;
  line-height: 1.7;
}

.ai-insight__grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 12px;
  margin-top: 12px;
}

.ai-insight__item {
  min-width: 0;

  span {
    display: block;
    color: var(--sm-color-text-muted);
    font-size: 11px;
  }

  p {
    margin: 4px 0 0;
    font-size: 12px;
    line-height: 1.6;
  }
}

.ai-insight__chips {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 10px;

  > span {
    color: var(--sm-color-text-muted);
    font-size: 11px;
  }
}

.ai-insight__note,
.ai-insight__foot {
  margin: 8px 0 0;
  color: var(--sm-color-text-muted);
  font-size: 11px;
  line-height: 1.6;
}

.ai-insight__foot {
  padding-top: 8px;
  border-top: 1px solid var(--sm-color-border);
}
</style>
