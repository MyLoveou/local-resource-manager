<template>
  <section v-if="insight" class="ai-insight">
    <div class="ai-insight__row">
      <strong>AI 检索解读</strong>
      <n-tag size="small" :bordered="false">{{ sourceLabel }}</n-tag>
      <button type="button" class="ai-insight__toggle" @click="expanded = !expanded">
        {{ expanded ? '收起' : '展开' }}
      </button>
    </div>
    <p class="ai-insight__strategy">{{ insight.strategy }}</p>
    <p v-if="!expanded" class="ai-insight__summary">
      {{ insight.source === 'text' ? insight.raw : (insight.caption || '暂无 VLM 文案') }}
    </p>

    <template v-if="expanded">
      <div class="ai-insight__grid">
        <div v-if="insight.source === 'text'" class="ai-insight__item">
          <span>原始查询</span>
          <p>{{ insight.raw || '无' }}</p>
        </div>
        <div v-if="insight.source === 'text'" class="ai-insight__item">
          <span>语义检索文本</span>
          <p>{{ insight.semanticText || insight.raw || '无' }}</p>
        </div>

        <template v-if="insight.source !== 'text'">
          <div class="ai-insight__item">
            <span>图片识别</span>
            <p>{{ insight.caption || '暂无 VLM 文案' }}</p>
          </div>
          <div class="ai-insight__item">
            <span>人数（YOLO）/ 方向</span>
            <p>{{ peopleText }}</p>
          </div>
        </template>

        <div class="ai-insight__item">
          <span>硬条件</span>
          <p>{{ insight.filters.length ? insight.filters.join(' · ') : '无' }}</p>
        </div>
      </div>

      <div v-if="insight.labels.length" class="ai-insight__chips">
        <span>{{ insight.source === 'image' ? 'CLIP 标签' : '识别标签' }}</span>
        <n-tag v-for="label in insight.labels" :key="label" size="small" :bordered="false">
          {{ label }}
        </n-tag>
      </div>
      <div v-if="insight.tags.length" class="ai-insight__chips">
        <span>{{ insight.source === 'image' ? '图片标签' : '查询标签' }}</span>
        <n-tag v-for="tag in insight.tags" :key="tag" size="small" :bordered="false">
          {{ tag }}
        </n-tag>
      </div>

      <p
        v-if="insight.source === 'text' && !insight.filters.length && !insight.labels.length"
        class="ai-insight__note"
      >
        未识别到人数、方向或固定标签条件，当前仅使用原始查询的 CLIP 语义向量。
      </p>
      <p v-for="note in insight.notes" :key="note" class="ai-insight__note">{{ note }}</p>
      <p class="ai-insight__foot">这里展示的是检索依据，不是模型内部思维链。</p>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { NTag } from 'naive-ui'
import type { AIQueryInsight } from '@/infrastructure/http'

const props = defineProps<{
  insight: AIQueryInsight | null
}>()

const expanded = ref(false)

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

.ai-insight__toggle {
  margin-left: auto;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--sm-color-accent);
  font-size: 11px;
  cursor: pointer;
}

.ai-insight__summary {
  margin: 6px 0 0;
  color: var(--sm-color-text);
  font-size: 12px;
  line-height: 1.6;
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
