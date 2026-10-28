<template>
  <aside class="info-panel">
    <div v-if="resource" class="info-panel-content">
      <div class="info-panel-tabs">
        <button
          v-for="tab in inspectorTabs"
          :key="tab.value"
          type="button"
          class="info-panel-tab"
          :class="{ 'info-panel-tab--active': inspectorTab === tab.value }"
          @click="inspectorTab = tab.value"
        >
          {{ tab.label }}
        </button>
      </div>
      <div class="info-panel-body">
        <template v-if="inspectorTab === 'detail'">
        <section class="info-panel-section">
          <img v-if="coverUrl" class="info-panel-cover" :class="{ 'info-panel-cover--open': isImage }" :src="coverUrl"
            alt="封面" decoding="async" @click="openViewerFromCover" />
          <div class="info-panel-title" :title="resource.title">{{ resource.title }}</div>
          <div class="info-panel-meta">类型 {{ typeLabel }}</div>
          <div v-if="resource.storageKind === 'indexed'" class="info-panel-meta">
            源路径 {{ launchPathLabel }}
          </div>
        </section>
        <section class="info-panel-section">
          <div class="info-panel-section-title">技术信息</div>
          <template v-if="isSeries">
            <EpisodeList
              :resource-id="resource.id"
              :seasons="resource.seasons ?? []"
              :extras="resource.extras ?? []"
              @play="playEpisode"
              @refresh="reloadResource"
            />
          </template>
          <template v-else>
            <div v-if="shown(formatLabel)" class="info-panel-meta">格式 {{ formatLabel }}</div>
            <div class="info-panel-meta">大小 {{ sizeLabel }}</div>
          </template>
          <div class="info-panel-meta">创建 {{ resource.createdAt || '—' }}</div>
          <div v-if="resource.status === 'trashed'" class="info-panel-meta">
            删除 {{ resource.deletedAt || '—' }}
          </div>
          <template v-if="isImage">
            <div v-if="shown(resolutionLabel)" class="info-panel-meta">分辨率 {{ resolutionLabel }}</div>
            <div v-if="shown(takenAtLabel)" class="info-panel-meta">拍摄 {{ takenAtLabel }}</div>
            <div v-if="shown(cameraLabel)" class="info-panel-meta">机身 {{ cameraLabel }}</div>
            <div v-if="shown(lensLabel)" class="info-panel-meta">镜头 {{ lensLabel }}</div>
            <div v-if="shown(isoLabel)" class="info-panel-meta">ISO {{ isoLabel }}</div>
            <div v-if="shown(apertureLabel)" class="info-panel-meta">光圈 {{ apertureLabel }}</div>
            <div v-if="shown(shutterLabel)" class="info-panel-meta">快门 {{ shutterLabel }}</div>
            <div class="info-panel-meta">
              <n-checkbox
                :checked="timelineEffective"
                :disabled="timelineBusy"
                @update:checked="toggleTimeline"
              >
                计入时间线
              </n-checkbox>
            </div>
            <div v-if="hasGps || resource.mapVisible === true" class="info-panel-meta">
              <n-checkbox
                :checked="mapEffective"
                :disabled="mapBusy"
                @update:checked="toggleMap"
              >
                加入地图
              </n-checkbox>
            </div>
          </template>
          <template v-else-if="isVideo">
            <div v-if="shown(resolutionLabel)" class="info-panel-meta">分辨率 {{ resolutionLabel }}</div>
            <div v-if="shown(clarityText)" class="info-panel-meta">清晰度 {{ clarityText }}</div>
            <div v-if="shown(durationLabel)" class="info-panel-meta">时长 {{ durationLabel }}</div>
            <div v-if="shown(fpsLabel)" class="info-panel-meta">帧率 {{ fpsLabel }}</div>
            <div v-if="shown(bitrateLabel)" class="info-panel-meta">码率 {{ bitrateLabel }}</div>
            <div v-if="shown(qualityText)" class="info-panel-meta">画质 {{ qualityText }}</div>
            <div v-if="shown(takenAtLabel)" class="info-panel-meta">拍摄 {{ takenAtLabel }}</div>
            <div class="info-panel-meta">
              <n-checkbox
                :checked="timelineEffective"
                :disabled="timelineBusy"
                @update:checked="toggleTimeline"
              >
                计入时间线
              </n-checkbox>
            </div>
            <div v-if="hasGps || resource.mapVisible === true" class="info-panel-meta">
              <n-checkbox
                :checked="mapEffective"
                :disabled="mapBusy"
                @update:checked="toggleMap"
              >
                加入地图
              </n-checkbox>
            </div>
            <div v-if="subtitleNames.length" class="info-panel-meta">
              字幕 {{ subtitleNames.join('、') }}
            </div>
          </template>
        </section>
        <section v-if="resource.synopsis || resource.catalog" class="info-panel-section">
          <div class="info-panel-section-title">作品资料</div>
          <div v-if="resource.synopsis" class="info-panel-synopsis">{{ resource.synopsis }}</div>
          <div v-if="resource.catalog?.nameCn" class="info-panel-meta">中文名 {{ resource.catalog.nameCn }}</div>
          <div v-if="resource.catalog?.originalTitle" class="info-panel-meta">
            原名 {{ resource.catalog.originalTitle }}
          </div>
          <div v-if="resource.catalog?.date" class="info-panel-meta">放送 {{ resource.catalog.date }}</div>
          <div v-if="resource.catalog?.platform" class="info-panel-meta">平台 {{ resource.catalog.platform }}</div>
          <div v-if="resource.catalog?.eps != null" class="info-panel-meta">集数 {{ resource.catalog.eps }}</div>
          <div v-if="resource.catalog?.siteScore != null" class="info-panel-meta">
            站点评分 {{ resource.catalog.siteScore }}
          </div>
          <div v-for="row in catalogInfobox" :key="row.key" class="info-panel-meta">
            {{ row.key }} {{ row.text }}
          </div>
        </section>
        <section class="info-panel-section">
          <div class="info-panel-section-title">编辑</div>
          <template v-if="shown(draft.synopsis)">
            <div class="info-panel-label">作品简介</div>
            <n-input
              type="textarea"
              :autosize="{ minRows: 2, maxRows: 5 }"
              :value="draft.synopsis"
              placeholder="站点或自行填写的作品简介"
              @update:value="draft.synopsis = $event"
            />
          </template>
          <template v-if="shown(draft.description)">
            <div class="info-panel-label">我的评价</div>
            <n-input
              type="textarea"
              :autosize="{ minRows: 2, maxRows: 5 }"
              :value="draft.description"
              placeholder="你对这部作品的评价，刮削不会覆盖"
              @update:value="draft.description = $event"
            />
          </template>
          <template v-if="shown(draft.author)">
            <div class="info-panel-label">作者</div>
            <n-input :value="draft.author" placeholder="可选" @update:value="draft.author = $event" />
          </template>
          <template v-if="isImage && shown(draft.takenAtLocal)">
            <div class="info-panel-label">拍摄</div>
            <input
              class="info-panel-taken"
              type="datetime-local"
              :value="draft.takenAtLocal"
              @input="onTakenAtInput"
            />
          </template>
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
        <template v-if="isWork">
          <div class="info-panel-label">备注</div>
          <div class="info-panel-todos">
            <div v-for="note in workNotes" :key="note.id" class="info-panel-note">
              <div class="info-panel-note-title">{{ note.title || '备注' }}</div>
              <div class="info-panel-note-body">{{ note.content }}</div>
              <n-button size="tiny" quaternary :disabled="noteBusy" @click="removeNote(note.id)">删</n-button>
            </div>
            <n-input
              size="small"
              :value="noteTitle"
              placeholder="标题"
              :disabled="noteBusy"
              @update:value="noteTitle = $event"
            />
            <n-input
              type="textarea"
              size="small"
              :autosize="{ minRows: 2, maxRows: 4 }"
              :value="noteContent"
              placeholder="内容，回车添加"
              :disabled="noteBusy"
              @update:value="noteContent = $event"
              @keydown.enter.exact.prevent="addNote"
            />
          </div>
        </template>
        </section>
        </template>
        <InfoPanelRelationTab
          v-else-if="inspectorTab === 'relation'"
          :rating="draft.ratingStars"
          :category-options="categoryOptions"
          :category-ids="draft.categoryIds"
          :tag-names="draft.tagNames"
          :tag-input="draft.tagInput"
          :character-options="characterOptions"
          :character-ids="characterIds"
          :character-busy="characterBusy"
          :person-options="personOptions"
          :person-ids="personIds"
          :person-busy="personBusy"
          @update:rating="draft.ratingStars = $event"
          @update:category-ids="draft.categoryIds = $event"
          @update:tag-input="draft.tagInput = $event"
          @remove-tag="removeTag"
          @commit-tag="commitTagInput"
          @update:characters="(value) => void updateCharacters(value)"
          @update:persons="(value) => void updatePersons(value)"
        />
        <InfoPanelAITab
          v-else
          :is-image="isImage"
          @similar="openSimilar"
          @open-ai="openAICenter"
        />
      </div>
      <InfoPanelFooter
        v-if="inspectorTab !== 'ai'"
        :saving="saving"
        :dirty="dirty"
        :resource-type="resource.type"
        :thumbnail-busy="thumbnailBusy"
        :needs-scrape-query="needsScrapeQuery"
        :scrape-query-placeholder="scrapeQueryPlaceholder"
        :scrape-query="scrapeQuery"
        :is-shell-open="isShellOpen"
        :can-shell-open="canShellOpen"
        :shell-busy="shellBusy"
        :shell-action-label="shellActionLabel"
        :more-options="moreOptions"
        :deleting="deleting"
        :resource-status="resource.status"
        :error-message="errorMessage"
        @save="savePanel"
        @rebuild-thumbnail="rebuildCurrentThumbnail"
        @update:scrape-query="scrapeQuery = $event"
        @open-default="onOpenDefault"
        @edit="openModal"
        @more="onMoreSelect"
        @delete="handleDelete"
        @restore="handleRestore"
        @purge="handlePurge"
      />
      <EditResourceModal :show="editOpen" :draft="draft" :category-options="categoryOptions" :cover-url="modalCoverUrl"
        :saving="saving" :allow-cover="canChangeCover" :show-taken-at="isImage" @update:show="onModalShow"
        @save="saveModal" @cancel="cancelModal" @pick-cover="pickCoverForModal" />
      <InfoPanelCollectionsModal
        :show="collectionOpen"
        :resource-id="resource?.id ?? null"
        @update:show="collectionOpen = $event"
      />
      <ScrapeConfirmQueue
        v-model:show="scrapeOpen"
        :resource-ids="scrapeIds"
        :force="scrapeForce"
        :prefer-latest="scrapePreferLatest"
        :allow-bili-query="needsScrapeQuery"
        :query-placeholder="scrapeQueryPlaceholder"
        :query-empty-hint="scrapeQueryEmptyHint"
        :initial-query="scrapeQueryHint"
        @applied="onScrapeApplied"
      />
    </div>
    <div v-else class="info-panel-empty">未选择资源</div>
  </aside>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NCheckbox, NDropdown, NInput, NModal, NPopconfirm, NRate, NSelect, NTag } from 'naive-ui'
import type { DropdownOption } from 'naive-ui'
import EditResourceModal from '@/components/EditResourceModal/index.vue'
import EpisodeList from '@/components/EpisodeList/index.vue'
import InfoPanelCollectionsModal from './InfoPanelCollectionsModal.vue'
import InfoPanelAITab from './InfoPanelAITab.vue'
import InfoPanelRelationTab from './InfoPanelRelationTab.vue'
import InfoPanelFooter from './InfoPanelFooter.vue'
import ScrapeConfirmQueue from '@/components/ScrapeConfirmQueue/index.vue'
import { getResource, getCategoryTree, listCharacters, listPersons, invalidateResourceCache, rebuildThumbnail, resolveCardImageUrl } from '@/infrastructure/http'
import { openResource } from '@/infrastructure/consume/consumeResource'
import { createWorkNote, deleteWorkNote } from '@/infrastructure/http/workbench'
import { useSelectionStore } from '@/application/stores/selection'
import { useLibraryStore } from '@/application/stores/library'
import { useCategoryTreeStore } from '@/application/stores/categoryTree'
import { useImageViewerStore } from '@/application/stores/imageViewer'
import { useVideoPlayerStore } from '@/application/stores/videoPlayer'
import {
  openLaunchOrPrimary,
  openAny,
  openPrimaryWithOther,
  revealInFolder,
  launchOrPrimaryPath,
  revealablePath,
} from '@/infrastructure/shell/openLibraryFile'
import { useResourceHandle } from '@/hooks/useResourceHandle'
import { notify } from '@/application/notify'
import { storeToRefs } from 'pinia'
import type { CategoryNode, MetadataDraft, Resource, ResourceFile, ResourceTodo, SeriesEpisode } from '@/domain'
import {
  COVER_FILE_FILTER,
  FILE_ROLE,
  RESOURCE_TYPE_LABEL,
  SUBTITLE_FILE_FILTER,
  clarityLabel,
  consumeKindOf,
  formatBitrate,
  formatDuration,
  formatFps,
  formatResolution,
  isSeriesResourceType,
  localInputToTakenAt,
  profileFor,
  qualityLabel,
  takenAtToLocalInput,
} from '@/domain'

const selection = useSelectionStore()
const library = useLibraryStore()
const categoryStore = useCategoryTreeStore()
const imageViewer = useImageViewerStore()
const videoPlayer = useVideoPlayerStore()
const shellBusy = ref(false)
const { selectedId } = storeToRefs(selection)
const { deleteResource, restoreResource, purgeResource, patchResource, replaceCover, addSubtitle, addTodo, patchTodo, removeTodo } =
  useResourceHandle()

const resource = ref<Resource | null>(null)
const inspectorTab = ref<'detail' | 'relation' | 'ai'>('detail')
const router = useRouter()
const inspectorTabs = [
  { value: 'detail', label: '详情' },
  { value: 'relation', label: '关联' },
  { value: 'ai', label: 'AI' },
] as const
const categories = ref<CategoryNode[]>([])
const deleting = ref(false)
const saving = ref(false)
const thumbnailBusy = ref(false)
const errorMessage = ref('')
const editOpen = ref(false)
const modalTextSnapshot = ref<{ title: string; description: string; synopsis: string } | null>(null)
let loadGen = 0

const todoInput = ref('')
const todoBusy = ref(false)
const subtitleBusy = ref(false)
const timelineBusy = ref(false)
const mapBusy = ref(false)
const characterBusy = ref(false)
const characterOptions = ref<{ label: string; value: number }[]>([])
const personBusy = ref(false)
const personOptions = ref<{ label: string; value: number }[]>([])

const draft = reactive<MetadataDraft>({
  title: '',
  description: '',
  synopsis: '',
  author: '',
  ratingStars: 0,
  categoryIds: [],
  tagNames: [],
  tagInput: '',
  pendingCoverPath: null,
  takenAtLocal: '',
})

function applyResourceToDraft(row: Resource): void {
  draft.title = row.title
  draft.description = row.description ?? ''
  draft.synopsis = row.synopsis ?? ''
  draft.author = row.author ?? ''
  draft.ratingStars = (row.rating ?? 0) / 2
  draft.categoryIds = (row.categories ?? []).map((category) => category.id).filter((id): id is number => id != null)
  draft.tagNames = (row.tags ?? []).map((t) => t.name)
  draft.tagInput = ''
  draft.pendingCoverPath = null
  const primary = row.files?.find((f) => f.role === FILE_ROLE.PRIMARY) ?? row.files?.[0]
  draft.takenAtLocal = takenAtToLocalInput(primary?.exifTakenAt)
}

function snapshotEqualsSaved(): boolean {
  const row = resource.value
  if (!row) return true
  const savedTags = (row.tags ?? []).map((t) => t.name).join('\0')
  const draftTags = [...draft.tagNames].join('\0')
  const savedCategories = (row.categories ?? []).map((category) => category.id ?? 0).sort().join(',')
  const draftCategories = [...draft.categoryIds].sort().join(',')
  return (
    draft.ratingStars === (row.rating ?? 0) / 2 &&
    (draft.description ?? '') === (row.description ?? '') &&
    (draft.synopsis ?? '') === (row.synopsis ?? '') &&
    (draft.author ?? '') === (row.author ?? '') &&
    savedCategories === draftCategories &&
    savedTags === draftTags &&
    draft.tagInput.trim() === '' &&
    draft.takenAtLocal === takenAtToLocalInput(primaryTakenAt(row))
  )
}

const dirty = computed(() => !snapshotEqualsSaved())

const typeLabel = computed(() =>
  resource.value ? RESOURCE_TYPE_LABEL[resource.value.type] : '—'
)
const consume = computed(() =>
  resource.value ? consumeKindOf(resource.value.type) : undefined
)
const isVideo = computed(() => consume.value === 'overlay-video')
const isImage = computed(() => consume.value === 'overlay-image')
const isSeries = computed(() =>
  resource.value != null && isSeriesResourceType(resource.value.type)
)
const isShellOpen = computed(() => consume.value === 'shell-open')
const isWork = computed(() => resource.value?.type === 'work_directory')
const noteTitle = ref('')
const noteContent = ref('')
const noteBusy = ref(false)
const workNotes = computed(() => {
  const raw = resource.value?.extra?.workNotes
  if (!Array.isArray(raw)) return []
  return raw.flatMap((item) => {
    if (!item || typeof item !== 'object') return []
    const row = item as { id?: unknown; title?: unknown; content?: unknown }
    if (typeof row.id !== 'string') return []
    return [{ id: row.id, title: String(row.title ?? ''), content: String(row.content ?? '') }]
  })
})
const hasLaunch = computed(() =>
  (resource.value?.files ?? []).some((f) => f.role === FILE_ROLE.LAUNCH)
)
const canShellOpen = computed(() => launchOrPrimaryPath(resource.value) != null)
const canReveal = computed(() => revealablePath(resource.value) != null)
const revealHint = computed(() => {
  if (shellBusy.value) return '正在打开…'
  if (!canReveal.value) return '找不到可定位的文件'
  return '在系统资源管理器中显示'
})
const shellActionLabel = computed(() => {
  if (isWork.value) return '外部打开'
  return hasLaunch.value ? '启动' : '打开'
})
const revealLabel = computed(() => (isWork.value ? '资源管理器' : '打开所在位置'))
const launchPathLabel = computed(() => revealablePath(resource.value) ?? '—')

/** 图片主文件即作品，不能换封面；其余类型可手选海报。 */
const canChangeCover = computed(() =>
  resource.value != null && profileFor(resource.value.type)?.allowsUserCover === true
)
const canScrape = computed(() => {
  const type = resource.value?.type
  return type === 'video' || type === 'anime' || type === 'image'
})
const needsScrapeQuery = computed(
  () => resource.value?.type === 'video' || resource.value?.type === 'image'
)
const scrapeQueryPlaceholder = computed(() =>
  resource.value?.type === 'image' ? '作品页面链接' : 'BV号、av、视频链接或名称'
)
const scrapeQueryEmptyHint = computed(() =>
  resource.value?.type === 'image' ? '请填写页面链接' : '请填写 BV 号、链接或视频名称'
)
const scrapeBusy = ref(false)
const scrapeOpen = ref(false)
const scrapeIds = ref<number[]>([])
const scrapeForce = ref(false)
const scrapePreferLatest = ref(false)
const scrapeQuery = ref('')
const scrapeQueryHint = ref('')

function openScrape(force: boolean): void {
  const id = resource.value?.id
  if (id == null) return
  const typed = needsScrapeQuery.value ? scrapeQuery.value.trim() : ''
  if (resource.value?.type === 'image' && !typed && !resource.value.scrapePending) {
    errorMessage.value = '请填写作品页面链接'
    return
  }
  errorMessage.value = ''
  scrapeQueryHint.value = typed
  scrapeForce.value = force || typed.length > 0
  scrapePreferLatest.value = !scrapeForce.value && resource.value?.scrapePending === true
  scrapeIds.value = [id]
  scrapeOpen.value = true
}

async function onScrapeApplied(): Promise<void> {
  const id = resource.value?.id
  if (id == null) return
  invalidateResourceCache(id)
  resource.value = await getResource(id)
  applyResourceToDraft(resource.value)
}

const moreOptions = computed((): DropdownOption[] => {
  const items: DropdownOption[] = []
  if (canChangeCover.value) items.push({ label: '更换封面', key: 'cover' })
  if (canScrape.value) {
    items.push({
      label: resource.value?.scrapePending ? '查看候选' : '获取元数据',
      key: 'scrape',
      disabled: scrapeBusy.value,
    })
    if (resource.value?.scrapePending) {
      items.push({ label: '重新搜索元数据', key: 'scrapeForce', disabled: scrapeBusy.value })
    }
  }
  items.push({ label: '加入合集', key: 'collections' })
  if (isVideo.value) items.push({ label: '添加字幕', key: 'subtitle', disabled: subtitleBusy.value })
  if (isImage.value || isShellOpen.value || consume.value === 'overlay-model') {
    items.push({ label: '打开默认应用', key: 'openDefault', disabled: shellBusy.value })
    if (!isWork.value) {
      items.push({ label: '用其他应用打开', key: 'openWith', disabled: shellBusy.value })
    }
  }
  if (canReveal.value) {
    items.push({ label: revealLabel.value, key: 'reveal', disabled: shellBusy.value })
  }
  return items
})


function primaryTakenAt(row: Resource): string | null | undefined {
  const files = row.files ?? []
  return (files.find((f) => f.role === FILE_ROLE.PRIMARY) ?? files[0])?.exifTakenAt
}

const timelineEffective = computed(() => {
  const row = resource.value
  if (!row || (row.type !== 'image' && row.type !== 'video')) return false
  if (row.timelineVisible === true) return true
  if (row.timelineVisible === false) return false
  return Boolean(primaryTakenAt(row))
})

const hasGps = computed(() => {
  const file = primaryFile()
  return file?.exifLat != null && file?.exifLng != null
})

const characterIds = computed(() =>
  (resource.value?.characters ?? []).map((character) => character.id),
)
const personIds = computed(() =>
  (resource.value?.persons ?? []).map((person) => person.id),
)

async function loadCharacterOptions(): Promise<void> {
  try {
    const characters = await listCharacters()
    characterOptions.value = characters.map((character) => ({
      label: character.workName ? `${character.name} ? ${character.workName}` : character.name,
      value: character.id,
    }))
  } catch {
    characterOptions.value = []
  }
}

async function loadPersonOptions(): Promise<void> {
  try {
    const persons = await listPersons()
    personOptions.value = persons.map((person) => ({ label: person.name, value: person.id }))
  } catch {
    personOptions.value = []
  }
}

async function updatePersons(ids: number[]): Promise<void> {
  const id = selectedId.value
  if (id === null) return
  personBusy.value = true
  try {
    const patched = await patchResource(id, { personIds: ids })
    resource.value = patched
    library.invalidate({ resources: [patched.type], home: true })
  } catch (error) {
    notify.fromError(error, { context: '更新人物失败' })
  } finally {
    personBusy.value = false
  }
}

async function updateCharacters(ids: number[]): Promise<void> {
  const id = selectedId.value
  if (id === null) return
  characterBusy.value = true
  try {
    const patched = await patchResource(id, { characterIds: ids })
    resource.value = patched
    library.invalidate({ resources: [patched.type], home: true })
  } catch (error) {
    notify.fromError(error, { context: '更新角色失败' })
  } finally {
    characterBusy.value = false
  }
}

async function rebuildCurrentThumbnail(): Promise<void> {
  const id = selectedId.value
  if (id === null) return
  thumbnailBusy.value = true
  try {
    const result = await rebuildThumbnail(id)
    invalidateResourceCache(id)
    resource.value = await getResource(id)
    if (result.failed) notify.toast.error('缩略图重建失败')
    else if (result.skipped) notify.toast.warning('没有可用的源图')
    else notify.toast.success('缩略图已重建')
  } catch (error) {
    notify.fromError(error, { context: '重建缩略图' })
  } finally {
    thumbnailBusy.value = false
  }
}

const mapEffective = computed(() => {
  const row = resource.value
  if (!row || (row.type !== 'image' && row.type !== 'video')) return false
  if (row.mapVisible === true) return true
  if (row.mapVisible === false) return false
  return hasGps.value
})

async function toggleTimeline(checked: boolean): Promise<void> {
  const id = selectedId.value
  if (id === null) return
  timelineBusy.value = true
  try {
    const patched = await patchResource(id, { timelineVisible: checked })
    resource.value = patched
    applyResourceToDraft(patched)
    library.invalidate({ resources: [patched.type], home: true })
  } catch (error) {
    notify.fromError(error, { context: '更新地图状态失败' })
  } finally {
    timelineBusy.value = false
  }
}

async function toggleMap(checked: boolean): Promise<void> {
  const id = selectedId.value
  if (id === null) return
  mapBusy.value = true
  try {
    const patched = await patchResource(id, { mapVisible: checked })
    resource.value = patched
    applyResourceToDraft(patched)
    library.invalidate({ resources: [patched.type], savedViews: true, home: true })
  } catch (error) {
    notify.fromError(error, { context: '更新地图状态失败' })
  } finally {
    mapBusy.value = false
  }
}

function onTakenAtInput(event: Event): void {
  draft.takenAtLocal = (event.target as HTMLInputElement).value
}

function primaryFile(): ResourceFile | undefined {
  const files = resource.value?.files ?? []
  return files.find((f) => f.role === FILE_ROLE.PRIMARY) ?? files[0]
}

const sizeLabel = computed(() => formatBytes(primaryFile()?.size))
const formatLabel = computed(() => primaryFile()?.format || '—')
const resolutionLabel = computed(() => formatResolution(primaryFile()?.width, primaryFile()?.height))
const takenAtLabel = computed(() => {
  const local = takenAtToLocalInput(primaryFile()?.exifTakenAt)
  return local ? local.replace('T', ' ') : '—'
})
const cameraLabel = computed(() => primaryFile()?.exifCamera || '—')
const lensLabel = computed(() => primaryFile()?.exifLens || '—')
const isoLabel = computed(() => {
  const iso = primaryFile()?.exifIso
  return iso != null && iso > 0 ? String(iso) : '—'
})
const apertureLabel = computed(() => primaryFile()?.exifAperture || '—')
const shutterLabel = computed(() => primaryFile()?.exifShutter || '—')
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

function infoboxText(value: unknown): string {
  if (value == null) return ''
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  if (Array.isArray(value)) {
    return value
      .map((item) => (item && typeof item === 'object' && 'v' in item ? String((item as { v?: unknown }).v ?? '') : infoboxText(item)))
      .filter(Boolean)
      .join('、')
  }
  return ''
}

const catalogInfobox = computed(() => {
  const rows = resource.value?.catalog?.infobox ?? []
  const out: { key: string; text: string }[] = []
  for (const row of rows) {
    const key = String(row.key ?? '')
    if (!key || key === '中文名' || key === '话数') continue
    const text = infoboxText(row.value)
    if (!text) continue
    out.push({ key, text })
    if (out.length >= 8) break
  }
  return out
})

const modalCoverUrl = computed(() => coverUrl.value)

const categoryOptions = computed(() => {
  const out: { label: string; value: number }[] = []
  const walk = (nodes: CategoryNode[], prefix = ''): void => {
    for (const node of nodes) {
      const path = prefix ? `${prefix} / ${node.name}` : node.name
      out.push({ label: path, value: node.id })
      if (node.children?.length) walk(node.children, path)
    }
  }
  walk(categories.value)
  return out
})

watch(
  () => (resource.value ? categoryStore.trees[resource.value.type] : undefined),
  (tree) => {
    if (tree) categories.value = tree
  },
  { deep: true },
)

watch(
  selectedId,
  async (id) => {
    const gen = ++loadGen
    errorMessage.value = ''
    editOpen.value = false
    scrapeOpen.value = false
    todoInput.value = ''
    noteTitle.value = ''
    noteContent.value = ''
    scrapeQuery.value = ''
    scrapeQueryHint.value = ''
    if (id === null) {
      resource.value = null
      return
    }
    try {
      const row = await getResource(id)
      if (gen !== loadGen) return
      resource.value = row
      applyResourceToDraft(row)
      void getCategoryTree(row.type).then((cats) => {
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
  () => (resource.value ? library.resourceRevision(resource.value.type) : 0),
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

watch(
  () => (resource.value ? library.categoryRevision(resource.value.type) : 0),
  () => {
    const type = resource.value?.type
    if (type) void categoryStore.load(type, true)
  }
)

function formatBytes(n: number | null | undefined): string {
  if (n == null || n <= 0) return '—'
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / (1024 * 1024)).toFixed(1)} MB`
}

/** 空值（''/占位 '—'）不展示：次要字段美观收敛 */
function shown(text: string): boolean {
  const value = text.trim()
  return value !== '' && value !== '—'
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
      synopsis: draft.synopsis || null,
      author: draft.author || null,
      rating: draft.ratingStars * 2,
      categoryIds: [...draft.categoryIds],
      tagNames: [...draft.tagNames],
      ...(row.type === 'image' ? { exifTakenAt: localInputToTakenAt(draft.takenAtLocal) } : {}),
    })
    resource.value = patched
    const pending = draft.pendingCoverPath
    applyResourceToDraft(patched)
    draft.pendingCoverPath = pending
    library.invalidate({
      resources: [patched.type],
      categories: [patched.type],
      tags: true,
      home: true,
    })
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

function openAICenter(): void {
  void router.push({ path: '/ai', query: { tab: 'search' } })
}

function openSimilar(): void {
  if (resource.value?.id == null) return
  void router.push({
    path: '/ai',
    query: { tab: 'similar', resourceId: String(resource.value.id) },
  })
}

function openModal(): void {
  modalTextSnapshot.value = {
    title: draft.title,
    description: draft.description,
    synopsis: draft.synopsis,
  }
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
      library.invalidate({ resources: [updated.type], home: true })
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
    draft.synopsis = modalTextSnapshot.value.synopsis
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
  if (id === null || !canChangeCover.value) return
  const paths = (await window.electron.selectFiles([COVER_FILE_FILTER])) ?? []
  const path = paths[0]
  if (!path) return
  errorMessage.value = ''
  try {
    const updated = await replaceCover(id, path)
    resource.value = updated
    applyResourceToDraft(updated)
    library.invalidate({ resources: [updated.type], home: true })
  } catch (error) {
    errorMessage.value = '更换封面失败'
    console.error(error)
  }
}

async function pickCoverForModal(): Promise<void> {
  if (!canChangeCover.value) return
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
  const bound = imageViewer.boundImageIds()
  const ids = bound.includes(id) ? bound : [id]
  void openResource(row, { playlist: ids })
}

function playEpisode(fileId: number): void {
  const row = resource.value
  const id = row?.id
  if (id == null || !row) return
  void openResource(row, { playlist: [id], fileId })
}

async function reloadResource(): Promise<void> {
  const id = selectedId.value
  if (id == null) return
  const row = await getResource(id)
  if (selectedId.value === id) resource.value = row
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
  void runShell(revealInFolder)
}

function onOpenDefault(): void {
  void runShell(isWork.value ? openAny : openLaunchOrPrimary)
}

function onOpenWith(): void {
  void runShell(openPrimaryWithOther)
}

async function addNote(): Promise<void> {
  const id = resource.value?.id
  if (id == null || noteBusy.value) return
  if (!noteTitle.value.trim() && !noteContent.value.trim()) return
  noteBusy.value = true
  errorMessage.value = ''
  try {
    resource.value = await createWorkNote(id, noteTitle.value, noteContent.value)
    noteTitle.value = ''
    noteContent.value = ''
    library.invalidate({ resources: ['work_directory'], home: true })
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '备注保存失败'
  } finally {
    noteBusy.value = false
  }
}

async function removeNote(noteId: string): Promise<void> {
  const id = resource.value?.id
  if (id == null || noteBusy.value) return
  noteBusy.value = true
  errorMessage.value = ''
  try {
    resource.value = await deleteWorkNote(id, noteId)
    library.invalidate({ resources: ['work_directory'], home: true })
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '备注删除失败'
  } finally {
    noteBusy.value = false
  }
}

const collectionOpen = ref(false)
function openCollections(): void {
  if (resource.value?.id != null) collectionOpen.value = true
}

function onMoreSelect(key: string | number): void {
  if (key === 'cover') {
    void pickCoverImmediate()
    return
  }
  if (key === 'scrape') {
    openScrape(false)
    return
  }
  if (key === 'scrapeForce') {
    openScrape(true)
    return
  }
  if (key === 'collections') {
    openCollections()
    return
  }
  if (key === 'reveal') {
    onReveal()
    return
  }
  if (key === 'subtitle') {
    void pickSubtitle()
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
    library.invalidate({
      resources: [row.type],
      categories: [row.type],
      collections: true,
      home: true,
    })
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
    library.invalidate({
      resources: true,
      categories: true,
      collections: true,
      home: true,
    })
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
    library.invalidate({
      resources: true,
      categories: true,
      collections: true,
      home: true,
    })
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
onMounted(() => {
  void loadCharacterOptions()
  void loadPersonOptions()
})
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
  background: var(--sm-color-bg-surface);
  color: var(--sm-color-text);
  border-left: 1px solid var(--sm-color-border);
  padding: var(--sm-space-3);
  overflow: hidden;
}

.info-panel-content {
  flex: 1;
  min-width: 0;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.info-panel-tabs {
  display: flex;
  flex-shrink: 0;
  gap: 2px;
  padding-bottom: var(--sm-space-2);
  border-bottom: 1px solid var(--sm-color-border);
}

.info-panel-tab {
  padding: 4px 10px;
  border: 0;
  border-radius: 6px;
  background: transparent;
  color: var(--sm-color-text-muted);
  font: inherit;
  font-size: 12px;
  cursor: pointer;
}

.info-panel-tab:hover {
  background: var(--sm-color-bg-muted);
  color: var(--sm-color-text);
}

.info-panel-tab--active {
  background: var(--sm-color-bg-muted);
  color: var(--sm-color-text);
  font-weight: 600;
}

.info-panel-body {
  flex: 1;
  min-width: 0;
  min-height: 0;
  overflow: auto;
  padding-top: var(--sm-space-1);
}

.info-panel-ai-empty {
  color: var(--sm-color-text-muted);
  font-size: 12px;
  line-height: 1.6;

  p {
    margin: 8px 0 12px;
  }
}

.info-panel-ai-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
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
  padding-top: var(--sm-space-3);
  margin-top: var(--sm-space-2);
  border-top: 1px solid var(--sm-color-border);
  background: var(--sm-color-bg-surface);
}

.info-panel-section-title {
  font-size: 12px;
  font-weight: 600;
  color: var(--sm-color-text);
  margin-top: var(--sm-space-2);
}

.info-panel-empty {
  color: var(--sm-color-text-muted);
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

.info-panel-characters {
  margin-top: 8px;
}

.info-panel-title {
  font-weight: 600;
  margin: 8px 0;
  overflow-wrap: anywhere;
  word-break: break-word;
}

.info-panel-synopsis {
  font-size: 12px;
  white-space: pre-wrap;
  margin-top: 8px;
  max-height: 160px;
  overflow: auto;
}

.info-panel-meta,
.info-panel-label {
  font-size: 12px;
  color: var(--sm-color-text-muted);
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
  border: 1px solid var(--sm-color-border);
  border-radius: var(--sm-radius-control);
  background: var(--sm-color-bg-surface);
  color: var(--sm-color-text);
  cursor: pointer;
}

.info-panel-episode:hover {
  background: var(--sm-color-bg-page);
}

.info-panel-taken {
  width: 100%;
  max-width: 100%;
  box-sizing: border-box;
  margin-top: 4px;
  padding: 6px 8px;
  font-size: 13px;
  color: var(--sm-color-text);
  background: var(--sm-color-bg-surface);
  border: 1px solid var(--sm-color-border);
  border-radius: var(--sm-radius-control);
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

.info-panel-note {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  gap: 4px 8px;
  min-width: 0;
}

.info-panel-note-title,
.info-panel-note-body {
  overflow-wrap: anywhere;
  word-break: break-word;
}

.info-panel-note-body {
  grid-column: 1;
  color: var(--sm-color-text-muted);
  font-size: 12px;
}

</style>
