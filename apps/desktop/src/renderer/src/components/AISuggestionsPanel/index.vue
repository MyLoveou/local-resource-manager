<template>
  <section class="ai-panel">
    <div class="ai-panel__row">
      <strong>AI 建议</strong>
      <n-tag size="small" :bordered="false">{{ ai.suggestions.length }} 张</n-tag>
      <n-button size="tiny" :loading="ai.suggestionsLoading" @click="ai.refreshSuggestions()">
        刷新
      </n-button>
    </div>
    <p class="ai-muted">
      审核后应用。标签只从你已有的词表里挑选——模型新造的泛词不会出现在这里；实体只会添加，不覆盖已有内容。
    </p>
    <div v-if="ai.suggestionsLoading" class="ai-empty">
      <n-spin size="small" /> 正在读取建议
    </div>
    <div v-else-if="!ai.suggestions.length" class="ai-empty">
      暂无建议。这里只显示「你词表里已有、但这张图还没加」的标签；先把常用标签用起来，或补充角色 / 扮演者 / 合集。
    </div>
    <div v-else class="ai-suggestion-list">
      <article
        v-for="item in ai.suggestions"
        :key="item.resourceId"
        class="ai-suggestion"
      >
        <button
          type="button"
          class="ai-suggestion__cover"
          :title="`打开 ${item.title || `资源 #${item.resourceId}`}`"
          @click="emit('open', item)"
        >
          <img
            v-if="item.thumbnailPath"
            :src="resolveCardImageUrl({ thumbnailPath: item.thumbnailPath })"
            :alt="item.title"
            loading="lazy"
          />
          <span v-else>无图</span>
        </button>
        <div class="ai-suggestion__main">
          <div class="ai-panel__row">
            <strong>{{ item.title || `资源 #${item.resourceId}` }}</strong>
            <n-tag size="tiny" :bordered="false">#{{ item.resourceId }}</n-tag>
          </div>
          <div v-if="item.tags.length" class="ai-suggestion__group">
            <span>标签（可多选）</span>
            <button
              v-for="tag in item.tags"
              :key="`tag-${item.resourceId}-${tag}`"
              type="button"
              class="ai-suggestion__tag"
              :class="{ active: isTagSelected(item, tag) }"
              :disabled="suggestionBusy === item.resourceId"
              @click="toggleTag(item, tag)"
            >
              {{ tag }}
            </button>
            <button type="button" class="ai-suggestion__select" @click="selectAllTags(item)">
              全选
            </button>
            <button
              v-if="selectedTagCount(item)"
              type="button"
              class="ai-suggestion__select"
              @click="clearSelectedTags(item)"
            >
              清空
            </button>
          </div>
          <div v-if="item.categories.length" class="ai-suggestion__group">
            <span>分类</span>
            <button
              v-for="entity in item.categories"
              :key="`category-${item.resourceId}-${entity.id}`"
              type="button"
              class="ai-suggestion__apply"
              :disabled="suggestionBusy === item.resourceId"
              :title="
                entity.confidence
                  ? `置信度 ${Math.round(entity.confidence * 100)}%（同标签资源的分类）`
                  : undefined
              "
              @click="applyEntity(item, 'categories', entity)"
            >
              + {{ entity.name }}
            </button>
          </div>
          <div v-if="item.characters.length" class="ai-suggestion__group">
            <span>角色</span>
            <button
              v-for="entity in item.characters"
              :key="`character-${item.resourceId}-${entity.id}`"
              type="button"
              class="ai-suggestion__apply"
              :disabled="suggestionBusy === item.resourceId"
              @click="applyEntity(item, 'characters', entity)"
            >
              + {{ entity.name }}
            </button>
          </div>
          <div v-if="item.persons.length" class="ai-suggestion__group">
            <span>扮演者</span>
            <button
              v-for="entity in item.persons"
              :key="`person-${item.resourceId}-${entity.id}`"
              type="button"
              class="ai-suggestion__apply"
              :disabled="suggestionBusy === item.resourceId"
              @click="applyEntity(item, 'persons', entity)"
            >
              + {{ entity.name }}
            </button>
          </div>
          <div v-if="item.collections.length" class="ai-suggestion__group">
            <span>合集</span>
            <button
              v-for="entity in item.collections"
              :key="`collection-${item.resourceId}-${entity.id}`"
              type="button"
              class="ai-suggestion__apply"
              :disabled="suggestionBusy === item.resourceId"
              @click="applyEntity(item, 'collections', entity)"
            >
              + {{ entity.name }}
            </button>
          </div>
        </div>
        <n-button
          v-if="item.tags.length"
          size="tiny"
          :loading="suggestionBusy === item.resourceId"
          :disabled="selectedTagCount(item) === 0"
          @click="applyTags(item)"
        >
          应用选中 {{ selectedTagCount(item) }}
        </n-button>
      </article>
    </div>
    <div v-if="ai.suggestionsHasMore" class="ai-panel__actions">
      <n-button
        size="small"
        :loading="ai.suggestionsLoadingMore"
        @click="ai.loadMoreSuggestions()"
      >
        加载更多建议
      </n-button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { NButton, NSpin, NTag } from 'naive-ui'
import { useAIStore } from '@/application/stores/ai'
import { notify } from '@/application/notify'
import { addCollectionItems } from '@/infrastructure/http/collections'
import { batchResources, resolveCardImageUrl } from '@/infrastructure/http'
import type { AIEntitySuggestion, AISuggestionItem } from '@/infrastructure/http'

const emit = defineEmits<{ open: [item: AISuggestionItem] }>()
const ai = useAIStore()
const suggestionBusy = ref(0)
const selectedSuggestionTags = ref<Record<number, string[]>>({})

function selectedTagsFor(item: AISuggestionItem): string[] {
  return selectedSuggestionTags.value[item.resourceId] ?? []
}

function selectedTagCount(item: AISuggestionItem): number {
  return selectedTagsFor(item).length
}

function isTagSelected(item: AISuggestionItem, tag: string): boolean {
  return selectedTagsFor(item).includes(tag)
}

function toggleTag(item: AISuggestionItem, tag: string): void {
  const current = selectedTagsFor(item)
  selectedSuggestionTags.value = {
    ...selectedSuggestionTags.value,
    [item.resourceId]: current.includes(tag)
      ? current.filter((value) => value !== tag)
      : [...current, tag],
  }
}

function selectAllTags(item: AISuggestionItem): void {
  selectedSuggestionTags.value = {
    ...selectedSuggestionTags.value,
    [item.resourceId]: [...item.tags],
  }
}

function clearSelectedTags(item: AISuggestionItem): void {
  selectedSuggestionTags.value = {
    ...selectedSuggestionTags.value,
    [item.resourceId]: [],
  }
}

async function applyTags(item: AISuggestionItem): Promise<void> {
  const tags = selectedTagsFor(item)
  if (!tags.length || item.resourceId == null) return
  suggestionBusy.value = item.resourceId
  try {
    const result = await batchResources('add_tags', [item.resourceId], tags)
    if (result.failed.length) {
      notify.toast.error(result.failed[0]?.message || '应用标签失败')
      return
    }
    clearSelectedTags(item)
    await ai.refreshSuggestions()
  } finally {
    suggestionBusy.value = 0
  }
}

async function applyEntity(
  item: AISuggestionItem,
  kind: 'categories' | 'characters' | 'persons' | 'collections',
  entity: AIEntitySuggestion,
): Promise<void> {
  if (item.resourceId == null) return
  suggestionBusy.value = item.resourceId
  try {
    if (kind === 'collections') {
      await addCollectionItems(entity.id, [item.resourceId])
    } else if (kind === 'categories') {
      const result = await batchResources('add_categories', [item.resourceId], undefined, [
        entity.id,
      ])
      if (result.failed.length) notify.toast.error(result.failed[0]?.message || '设置分类失败')
    } else if (kind === 'characters') {
      const result = await batchResources(
        'add_characters',
        [item.resourceId],
        undefined,
        undefined,
        [entity.id],
      )
      if (result.failed.length) notify.toast.error(result.failed[0]?.message || '添加角色失败')
    } else {
      const result = await batchResources(
        'add_persons',
        [item.resourceId],
        undefined,
        undefined,
        undefined,
        [entity.id],
      )
      if (result.failed.length) notify.toast.error(result.failed[0]?.message || '添加扮演者失败')
    }
    await ai.refreshSuggestions()
  } catch (error) {
    notify.fromError(error, { context: '应用 AI 建议失败' })
  } finally {
    suggestionBusy.value = 0
  }
}
</script>

<style scoped lang="less">
.ai-panel {
  margin-top: 14px;
  padding: 18px;
  border: 1px solid var(--sm-color-border);
  border-radius: 12px;
  background: var(--sm-color-bg-surface);
}

.ai-panel__row {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;

  > strong {
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.ai-panel__actions {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 16px;
}

.ai-muted {
  color: var(--sm-color-text-muted);
  font-size: 12px;
}

.ai-empty {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 14px;
  color: var(--sm-color-text-muted);
  font-size: 13px;
}

.ai-suggestion-list {
  margin-top: 8px;
}

.ai-suggestion {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid var(--sm-color-border);
}

.ai-suggestion__cover {
  display: flex;
  flex: 0 0 96px;
  align-items: center;
  justify-content: center;
  width: 96px;
  height: 72px;
  overflow: hidden;
  padding: 0;
  border: 1px solid var(--sm-color-border);
  border-radius: 6px;
  background: var(--sm-color-bg-surface);
  color: var(--sm-color-text-muted);
  font-size: 11px;
  cursor: pointer;

  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
}

.ai-suggestion__tag {
  padding: 1px 6px;
  border: 1px solid var(--sm-color-border);
  border-radius: 999px;
  background: transparent;
  color: var(--sm-color-text-muted);
  font-size: 11px;
  cursor: pointer;
}

.ai-suggestion__tag.active {
  border-color: var(--sm-color-accent);
  background: color-mix(in srgb, var(--sm-color-accent) 12%, transparent);
  color: var(--sm-color-text);
}

.ai-suggestion__select {
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--sm-color-accent);
  font-size: 11px;
  cursor: pointer;
}

.ai-suggestion:last-child {
  border-bottom: 0;
}

.ai-suggestion__main {
  flex: 1;
  min-width: 0;
}

.ai-suggestion__group {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 6px;

  > span {
    color: var(--sm-color-text-muted);
    font-size: 11px;
  }
}

.ai-suggestion__apply {
  padding: 1px 6px;
  border: 1px solid var(--sm-color-border);
  border-radius: 4px;
  background: transparent;
  color: var(--sm-color-text);
  font-size: 11px;
  cursor: pointer;
}

.ai-suggestion__apply:hover {
  border-color: var(--sm-color-accent);
}
</style>
