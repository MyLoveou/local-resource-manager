<template>
  <aside class="info-panel">
    <div v-if="resource" class="info-panel-content">
      <div class="info-panel-body">
        <img v-if="coverUrl" class="info-panel-cover" :src="coverUrl" alt="封面" />
        <div class="info-panel-title">{{ resource.title }}</div>
        <div class="info-panel-meta">类型 {{ typeLabel }}</div>
        <div class="info-panel-meta">大小 {{ sizeLabel }}</div>
        <div class="info-panel-meta">创建 {{ resource.createdAt || '—' }}</div>
        <!-- 分类是独立词表，不是 type -->
        <div class="info-panel-label">评分</div>
        <n-rate allow-half :count="5" :value="draft.ratingStars" @update:value="draft.ratingStars = $event" />
        <div class="info-panel-label">分类</div>
        <n-select
          filterable
          tag
          clearable
          :options="categoryOptions"
          :value="draft.categoryName"
          @update:value="draft.categoryName = $event"
        />
        <div class="info-panel-label">标签（Enter 切词）</div>
        <div class="info-panel-tags">
          <n-tag v-for="name in draft.tagNames" :key="name" closable @close="removeTag(name)">
            {{ name }}
          </n-tag>
          <n-input
            :value="draft.tagInput"
            placeholder="回车添加"
            size="small"
            style="width: 120px"
            @update:value="draft.tagInput = $event"
            @keydown.enter.prevent="commitTagInput"
          />
        </div>
      </div>
      <div class="info-panel-footer">
        <div class="info-panel-actions">
          <n-button size="small" :loading="saving" :disabled="!dirty" @click="savePanel">保存</n-button>
          <n-button size="small" @click="openModal">编辑</n-button>
          <n-button v-if="canChangeCover" size="small" @click="pickCoverImmediate">更换封面</n-button>
          <n-popconfirm positive-text="删除" negative-text="取消" @positive-click="handleDelete">
            <template #trigger>
              <n-button size="small" type="error" :disabled="deleting" ghost>删除</n-button>
            </template>
            确定将此资源移入回收站？
          </n-popconfirm>
        </div>
        <p v-if="errorMessage" class="info-panel-error">{{ errorMessage }}</p>
      </div>
      <EditResourceModal
        :show="editOpen"
        :draft="draft"
        :category-options="categoryOptions"
        :cover-url="modalCoverUrl"
        :saving="saving"
        :allow-cover="canChangeCover"
        @update:show="onModalShow"
        @save="saveModal"
        @cancel="cancelModal"
        @pick-cover="pickCoverForModal"
      />
    </div>
    <div v-else class="info-panel-empty">未选择资源</div>
  </aside>
</template>

<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'
import { NButton, NInput, NPopconfirm, NRate, NSelect, NTag } from 'naive-ui'
import EditResourceModal from '@/components/EditResourceModal/index.vue'
import { getResource, getCategories, resolveLibraryMediaUrl } from '@/infrastructure/http'
import { useSelectionStore } from '@/application/stores/selection'
import { useLibraryStore } from '@/application/stores/library'
import { useResourceHandle } from '@/hooks/useResourceHandle'
import { storeToRefs } from 'pinia'
import type { Category, MetadataDraft, Resource } from '@/domain'

const IMAGE_FILTER = {
  name: '图片',
  extensions: ['jpg', 'jpeg', 'png', 'webp', 'gif', 'bmp', 'heic', 'avif'],
}

const selection = useSelectionStore()
const library = useLibraryStore()
const { selectedId } = storeToRefs(selection)
const { deleteResource, patchResource, replaceCover } = useResourceHandle()

const resource = ref<Resource | null>(null)
const categories = ref<Category[]>([])
const deleting = ref(false)
const saving = ref(false)
const errorMessage = ref('')
const editOpen = ref(false)
const modalTextSnapshot = ref<{ title: string; description: string } | null>(null)
let loadGen = 0

const draft = reactive<MetadataDraft>({
  title: '',
  description: '',
  ratingStars: 0,
  categoryName: null,
  tagNames: [],
  tagInput: '',
  pendingCoverPath: null,
})

function applyResourceToDraft(row: Resource): void {
  draft.title = row.title
  draft.description = row.description ?? ''
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
    (draft.categoryName ?? '') === (row.category?.name ?? '') &&
    savedTags === draftTags &&
    draft.tagInput.trim() === ''
  )
}

const dirty = computed(() => !snapshotEqualsSaved())

const typeLabel = computed(() => (resource.value?.type === 'video' ? '视频' : '图片'))

/** 图片主文件即封面，不提供更换封面；仅视频可换海报。 */
const canChangeCover = computed(() => resource.value?.type === 'video')

const sizeLabel = computed(() => {
  const files = resource.value?.files ?? []
  const primary = files.find((f) => f.role === 'primary') ?? files[0]
  return formatBytes(primary?.size)
})

const coverUrl = computed(() => resolveLibraryMediaUrl(resource.value?.coverPath))

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
    if (id === null) {
      resource.value = null
      return
    }
    try {
      const [row, cats] = await Promise.all([getResource(id), getCategories()])
      if (gen !== loadGen) return
      resource.value = row
      categories.value = cats
      applyResourceToDraft(row)
    } catch (error) {
      if (gen !== loadGen) return
      resource.value = null
      errorMessage.value = '加载详情失败'
      console.error(error)
    }
  },
  { immediate: true }
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
      ...(includeTextFields
        ? { title: draft.title, description: draft.description || null }
        : {}),
      rating: draft.ratingStars * 2,
      categoryName: draft.categoryName,
      tagNames: [...draft.tagNames],
    })
    resource.value = patched
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
  const paths = (await window.electron.selectFiles([IMAGE_FILTER])) ?? []
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
  const paths = (await window.electron.selectFiles([IMAGE_FILTER])) ?? []
  const path = paths[0]
  if (path) draft.pendingCoverPath = path
}

async function handleDelete(): Promise<void> {
  const id = selectedId.value
  const row = resource.value
  if (id === null || row === null) return
  deleting.value = true
  errorMessage.value = ''
  try {
    await deleteResource(id)
    library.bump(row.type)
    selection.clear()
  } catch (error) {
    errorMessage.value = '删除失败'
    console.error(error)
  } finally {
    deleting.value = false
  }
}
</script>

<style scoped lang="less">
.info-panel {
  width: 350px;
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
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.info-panel-body {
  flex: 1;
  min-height: 0;
  overflow: auto;
}

.info-panel-footer {
  flex-shrink: 0;
  padding-top: 12px;
  margin-top: 8px;
  border-top: 1px solid #e5e7eb;
  background: #fff;
}

.info-panel-empty {
  color: #6b7280;
}

.info-panel-cover {
  width: 100%;
  max-height: 180px;
  object-fit: contain;
}

.info-panel-title {
  font-weight: 600;
  margin: 8px 0;
}

.info-panel-meta,
.info-panel-label {
  font-size: 12px;
  color: #6b7280;
  margin-top: 8px;
}

.info-panel-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  margin-top: 4px;
}

.info-panel-error {
  color: #b91c1c;
  margin: 8px 0 0;
}

.info-panel-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
</style>
