<template>
  <div class="photo-timeline">
    <div v-if="!hideFilters" class="photo-timeline__filters">
      <n-select
        size="small"
        clearable
        placeholder="年份"
        :options="yearOptions"
        :value="year"
        class="photo-timeline__year"
        @update:value="(value: number | null) => (year = value ?? null)"
      />
      <n-select
        size="small"
        clearable
        placeholder="月份"
        :options="monthOptions"
        :value="month"
        class="photo-timeline__month-filter"
        @update:value="(value: number | null) => (month = value ?? null)"
      />
      <n-select
        size="small"
        multiple
        clearable
        filterable
        placeholder="标签（AND）"
        :options="tagOptions"
        :value="tagIds"
        class="photo-timeline__tags"
        @update:value="(value: number[]) => (tagIds = value ?? [])"
      />
      <n-checkbox
        size="small"
        :checked="includeAll"
        @update:checked="(checked: boolean) => (includeAll = checked)"
      >
        显示全部照片
      </n-checkbox>
      <n-checkbox
        size="small"
        :checked="includeUntimed"
        @update:checked="(checked: boolean) => (includeUntimed = checked)"
      >
        包含未知时间
      </n-checkbox>
      <n-button v-if="!embedded" size="small" :loading="backfilling" @click="runBackfill">
        回填拍摄时间
      </n-button>
    </div>

    <div v-if="timeline && months.length" class="photo-timeline__density">
      <button
        v-for="group in months"
        :key="group.key"
        type="button"
        class="photo-timeline__density-item"
        :style="{ flexGrow: Math.max(1, group.days.reduce((sum, day) => sum + day.count, 0)) }"
        @click="scrollToMonth(group.key)"
      >
        <span>{{ group.label }}</span>
      </button>
    </div>

    <div ref="scrollRef" class="photo-timeline__scroll">
      <div v-if="loading" class="photo-timeline__skeleton">
        <span v-for="index in 3" :key="index" class="photo-timeline__skeleton-row" />
      </div>
      <EmptyGuide
        v-else-if="!timeline || timeline.total === 0"
        hint="还没有可显示的照片。导入后可按拍摄时间在这里浏览。"
      />
      <template v-else>
        <section
          v-for="group in months"
          :key="group.key"
          :id="`timeline-month-${group.key}`"
          class="photo-timeline__month-section"
        >
          <h3 class="photo-timeline__month">{{ group.label }}</h3>
          <div
            v-for="day in group.days"
            :key="day.date"
            class="photo-timeline__day-section"
          >
            <div class="photo-timeline__day-head">
              <span class="photo-timeline__day-label">{{ dayLabel(day.date) }} · {{ day.count }} 张</span>
              <n-button v-if="!hideFilters" text size="tiny" @click="openDay(day.date)">查看当天</n-button>
            </div>
            <div class="photo-timeline__row-wrap">
              <PhotoRow
                :photos="day.photos"
                :layout="layoutForDay(day.date)"
                :selected-ids="selectedId !== null ? [selectedId] : []"
                @select="selectPhoto"
                @open="openPhoto"
              />
            </div>
          </div>
        </section>

        <section v-if="timeline.unknownCount > 0" class="photo-timeline__month-section">
          <h3 class="photo-timeline__month">未知时间</h3>
          <div class="photo-timeline__day-section">
            <div class="photo-timeline__day-head">
              <span class="photo-timeline__day-label">{{ timeline.unknownCount }} 张</span>
              <n-button v-if="!hideFilters" text size="tiny" @click="openDay(null)">查看全部</n-button>
            </div>
            <div class="photo-timeline__row-wrap">
              <PhotoRow
                :photos="timeline.unknownPhotos"
                :layout="unknownLayout"
                :selected-ids="selectedId !== null ? [selectedId] : []"
                @select="selectPhoto"
                @open="openPhoto"
              />
            </div>
          </div>
        </section>

        <p class="photo-timeline__total">共 {{ timeline.total }} 张</p>
      </template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { NButton, NCheckbox, NSelect } from 'naive-ui'
import { useElementSize } from '@vueuse/core'
import justifiedLayout from 'justified-layout'
import EmptyGuide from '@/components/EmptyGuide/index.vue'
import PhotoRow from './PhotoRow.vue'
import { notify } from '@/application/notify'
import { useSelectionStore } from '@/application/stores/selection'
import { useLibraryStore } from '@/application/stores/library'
import { openResource } from '@/infrastructure/consume/consumeResource'
import {
  backfillPhotos,
  getPhotoTimeline,
  getTags,
} from '@/infrastructure/http'
import type {
  CategoryRule,
  PhotoTimeline as PhotoTimelineData,
  PhotoTimelineDay,
  PhotoTile,
  ResourceType,
  SavedViewFilters,
  TimelineScope,
} from '@/domain'

const props = withDefaults(defineProps<{
  type?: ResourceType
  categoryIds?: number[]
  tagIds?: number[]
  scope?: TimelineScope
  rules?: SavedViewFilters
  hideFilters?: boolean
  embedded?: boolean
}>(), {
  type: 'image',
  categoryIds: () => [],
  tagIds: () => [],
  scope: undefined,
  rules: () => ({
    image: { include: [], exclude: [] },
    video: { include: [], exclude: [] },
    tagIds: [],
    includeUntimed: false,
  }),
  hideFilters: false,
  embedded: false,
})

const emit = defineEmits<{
  openDay: [payload: { date: string | null; includeAll: boolean; categoryIds: number[]; tagIds: number[] }]
}>()

const route = useRoute()
const selection = useSelectionStore()
const library = useLibraryStore()
const timeline = ref<PhotoTimelineData | null>(null)
const loading = ref(false)
const backfilling = ref(false)
const includeAll = ref(false)
const includeUntimed = ref(false)
const year = ref<number | null>(null)
const month = ref<number | null>(null)
const tagIds = ref<number[]>([...props.tagIds])

const tagOptions = ref<{ label: string; value: number }[]>([])
const scrollRef = ref<HTMLElement | null>(null)
const { width: scrollWidth } = useElementSize(scrollRef)
const layoutWidth = computed(() => Math.max(1, scrollWidth.value - 32))

const currentYear = new Date().getFullYear()
const yearOptions = Array.from({ length: 10 }, (_, index) => {
  const value = currentYear - index
  return { label: String(value), value }
})
const monthOptions = Array.from({ length: 12 }, (_, index) => {
  const value = index + 1
  return { label: `${value} 月`, value }
})

type LayoutResult = ReturnType<typeof justifiedLayout>

function layoutFor(photos: PhotoTile[]): LayoutResult {
  if (photos.length === 0) {
    return { containerHeight: 0, widowCount: 0, boxes: [] }
  }
  const ratios = photos.map((photo) =>
    photo.width && photo.height ? photo.width / photo.height : 4 / 3
  )
  return justifiedLayout(ratios, {
    containerWidth: layoutWidth.value,
    targetRowHeight: 220,
    boxSpacing: 6,
    containerPadding: 0,
  })
}

const dayLayouts = computed(() => {
  const map = new Map<string, LayoutResult>()
  for (const day of timeline.value?.days ?? []) {
    map.set(day.date, layoutFor(day.photos))
  }
  return map
})

function layoutForDay(date: string): LayoutResult {
  return dayLayouts.value.get(date) ?? { containerHeight: 0, widowCount: 0, boxes: [] }
}

const unknownLayout = computed(() => layoutFor(timeline.value?.unknownPhotos ?? []))

interface MonthGroup {
  key: string
  label: string
  days: PhotoTimelineDay[]
}

const months = computed<MonthGroup[]>(() => {
  const groups: MonthGroup[] = []
  for (const day of timeline.value?.days ?? []) {
    const key = day.date.slice(0, 7)
    let group = groups.find((item) => item.key === key)
    if (!group) {
      const [yearText, monthText] = key.split('-')
      group = { key, label: `${yearText} 年 ${Number(monthText)} 月`, days: [] }
      groups.push(group)
    }
    group.days.push(day)
  }
  return groups
})

const selectedId = computed(() => selection.selectedId)

function allTiles() {
  const pending = timeline.value
  if (!pending) return []
  return [
    ...pending.days.flatMap((day) => day.photos),
    ...pending.unknownPhotos,
  ]
}

const imageViewerIds = computed(() =>
  allTiles().filter((photo) => photo.kind !== 'video').map((photo) => photo.id)
)

const videoPlayerIds = computed(() =>
  allTiles().filter((photo) => photo.kind === 'video').map((photo) => photo.id)
)

function scrollToMonth(key: string): void {
  const el = document.getElementById(`timeline-month-${key}`)
  el?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

function dayLabel(date: string): string {
  const [yearText, monthText, dayText] = date.split('-').map(Number)
  if (!yearText || !monthText || !dayText) return date
  const weekday = ['周日', '周一', '周二', '周三', '周四', '周五', '周六'][
    new Date(yearText, monthText - 1, dayText).getDay()
  ]
  return `${monthText} 月 ${dayText} 日 · ${weekday}`
}

function selectPhoto(id: number): void {
  selection.select(id)
}

function openPhoto(id: number): void {
  const tile = allTiles().find((photo) => photo.id === id)
  if (!tile) return
  void openResource(
    { id: tile.id, type: tile.kind },
    {
      playlist:
        tile.kind === 'video' ? videoPlayerIds.value : imageViewerIds.value,
    },
  )
}

function readQuery(): void {
  const query = route.query
  includeAll.value = query.includeAll === '1'
  includeUntimed.value = query.includeUntimed === '1'
  year.value = query.year ? Number(query.year) : null
  month.value = query.month ? Number(query.month) : null
  tagIds.value = query.tagIds
    ? String(query.tagIds).split(',').flatMap((value) => {
        const id = Number(value)
        return Number.isFinite(id) ? [id] : []
      })
    : []
}

async function load(): Promise<void> {
  loading.value = true
  try {
    const scope = (props.scope ?? props.type) as TimelineScope
    const imageRule: CategoryRule = props.scope
      ? props.rules.image
      : { include: props.categoryIds, exclude: [] }
    const videoRule: CategoryRule = props.scope ? props.rules.video : { include: [], exclude: [] }
    timeline.value = await getPhotoTimeline({
      scope,
      includeAll: includeAll.value,
      year: year.value ?? undefined,
      month: month.value ?? undefined,
      imageRule,
      videoRule,
      tagIds: props.hideFilters
        ? props.rules.tagIds.length ? props.rules.tagIds : undefined
        : tagIds.value.length ? tagIds.value : undefined,
      dateFrom: props.hideFilters ? props.rules.dateFrom : null,
      dateTo: props.hideFilters ? props.rules.dateTo : null,
      includeUntimed: props.hideFilters ? props.rules.includeUntimed : includeUntimed.value,
    })
  } catch (error) {
    notify.fromError(error, { context: '获取照片时间线' })
  } finally {
    loading.value = false
  }
}

async function runBackfill(): Promise<void> {
  backfilling.value = true
  try {
    const result = await backfillPhotos()
    notify.toast.success(
      `已扫描 ${result.scanned} 张：补时间 ${result.takenAtUpdated}，补位置 ${result.gpsUpdated}`
    )
    await load()
  } catch (error) {
    notify.fromError(error, { context: '回填拍摄时间' })
  } finally {
    backfilling.value = false
  }
}

function openDay(date: string | null): void {
  emit('openDay', {
    date,
    includeAll: includeAll.value,
    categoryIds: props.categoryIds,
    tagIds: tagIds.value,
  })
}

watch(
  [
    includeAll,
    includeUntimed,
    year,
    month,
    tagIds,
    () => props.type,
    () => props.categoryIds,
    () => props.scope,
    () => props.rules,
    () => props.hideFilters,
  ],
  () => {
    void load()
  },
  { deep: true },
)

watch(
  () => props.tagIds,
  (value) => {
    tagIds.value = [...value]
  },
)

watch(
  () => props.type,
  () => {
    void getTags(props.type).then((tags) => {
      tagOptions.value = tags.flatMap((tag) =>
        tag.id === undefined ? [] : [{ label: tag.name, value: tag.id }]
      )
    })
  },
)

watch(
  () => library.tagsRevision,
  () => {
    void getTags(props.type).then((tags) => {
      tagOptions.value = tags.flatMap((tag) =>
        tag.id === undefined ? [] : [{ label: tag.name, value: tag.id }]
      )
    })
  },
)

watch(
  () =>
    props.scope === 'media'
      ? library.resourceRevision('image') + library.resourceRevision('video')
      : library.resourceRevision(props.type),
  async () => {
    const top = scrollRef.value?.scrollTop ?? 0
    await load()
    await nextTick()
    if (scrollRef.value) scrollRef.value.scrollTop = top
  }
)

watch(
  () => library.watchRevision,
  async () => {
    const type = library.watchType
    if (type !== 'image' && type !== 'video') return
    if (props.scope !== 'media' && type !== props.type) return
    const top = scrollRef.value?.scrollTop ?? 0
    await load()
    await nextTick()
    if (scrollRef.value) scrollRef.value.scrollTop = top
  }
)

onMounted(() => {
  readQuery()
  void load()
  void getTags(props.type).then((tags) => {
    tagOptions.value = tags.flatMap((tag) =>
      tag.id === undefined ? [] : [{ label: tag.name, value: tag.id }]
    )
  })
})
</script>

<style scoped lang="less">
.photo-timeline {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.photo-timeline__filters {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--sm-space-2);
  padding: var(--sm-space-2);
  flex-shrink: 0;
}

.photo-timeline__density {
  display: flex;
  gap: 3px;
  height: 24px;
  padding: 0 var(--sm-space-2) 4px;
  flex-shrink: 0;
}

.photo-timeline__density-item {
  min-width: 18px;
  border: 0;
  border-radius: 3px;
  background: var(--sm-color-bg-muted, #e5e7eb);
  color: var(--sm-color-text-muted);
  font-size: 10px;
  overflow: hidden;
  white-space: nowrap;
  cursor: pointer;

  &:hover {
    background: var(--sm-color-border);
    color: var(--sm-color-text);
  }
}

.photo-timeline__year,
.photo-timeline__month-filter {
  width: 100px;
}

.photo-timeline__category {
  width: 130px;
}

.photo-timeline__tags {
  min-width: 180px;
  flex: 1;
}

.photo-timeline__scroll {
  flex: 1;
  min-height: 0;
  overflow: auto;
}

.photo-timeline__month-section {
  position: relative;
}

.photo-timeline__month {
  position: sticky;
  top: 0;
  z-index: 2;
  margin: 0;
  padding: 10px 16px 6px;
  background: var(--sm-color-bg-page);
  font-size: 16px;
  font-weight: 600;
  backdrop-filter: blur(6px);
}

.photo-timeline__day-section {
  padding: 0 16px;
}

.photo-timeline__day-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--sm-space-2);
  padding: 10px 0 6px;
}

.photo-timeline__day-label {
  font-size: 12px;
  color: var(--sm-color-text-muted);
}

.photo-timeline__row-wrap {
  margin-bottom: 6px;
}

.photo-timeline__total {
  padding: 16px;
  text-align: center;
  font-size: 12px;
  color: var(--sm-color-text-muted);
}

.photo-timeline__skeleton {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.photo-timeline__skeleton-row {
  display: block;
  height: 180px;
  border-radius: 6px;
  background: var(--sm-color-bg-muted, #f1f1f1);
}
</style>
