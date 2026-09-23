<template>
  <div class="scrape-fields">
    <label class="scrape-fields__row">
      <n-checkbox :checked="applyTitle" @update:checked="$emit('update:applyTitle', $event)">标题</n-checkbox>
      <span class="scrape-fields__cmp">
        <span class="scrape-fields__old">{{ current.title || '—' }}</span>
        <span class="scrape-fields__new">{{ preview.title || '—' }}</span>
      </span>
    </label>
    <label class="scrape-fields__row">
      <n-checkbox :checked="applySynopsis" @update:checked="$emit('update:applySynopsis', $event)">简介</n-checkbox>
      <span class="scrape-fields__cmp">
        <span class="scrape-fields__old">{{ current.synopsis || '—' }}</span>
        <span class="scrape-fields__new scrape-fields__new--wrap">{{ preview.synopsis || '—' }}</span>
      </span>
    </label>
    <label class="scrape-fields__row">
      <n-checkbox :checked="applyAuthor" @update:checked="$emit('update:applyAuthor', $event)">作者</n-checkbox>
      <span class="scrape-fields__cmp">
        <span class="scrape-fields__old">{{ current.author || '—' }}</span>
        <span class="scrape-fields__new">{{ preview.author || '—' }}</span>
      </span>
    </label>
    <label class="scrape-fields__row">
      <n-checkbox :checked="applyTags" @update:checked="$emit('update:applyTags', $event)">标签（只追加）</n-checkbox>
      <span class="scrape-fields__cmp">
        <span class="scrape-fields__old">{{ tagText(current.tags) }}</span>
        <span class="scrape-fields__new">{{ tagText(preview.tags) }}</span>
      </span>
    </label>
    <label class="scrape-fields__row">
      <n-checkbox :checked="applyCatalog" @update:checked="$emit('update:applyCatalog', $event)">作品档案</n-checkbox>
      <span class="scrape-fields__cmp">
        <span class="scrape-fields__old">{{ current.catalogSummary || '—' }}</span>
        <span class="scrape-fields__new">{{ preview.catalogSummary || '—' }}</span>
      </span>
    </label>
    <div class="scrape-fields__cover-block">
      <n-checkbox :checked="applyCover" @update:checked="$emit('update:applyCover', $event)">封面</n-checkbox>
      <div v-if="applyCover" class="scrape-fields__covers">
        <button
          v-for="url in preview.coverUrls"
          :key="url"
          type="button"
          class="scrape-fields__cover"
          :class="{ 'scrape-fields__cover--picked': pickedCover === url }"
          @click="$emit('update:pickedCover', url)"
        >
          <img :src="scrapeImageSrc(url)" alt="封面候选" referrerpolicy="no-referrer" />
        </button>
        <p v-if="preview.coverUrls.length === 0" class="scrape-fields__hint">此条无封面图</p>
      </div>
      <n-checkbox
        v-if="preview.userCoverLocked && applyCover"
        :checked="replaceUserCover"
        @update:checked="$emit('update:replaceUserCover', $event)"
      >
        覆盖我手动指定的封面
      </n-checkbox>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { NCheckbox } from 'naive-ui'
import { scrapeImageSrc } from '@/infrastructure/http/scrape'
import type { ScrapeCurrent, ScrapePreview } from '@/domain'

const props = defineProps<{
  preview: ScrapePreview
  pickedCover: string | null
  applyTitle: boolean
  applySynopsis: boolean
  applyAuthor: boolean
  applyTags: boolean
  applyCatalog: boolean
  applyCover: boolean
  replaceUserCover: boolean
}>()

defineEmits<{
  'update:pickedCover': [string | null]
  'update:applyTitle': [boolean]
  'update:applySynopsis': [boolean]
  'update:applyAuthor': [boolean]
  'update:applyTags': [boolean]
  'update:applyCatalog': [boolean]
  'update:applyCover': [boolean]
  'update:replaceUserCover': [boolean]
}>()

const current = computed((): ScrapeCurrent => ({
  title: props.preview.current?.title ?? '',
  synopsis: props.preview.current?.synopsis,
  author: props.preview.current?.author,
  tags: props.preview.current?.tags ?? [],
  catalogSummary: props.preview.current?.catalogSummary,
}))

function tagText(tags: string[] | undefined): string {
  if (!tags?.length) return '—'
  return tags.join('、')
}
</script>

<style scoped lang="less">
.scrape-fields {
  display: flex;
  flex-direction: column;
  gap: var(--sm-space-3);
  min-width: 0;
  min-height: 0;
  flex: 1;
  overflow: auto;
}

.scrape-fields__row {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
}

.scrape-fields__cmp {
  display: flex;
  flex-direction: column;
  gap: 2px;
  padding-left: 2px;
}

.scrape-fields__old {
  color: var(--sm-color-text-muted);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.scrape-fields__new {
  color: var(--sm-color-text);
  font-size: 13px;
}

.scrape-fields__new--wrap {
  max-height: 5.2em;
  overflow: auto;
  white-space: pre-wrap;
}

.scrape-fields__cover-block {
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 12px;
}

.scrape-fields__covers {
  display: flex;
  flex-wrap: nowrap;
  gap: 8px;
  overflow-x: auto;
}

.scrape-fields__cover {
  padding: 0;
  border: 1px solid var(--sm-color-border);
  background: transparent;
  cursor: pointer;
  border-radius: var(--sm-radius-control);
  flex-shrink: 0;
}

.scrape-fields__cover img {
  width: 72px;
  height: 108px;
  object-fit: cover;
  display: block;
  background: var(--sm-color-bg-muted, #eee);
}

.scrape-fields__cover--picked {
  outline: 2px solid var(--sm-color-primary);
  outline-offset: -2px;
}

.scrape-fields__hint {
  margin: 0;
  font-size: 12px;
  color: var(--sm-color-text-muted);
}
</style>
