<template>
  <aside class="info-panel">
    <div v-if="resource" class="info-panel-content">
      <div class="info-panel-body">
        <img v-if="coverUrl" class="info-panel-cover" :class="{ 'info-panel-cover--open': isImage }" :src="coverUrl"
          alt="封面" decoding="async" @click="openViewerFromCover" />
        <div class="info-panel-title" :title="resource.title">{{ resource.title }}</div>
        <div class="info-panel-meta">类型 {{ typeLabel }}</div>
        <template v-if="isSeries">
          <div
            v-for="season in resource.seasons ?? []"
            :key="season.id ?? season.seasonNumber"
            class="info-panel-season"
          >
            <div class="info-panel-label">第 {{ season.seasonNumber }} 季</div>
            <button
              v-for="ep in season.episodes ?? []"
              :key="ep.fileId"
              type="button"
              class="info-panel-episode"
              @click="playEpisode(ep.fileId)"
            >
              {{ episodeButtonLabel(ep) }}
            </button>
          </div>
          <div v-if="(resource.extras ?? []).length" class="info-panel-label">特典</div>
          <button
            v-for="extra in resource.extras ?? []"
            :key="extra.fileId"
            type="button"
            class="info-panel-episode"
            @click="playEpisode(extra.fileId)"
          >
            {{ extra.title || '特典' }}
          </button>
        </template>
        <template v-else>
          <div class="info-panel-meta">格式 {{ formatLabel }}</div>
          <div class="info-panel-meta">大小 {{ sizeLabel }}</div>
        </template>
        <div class="info-panel-meta">创建 {{ resource.createdAt || '—' }}</div>
        <div v-if="resource.status === 'trashed'" class="info-panel-meta">
          删除 {{ resource.deletedAt || '—' }}
        </div>
        <template v-if="isImage">
          <div class="info-panel-meta">分辨率 {{ resolutionLabel }}</div>
        </template>
        <template v-else-if="!isSeries">
          <div class="info-panel-meta">分辨率 {{ resolutionLabel }}</div>
          <div class="info-panel-meta">清晰度 {{ clarityText }}</div>
          <div class="info-panel-meta">时长 {{ durationLabel }}</div>
          <div class="info-panel-meta">帧率 {{ fpsLabel }}</div>
          <div class="info-panel-meta">码率 {{ bitrateLabel }}</div>
          <div class="info-panel-meta">画质 {{ qualityText }}</div>
          <div v-if="subtitleNames.length" class="info-panel-meta">
            字幕 {{ subtitleNames.join('、') }}
          </div>
        </template>
        <div class="info-panel-label">描述</div>
        <n-input type="textarea" :autosize="{ minRows: 2, maxRows: 5 }" :value="draft.description" placeholder="记录说明"
          @update:value="draft.description = $event" />
        <div class="info-panel-label">作者</div>
        <n-input :value="draft.author" placeholder="可选" @update:value="draft.author = $event" />
        <div class="info-panel-label">待办</div>
        <div class="info-panel-todos">
          <div v-for="todo in resource.todos ?? []" :key="todo.id ?? todo.content" class="info-panel-todo">
            <n-checkbox :checked="todo.done" :disabled="todo.id == null || todoBusy"
              @update:checked="toggleTodo(todo, $event)" />
            <n-input size="tiny" :value="todo.content" :disabled="todo.id == null || todoBusy"
              @keydown.enter.prevent="(e: KeyboardEvent) => onTodoRenameEnter(e, todo)"
              @blur="(e: FocusEvent) => renameTodoFromEvent(todo, e)" />
            <n-button size="tiny" quaternary :disabled="todo.id == null || todoBusy" @click="removeTodoRow(todo)">
              删
            </n-button>
          </div>
          <div class="info-panel-todo-add">
            <n-input :value="todoInput" size="small" placeholder="回车添加" @update:value="todoInput = $event"
              @keydown.enter.prevent="onTodoAddEnter" />
          </div>
        </div>
        <!-- 分类是独立词表，不是 type -->
        <div class="info-panel-label">评分</div>
        <n-rate allow-half :count="5" :value="draft.ratingStars" @update:value="draft.ratingStars = $event" />
        <div class="info-panel-label">分类</div>
        <n-select filterable tag clearable :options="categoryOptions" :value="draft.categoryName"
          @update:value="draft.categoryName = $event" />
        <div class="info-panel-label">标签（Enter 切词）</div>
        <div class="info-panel-tags">
          <n-tag v-for="name in draft.tagNames" :key="name" closable @close="removeTag(name)">
            {{ name }}
          </n-tag>
          <n-input :value="draft.tagInput" placeholder="回车添加" size="small" style="width: 120px"
            @update:value="draft.tagInput = $event" @keydown.enter.prevent="commitTagInput" />
        </div>
      </div>
      <div class="info-panel-footer">
        <div class="info-panel-actions">
          <n-button size="small" :loading="saving" :disabled="!dirty" @click="savePanel">保存</n-button>
          <n-button size="small" @click="openModal">编辑</n-button>
          <n-dropdown v-if="moreOptions.length > 0" trigger="click" :options="moreOptions" @select="onMoreSelect">
            <n-button size="small">更多</n-button>
          </n-dropdown>
          <n-popconfirm v-if="resource.status !== 'trashed'" positive-text="移入" negative-text="取消"
            @positive-click="handleDelete">
            <template #trigger>
              <n-button size="small" type="error" :disabled="deleting" ghost>移入回收站</n-button>
            </template>
            确定将此资源移入回收站？可稍后恢复。
          </n-popconfirm>
          <n-popconfirm v-else positive-text="恢复" negative-text="取消" @positive-click="handleRestore">
            <template #trigger>
              <n-button size="small" :disabled="deleting">恢复</n-button>
            </template>
            确定恢复此资源？
          </n-popconfirm>
          <n-popconfirm v-if="resource.status === 'trashed'" positive-text="彻底删除" negative-text="取消"
            @positive-click="handlePurge">
            <template #trigger>
              <n-button size="small" type="error" :disabled="deleting" ghost>彻底删除</n-button>
            </template>
            彻底删除后不可恢复。只删除库内副本，不删除你电脑上的原文件。
          </n-popconfirm>
        </div>
        <p v-if="errorMessage" class="info-panel-error">{{ errorMessage }}</p>
      </div>
      <EditResourceModal :show="editOpen" :draft="draft" :category-options="categoryOptions" :cover-url="modalCoverUrl"
        :saving="saving" :allow-cover="canChangeCover" @update:show="onModalShow" @save="saveModal"
        @cancel="cancelModal" @pick-cover="pickCoverForModal" />
    </div>
    <div v-else class="info-panel-empty">未选择资源</div>
  </aside>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { NButton, NCheckbox, NDropdown, NInput, NPopconfirm, NRate, NSelect, NTag } from 'naive-ui'
import type { DropdownOption } from 'naive-ui'
import EditResourceModal from '@/components/EditResourceModal/index.vue'
import { getResource, getCategories, invalidateCategories, invalidateResourceCache, resolveCardImageUrl } from '@/infrastructure/http'
import { useSelectionStore } from '@/application/stores/selection'
import { useLibraryStore } from '@/application/stores/library'
import { useImageViewerStore } from '@/application/stores/imageViewer'
import { useVideoPlayerStore } from '@/application/stores/videoPlayer'
import {
  openPrimaryDefault,
  openPrimaryWithOther,
  revealPrimary,
} from '@/infrastructure/shell/openLibraryFile'
import { useResourceHandle } from '@/hooks/useResourceHandle'
import { storeToRefs } from 'pinia'
import type { Category, MetadataDraft, Resource, ResourceFile, ResourceTodo, SeriesEpisode } from '@/domain'
import {
  COVER_FILE_FILTER,
  FILE_ROLE,
  RESOURCE_TYPE_LABEL,
  SUBTITLE_FILE_FILTER,
  clarityLabel,
  formatBitrate,
  formatDuration,
  formatFps,
  formatResolution,
  isSeriesResourceType,
  qualityLabel,
} from '@/domain'

const selection = useSelectionStore()
const library = useLibraryStore()
const imageViewer = useImageViewerStore()
const videoPlayer = useVideoPlayerStore()
const shellBusy = ref(false)
const { selectedId } = storeToRefs(selection)
const { deleteResource, restoreResource, purgeResource, patchResource, replaceCover, addSubtitle, addTodo, patchTodo, removeTodo } =
  useResourceHandle()

const resource = ref<Resource | null>(null)
const categories = ref<Category[]>([])
const deleting = ref(false)
const saving = ref(false)
const errorMessage = ref('')
const editOpen = ref(false)
const modalTextSnapshot = ref<{ title: string; description: string } | null>(null)
let loadGen = 0

const todoInput = ref('')
const todoBusy = ref(false)
const subtitleBusy = ref(false)

const draft = reactive<MetadataDraft>({
  title: '',
  description: '',
  author: '',
  ratingStars: 0,
  categoryName: null,
  tagNames: [],
  tagInput: '',
  pendingCoverPath: null,
})

function applyResourceToDraft(row: Resource): void {
  draft.title = row.title
  draft.description = row.description ?? ''
  draft.author = row.author ?? ''
  draft.ratingStars = (row.rating ?? 0) / 2
  draft.categoryName = row.category?.name ?? null
  draft.tagNames = (row.tags ?? []).map((t) => t.name)
  draft.tagInput = ''
  draft.pendingCoverPath = null
}

function snapshotEqualsSaved(): boolean {
  const row = resource.value
  if (!row) return true
  const savedTags = (row.tags ?? []).map((t) => t.name).join('\0')
  const draftTags = [...draft.tagNames].join('\0')
  return (
    draft.ratingStars === (row.rating ?? 0) / 2 &&
    (draft.description ?? '') === (row.description ?? '') &&
    (draft.author ?? '') === (row.author ?? '') &&
    (draft.categoryName ?? '') === (row.category?.name ?? '') &&
    savedTags === draftTags &&
    draft.tagInput.trim() === ''
  )
}

const dirty = computed(() => !snapshotEqualsSaved())

const typeLabel = computed(() =>
  resource.value ? RESOURCE_TYPE_LABEL[resource.value.type] : '—'
)
const isVideo = computed(() => resource.value?.type === 'video')
const isImage = computed(() => resource.value?.type === 'image')
const isSeries = computed(() =>
  resource.value != null && isSeriesResourceType(resource.value.type)
)

/** 图片主文件即封面，不提供更换封面；仅视频可换海报。 */
const canChangeCover = computed(() => isVideo.value)

const moreOptions = computed((): DropdownOption[] => {
  const items: DropdownOption[] = []
  if (canChangeCover.value) items.push({ label: '更换封面', key: 'cover' })
  if (isVideo.value) items.push({ label: '添加字幕', key: 'subtitle', disabled: subtitleBusy.value })
  if (isImage.value) {
    items.push(
      { label: '打开所在位置', key: 'reveal', disabled: shellBusy.value },
      { label: '用外部应用打开', key: 'openDefault', disabled: shellBusy.value },
      { label: '选择其他应用', key: 'openWith', disabled: shellBusy.value }
    )
  }
  return items
})

function primaryFile(): ResourceFile | undefined {
  const files = resource.value?.files ?? []
  return files.find((f) => f.role === FILE_ROLE.PRIMARY) ?? files[0]
}

const sizeLabel = computed(() => formatBytes(primaryFile()?.size))
const formatLabel = computed(() => primaryFile()?.format || '—')
const resolutionLabel = computed(() => formatResolution(primaryFile()?.width, primaryFile()?.height))
const durationLabel = computed(() => formatDuration(primaryFile()?.duration))
const fpsLabel = computed(() => formatFps(primaryFile()?.fps))
const bitrateLabel = computed(() => formatBitrate(primaryFile()?.bitrate))
const clarityText = computed(() => clarityLabel(primaryFile()?.width, primaryFile()?.height))
const qualityText = computed(() =>
  qualityLabel(
    primaryFile()?.width,
    primaryFile()?.height,
    primaryFile()?.fps,
    primaryFile()?.bitrate,
    primaryFile()?.codec
  )
)
const subtitleNames = computed(() =>
  (resource.value?.files ?? [])
    .filter((f) => f.role === FILE_ROLE.SUBTITLE)
    .map((f) => f.path.replace(/\\/g, '/').split('/').pop() || f.path)
)

const coverUrl = computed(() => resolveCardImageUrl(resource.value ?? {}))

const modalCoverUrl = computed(() => coverUrl.value)

const categoryOptions = computed(() => {
  const names = new Set(categories.value.map((c) => c.name))
  if (draft.categoryName) names.add(draft.categoryName)
  return [...names].sort().map((name) => ({ label: name, value: name }))
})

watch(
  selectedId,
  async (id) => {
    const gen = ++loadGen
    errorMessage.value = ''
    editOpen.value = false
    todoInput.value = ''
    if (id === null) {
      resource.value = null
      return
    }
    try {
      const row = await getResource(id)
      if (gen !== loadGen) return
      resource.value = row
      applyResourceToDraft(row)
      void getCategories().then((cats) => {
        if (gen !== loadGen) return
        categories.value = cats
      })
    } catch (error) {
      if (gen !== loadGen) return
      resource.value = null
      errorMessage.value = '加载详情失败'
      console.error(error)
    }
  },
  { immediate: true }
)

watch(
  () => library.revision,
  async () => {
    const id = selectedId.value
    if (id === null || editOpen.value) return
    invalidateResourceCache(id)
    const gen = ++loadGen
    try {
      const row = await getResource(id)
      if (gen !== loadGen) return
      resource.value = row
      applyResourceToDraft(row)
    } catch (error) {
      if (gen !== loadGen) return
      console.error(error)
    }
  }
)

function formatBytes(n: number | null | undefined): string {
  if (n == null || n <= 0) return '—'
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / (1024 * 1024)).toFixed(1)} MB`
}

function commitTagInput(): void {
  const text = draft.tagInput.trim()
  if (!text) return
  if (!draft.tagNames.includes(text)) {
    draft.tagNames.push(text)
  }
  draft.tagInput = ''
}

function removeTag(name: string): void {
  draft.tagNames = draft.tagNames.filter((item) => item !== name)
}

function flushTagInput(): void {
  if (draft.tagInput.trim()) commitTagInput()
}

async function persist(includeTextFields: boolean): Promise<boolean> {
  const id = selectedId.value
  const row = resource.value
  if (id === null || row === null) return false
  flushTagInput()
  saving.value = true
  errorMessage.value = ''
  try {
    const patched = await patchResource(id, {
      ...(includeTextFields ? { title: draft.title } : {}),
      description: draft.description || null,
      author: draft.author || null,
      rating: draft.ratingStars * 2,
      categoryName: draft.categoryName,
      tagNames: [...draft.tagNames],
    })
    resource.value = patched
    invalidateCategories()
    const pending = draft.pendingCoverPath
    applyResourceToDraft(patched)
    draft.pendingCoverPath = pending
    if (includeTextFields || patched.coverPath !== row.coverPath) {
      library.bump(patched.type)
    }
    return true
  } catch (error) {
    errorMessage.value = '保存失败'
    console.error(error)
    return false
  } finally {
    saving.value = false
  }
}

async function savePanel(): Promise<void> {
  await persist(false)
}

function openModal(): void {
  modalTextSnapshot.value = { title: draft.title, description: draft.description }
  draft.pendingCoverPath = null
  editOpen.value = true
}

async function saveModal(): Promise<void> {
  const id = selectedId.value
  if (id === null) return
  const pending = draft.pendingCoverPath
  const ok = await persist(true)
  if (!ok) return
  if (pending) {
    try {
      const updated = await replaceCover(id, pending)
      resource.value = updated
      applyResourceToDraft(updated)
      library.bump(updated.type)
    } catch (error) {
      errorMessage.value = '更换封面失败'
      draft.pendingCoverPath = pending
      console.error(error)
      return
    }
  }
  editOpen.value = false
}

function cancelModal(): void {
  if (modalTextSnapshot.value) {
    draft.title = modalTextSnapshot.value.title
    draft.description = modalTextSnapshot.value.description
  }
  draft.pendingCoverPath = null
  editOpen.value = false
}

function onModalShow(value: boolean): void {
  if (!value) cancelModal()
  else editOpen.value = true
}

async function pickCoverImmediate(): Promise<void> {
  const id = selectedId.value
  if (id === null) return
  const paths = (await window.electron.selectFiles([COVER_FILE_FILTER])) ?? []
  const path = paths[0]
  if (!path) return
  errorMessage.value = ''
  try {
    const updated = await replaceCover(id, path)
    resource.value = updated
    applyResourceToDraft(updated)
    library.bump(updated.type)
  } catch (error) {
    errorMessage.value = '更换封面失败'
    console.error(error)
  }
}

async function pickCoverForModal(): Promise<void> {
  const paths = (await window.electron.selectFiles([COVER_FILE_FILTER])) ?? []
  const path = paths[0]
  if (path) draft.pendingCoverPath = path
}

async function pickSubtitle(): Promise<void> {
  const id = selectedId.value
  if (id === null || !isVideo.value) return
  const paths = (await window.electron.selectFiles([SUBTITLE_FILE_FILTER])) ?? []
  const path = paths[0]
  if (!path) return
  subtitleBusy.value = true
  errorMessage.value = ''
  try {
    const updated = await addSubtitle(id, path)
    if (selectedId.value !== id) return
    resource.value = updated
  } catch (error) {
    errorMessage.value = '添加字幕失败'
    console.error(error)
  } finally {
    subtitleBusy.value = false
  }
}

function onTodoAddEnter(event: KeyboardEvent): void {
  if (event.isComposing) return
  void submitTodo()
}

function onTodoRenameEnter(event: KeyboardEvent, todo: ResourceTodo): void {
  if (event.isComposing) return
  const el = event.target as HTMLInputElement | null
  if (el && typeof el.value === 'string') {
    void renameTodo(todo, el.value)
  }
}

function renameTodoFromEvent(todo: ResourceTodo, event: FocusEvent): void {
  const el = event.target as HTMLInputElement | null
  if (!el || typeof el.value !== 'string') return
  void renameTodo(todo, el.value)
}

async function submitTodo(): Promise<void> {
  const id = selectedId.value
  const text = todoInput.value.trim()
  if (id === null || !text) return
  todoBusy.value = true
  errorMessage.value = ''
  try {
    const updated = await addTodo(id, text)
    if (selectedId.value !== id) return
    resource.value = updated
    todoInput.value = ''
  } catch (error) {
    errorMessage.value = '添加待办失败'
    console.error(error)
  } finally {
    todoBusy.value = false
  }
}

async function renameTodo(todo: ResourceTodo, content: string): Promise<void> {
  const id = selectedId.value
  const text = content.trim()
  if (id === null || todo.id == null || !text || text === todo.content) return
  todoBusy.value = true
  errorMessage.value = ''
  try {
    const updated = await patchTodo(id, todo.id, { content: text })
    if (selectedId.value !== id) return
    resource.value = updated
  } catch (error) {
    errorMessage.value = '更新待办失败'
    console.error(error)
  } finally {
    todoBusy.value = false
  }
}

async function toggleTodo(todo: ResourceTodo, done: boolean): Promise<void> {
  const id = selectedId.value
  if (id === null || todo.id == null) return
  todoBusy.value = true
  errorMessage.value = ''
  try {
    const updated = await patchTodo(id, todo.id, { done })
    if (selectedId.value !== id) return
    resource.value = updated
  } catch (error) {
    errorMessage.value = '更新待办失败'
    console.error(error)
  } finally {
    todoBusy.value = false
  }
}

async function removeTodoRow(todo: ResourceTodo): Promise<void> {
  const id = selectedId.value
  if (id === null || todo.id == null) return
  todoBusy.value = true
  errorMessage.value = ''
  try {
    const updated = await removeTodo(id, todo.id)
    if (selectedId.value !== id) return
    resource.value = updated
  } catch (error) {
    errorMessage.value = '删除待办失败'
    console.error(error)
  } finally {
    todoBusy.value = false
  }
}

function openViewerFromCover(): void {
  const row = resource.value
  const id = row?.id
  if (id == null || row?.type !== 'image') return
  const ids = imageViewer.playlistIds.includes(id) ? imageViewer.playlistIds : [id]
  imageViewer.open(id, ids)
}

function playEpisode(fileId: number): void {
  const id = resource.value?.id
  if (id == null) return
  videoPlayer.open(id, [id], fileId)
}

function episodeButtonLabel(ep: SeriesEpisode): string {
  const num = String(ep.episodeNumber).padStart(2, '0')
  const dur = formatDuration(ep.duration)
  const title = ep.title?.trim()
  if (title) return `E${num} ${title} · ${dur}`
  return `E${num} · ${dur}`
}

async function runShell(
  action: (row: Resource | null) => Promise<string | null>
): Promise<void> {
  shellBusy.value = true
  errorMessage.value = ''
  try {
    const message = await action(resource.value)
    if (message) errorMessage.value = message
  } catch (error) {
    errorMessage.value = '打开失败'
    console.error(error)
  } finally {
    shellBusy.value = false
  }
}

function onReveal(): void {
  void runShell(revealPrimary)
}

function onOpenDefault(): void {
  void runShell(openPrimaryDefault)
}

function onOpenWith(): void {
  void runShell(openPrimaryWithOther)
}

function onMoreSelect(key: string | number): void {
  if (key === 'cover') {
    void pickCoverImmediate()
    return
  }
  if (key === 'subtitle') {
    void pickSubtitle()
    return
  }
  if (key === 'reveal') {
    onReveal()
    return
  }
  if (key === 'openDefault') {
    onOpenDefault()
    return
  }
  if (key === 'openWith') {
    onOpenWith()
  }
}

async function handleDelete(): Promise<void> {
  const id = selectedId.value
  const row = resource.value
  if (id === null || row === null) return
  deleting.value = true
  errorMessage.value = ''
  try {
    await deleteResource(id)
    library.bump(null)
    imageViewer.close()
    videoPlayer.close()
    selection.clear()
  } catch (error) {
    errorMessage.value = '删除失败'
    console.error(error)
  } finally {
    deleting.value = false
  }
}

async function handleRestore(): Promise<void> {
  const id = selectedId.value
  if (id === null) return
  deleting.value = true
  errorMessage.value = ''
  try {
    await restoreResource(id)
    library.bump(null)
    imageViewer.close()
    videoPlayer.close()
    selection.clear()
  } catch (error) {
    errorMessage.value = '恢复失败'
    console.error(error)
  } finally {
    deleting.value = false
  }
}

async function handlePurge(): Promise<void> {
  const id = selectedId.value
  if (id === null) return
  deleting.value = true
  errorMessage.value = ''
  try {
    await purgeResource(id)
    library.bump(null)
    imageViewer.close()
    videoPlayer.close()
    selection.clear()
  } catch (error) {
    errorMessage.value = '彻底删除失败'
    console.error(error)
  } finally {
    deleting.value = false
  }
}
</script>

<style scoped lang="less">
.info-panel {
  flex: 0 0 350px;
  width: 350px;
  max-width: 350px;
  min-width: 0;
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  box-sizing: border-box;
  border-left: 1px solid #e5e7eb;
  padding: 12px;
  overflow: hidden;
}

.info-panel-content {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.info-panel-body {
  flex: 1;
  min-width: 0;
  min-height: 0;
  overflow: auto;
}

.info-panel-body :deep(.n-input),
.info-panel-body :deep(.n-select),
.info-panel-body :deep(.n-base-selection) {
  width: 100%;
  max-width: 100%;
}

.info-panel-footer {
  flex-shrink: 0;
  min-width: 0;
  padding-top: 12px;
  margin-top: 8px;
  border-top: 1px solid #e5e7eb;
  background: #fff;
}

.info-panel-empty {
  color: #6b7280;
}

.info-panel-cover {
  display: block;
  width: 100%;
  max-width: 100%;
  max-height: 180px;
  object-fit: contain;

  &--open {
    cursor: zoom-in;
  }
}

.info-panel-title {
  font-weight: 600;
  margin: 8px 0;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.info-panel-meta,
.info-panel-label {
  font-size: 12px;
  color: #6b7280;
  margin-top: 8px;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.info-panel-season {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 8px;
}

.info-panel-episode {
  display: block;
  width: 100%;
  text-align: left;
  font-size: 12px;
  padding: 6px 8px;
  border: 1px solid #e5e7eb;
  border-radius: 4px;
  background: #fff;
  cursor: pointer;
}

.info-panel-episode:hover {
  background: #f3f4f6;
}

.info-panel-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  margin-top: 4px;
  min-width: 0;
}

.info-panel-tags :deep(.n-tag) {
  max-width: 100%;
  height: auto;
  white-space: normal;
  overflow-wrap: anywhere;
}

.info-panel-error {
  color: #b91c1c;
  margin: 8px 0 0;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.info-panel-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.info-panel-todos {
  display: flex;
  flex-direction: column;
  gap: 6px;
  margin-top: 4px;
  min-width: 0;
}

.info-panel-todo {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  min-width: 0;
}

.info-panel-todo :deep(.n-input) {
  flex: 1;
  min-width: 0;
}

.info-panel-todo-add {
  margin-top: 4px;
  min-width: 0;
}
</style>
