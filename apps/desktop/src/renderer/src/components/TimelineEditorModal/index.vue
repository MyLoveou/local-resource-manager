<template>
  <n-modal
    :show="show"
    preset="card"
    :title="dialogTitle"
    style="width: 620px"
    :mask-closable="!busy"
    @update:show="(value: boolean) => $emit('update:show', value)"
  >
    <div class="timeline-editor">
      <n-input v-model:value="name" :placeholder="namePlaceholder" />
      <n-radio-group v-model:value="scope">
        <n-space>
          <n-radio value="image">图片</n-radio>
          <n-radio value="video">视频</n-radio>
          <n-radio value="media">全部媒体</n-radio>
        </n-space>
      </n-radio-group>
      <n-date-picker v-model:value="dateRange" type="daterange" clearable />
      <section v-if="scope === 'image' || scope === 'media'" class="timeline-editor__section">
        <h4>图片分类</h4>
        <n-select
          v-model:value="imageInclude"
          multiple
          filterable
          clearable
          placeholder="包含分类（空 = 全部）"
          :options="imageOptions"
        />
        <n-select
          v-model:value="imageExclude"
          multiple
          filterable
          clearable
          placeholder="排除分类"
          :options="imageOptions"
        />
      </section>
      <section v-if="scope === 'video' || scope === 'media'" class="timeline-editor__section">
        <h4>视频分类</h4>
        <n-select
          v-model:value="videoInclude"
          multiple
          filterable
          clearable
          placeholder="包含分类（空 = 全部）"
          :options="videoOptions"
        />
        <n-select
          v-model:value="videoExclude"
          multiple
          filterable
          clearable
          placeholder="排除分类"
          :options="videoOptions"
        />
      </section>
      <n-select
        v-model:value="tagIds"
        multiple
        filterable
        clearable
        placeholder="标签（AND）"
        :options="tagOptions"
      />
      <n-select
        v-model:value="characterIds"
        multiple
        filterable
        clearable
        placeholder="角色（AND）"
        :options="characterOptions"
      />
      <n-select
        v-model:value="personIds"
        multiple
        filterable
        clearable
        placeholder="扮演者（AND）"
        :options="personOptions"
      />
      <n-checkbox v-model:checked="includeUntimed">包含未知时间</n-checkbox>
      <div class="timeline-editor__actions">
        <n-button @click="$emit('update:show', false)">取消</n-button>
        <n-button type="primary" :loading="busy" :disabled="!name.trim()" @click="save">
          保存
        </n-button>
      </div>
    </div>
  </n-modal>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import {
  NButton,
  NCheckbox,
  NDatePicker,
  NInput,
  NModal,
  NRadio,
  NRadioGroup,
  NSelect,
  NSpace,
} from 'naive-ui'
import { notify } from '@/application/notify'
import { createSavedView, getCategoryTree, getTags, listCharacters, listPersons, patchSavedView } from '@/infrastructure/http'
import { useLibraryStore } from '@/application/stores/library'
import type {
  CategoryNode,
  SavedView,
  SavedViewFilters,
  TimelineScope,
} from '@/domain'

const props = defineProps<{
  show: boolean
  view?: SavedView | null
  initialScope?: TimelineScope
  kind?: 'timeline' | 'map'
}>()
const library = useLibraryStore()
const kind = computed(() => props.kind ?? 'timeline')
const kindLabel = computed(() => kind.value === 'map' ? '地图' : '时间线')
const namePlaceholder = computed(() =>
  kind.value === 'map' ? '地图规则名称，例如 2026 旅行' : '时间线名称，例如 2026 漫展'
)
const dialogTitle = computed(() => {
  return props.view ? `编辑${kindLabel.value}` : `新建${kindLabel.value}`
})
const emit = defineEmits<{
  'update:show': [value: boolean]
  saved: [view: SavedView]
}>()

const name = ref('')
const scope = ref<TimelineScope>('image')
const imageInclude = ref<number[]>([])
const imageExclude = ref<number[]>([])
const videoInclude = ref<number[]>([])
const videoExclude = ref<number[]>([])
const tagIds = ref<number[]>([])
const characterIds = ref<number[]>([])
const personIds = ref<number[]>([])
const dateRange = ref<[number, number] | null>(null)
const includeUntimed = ref(false)
const busy = ref(false)
const imageTree = ref<CategoryNode[]>([])
const videoTree = ref<CategoryNode[]>([])
const tagOptions = ref<{ label: string; value: number }[]>([])
const characterOptions = ref<{ label: string; value: number }[]>([])
const personOptions = ref<{ label: string; value: number }[]>([])

const imageOptions = computed(() => flatten(imageTree.value))
const videoOptions = computed(() => flatten(videoTree.value))

function flatten(nodes: CategoryNode[], prefix = ''): { label: string; value: number }[] {
  const out: { label: string; value: number }[] = []
  for (const node of nodes) {
    const path = prefix ? `${prefix} / ${node.name}` : node.name
    out.push({ label: path, value: node.id })
    out.push(...flatten(node.children ?? [], path))
  }
  return out
}

function isoToTs(value?: string | null): number | null {
  if (!value) return null
  const time = new Date(`${value}T00:00:00`).getTime()
  return Number.isFinite(time) ? time : null
}

function tsToIso(value: number | null): string | null {
  if (value === null) return null
  const date = new Date(value)
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
}

function resetForm(): void {
  const view = props.view
  name.value = view?.name ?? ''
  scope.value = view?.scope ?? props.initialScope ?? 'image'
  imageInclude.value = [...(view?.filters.image.include ?? [])]
  imageExclude.value = [...(view?.filters.image.exclude ?? [])]
  videoInclude.value = [...(view?.filters.video.include ?? [])]
  videoExclude.value = [...(view?.filters.video.exclude ?? [])]
  tagIds.value = [...(view?.filters.tagIds ?? [])]
  characterIds.value = [...(view?.filters.characterIds ?? [])]
  personIds.value = [...(view?.filters.personIds ?? [])]
  const from = isoToTs(view?.filters.dateFrom)
  const to = isoToTs(view?.filters.dateTo)
  dateRange.value = from !== null && to !== null ? [from, to] : null
  includeUntimed.value = view?.filters.includeUntimed ?? false
}

async function loadOptions(): Promise<void> {
  const [images, videos, tags, characters, persons] = await Promise.all([
    getCategoryTree('image'),
    getCategoryTree('video'),
    getTags(),
    listCharacters(),
    listPersons(),
  ])
  imageTree.value = images
  videoTree.value = videos
  tagOptions.value = tags.flatMap((tag) =>
    tag.id === undefined ? [] : [{ label: tag.name, value: tag.id }]
  )
  characterOptions.value = characters.map((character) => ({
    label: character.workName ? `${character.name} ? ${character.workName}` : character.name,
    value: character.id,
  }))
  personOptions.value = persons.map((person) => ({ label: person.name, value: person.id }))
}

async function save(): Promise<void> {
  const title = name.value.trim()
  if (!title) return
  const filters: SavedViewFilters = {
    image: { include: imageInclude.value, exclude: imageExclude.value },
    video: { include: videoInclude.value, exclude: videoExclude.value },
    tagIds: tagIds.value,
    characterIds: characterIds.value,
    personIds: personIds.value,
    dateFrom: dateRange.value ? tsToIso(dateRange.value[0]) : null,
    dateTo: dateRange.value ? tsToIso(dateRange.value[1]) : null,
    includeUntimed: includeUntimed.value,
  }
  busy.value = true
  try {
    const saved = props.view
      ? await patchSavedView(props.view.id, { scope: scope.value, name: title, filters })
      : await createSavedView({ kind: kind.value, scope: scope.value, name: title, filters })
    library.invalidate({ savedViews: true, home: true })
    emit('saved', saved)
    emit('update:show', false)
    notify.toast.success(props.view ? `${kindLabel.value}已保存` : `${kindLabel.value}已创建`)
  } catch (error) {
    notify.fromError(error, { context: `保存${kindLabel.value}` })
  } finally {
    busy.value = false
  }
}

watch(
  () => props.show,
  (show) => {
    if (!show) return
    resetForm()
    void loadOptions()
  },
  { immediate: true },
)
</script>

<style scoped lang="less">
.timeline-editor {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.timeline-editor__section {
  display: flex;
  flex-direction: column;
  gap: 6px;

  h4 {
    margin: 0;
    font-size: 13px;
  }
}

.timeline-editor__actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
