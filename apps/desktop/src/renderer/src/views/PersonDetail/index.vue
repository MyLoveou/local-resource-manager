<template>
  <div v-if="person" class="person-detail">
    <header class="person-detail__head">
      <img v-if="person.coverPath" class="person-detail__cover" :src="resolveLibraryMediaUrl(person.coverPath)" alt="" />
      <div class="person-detail__identity">
        <h2>{{ person.name }}</h2>
        <p v-if="person.aliases.length">别名：{{ person.aliases.join('、') }}</p>
        <p v-if="person.description" class="person-detail__description">{{ person.description }}</p>
        <span class="person-detail__count">{{ person.resourceCount }} 项资源</span>
      </div>
      <div class="person-detail__actions">
        <n-button size="small" @click="editOpen = true">编辑</n-button>
        <n-button size="small" @click="mergeOpen = true">合并</n-button>
        <n-popconfirm positive-text="删除" negative-text="取消" @positive-click="remove">
          <template #trigger>
            <n-button size="small" type="error" ghost>删除</n-button>
          </template>
          删除扮演者不会删除资源。
        </n-popconfirm>
        <n-button size="small" @click="router.push('/persons')">返回</n-button>
      </div>
    </header>

    <div v-if="characters.length" class="person-detail__characters">
      <span>相关角色：</span>
      <button
        v-for="character in characters"
        :key="character.id"
        type="button"
        class="person-detail__character"
        @click="router.push(`/characters/${character.id}`)"
      >
        {{ character.name }}
      </button>
    </div>

    <div class="person-detail__body">
      <PhotoTimeline
        :key="`${person.id}-${layout}`"
        :person-ids="[person.id]"
        scope="media"
        :layout="layout"
        hide-filters
      />
    </div>

    <PersonEditorModal v-model:show="editOpen" :person="person" @saved="onSaved" />

    <n-modal v-model:show="mergeOpen" preset="card" title="合并扮演者" style="width: 440px">
      <p class="person-detail__merge-hint">将另一个扮演者合并到「{{ person.name }}」，资源关联和别名会转移。</p>
      <n-select
        v-model:value="mergeSourceId"
        filterable
        placeholder="选择要合并的扮演者"
        :options="mergeOptions"
      />
      <template #footer>
        <div class="person-detail__merge-actions">
          <n-button @click="mergeOpen = false">取消</n-button>
          <n-button type="primary" :disabled="mergeSourceId === null" @click="merge">合并</n-button>
        </div>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NButton, NPopconfirm, NModal, NSelect } from 'naive-ui'
import PersonEditorModal from '@/components/PersonEditorModal/index.vue'
import PhotoTimeline from '@/components/PhotoTimeline/index.vue'
import { notify } from '@/application/notify'
import {
  deletePerson,
  getPerson,
  getPersonCharacters,
  listPersons,
  mergePerson,
  resolveLibraryMediaUrl,
} from '@/infrastructure/http'
import type { CharacterBrief, Person } from '@/domain'

const route = useRoute()
const router = useRouter()
const person = ref<Person | null>(null)
const characters = ref<CharacterBrief[]>([])
const allPersons = ref<Person[]>([])
const layout = ref<'stream' | 'grid'>('grid')
const editOpen = ref(false)
const mergeOpen = ref(false)
const mergeSourceId = ref<number | null>(null)

const mergeOptions = computed(() =>
  allPersons.value
    .filter((item) => item.id !== person.value?.id)
    .map((item) => ({ label: item.name, value: item.id })),
)

async function load(): Promise<void> {
  const id = Number(route.params.id)
  if (!Number.isFinite(id)) {
    void router.replace('/persons')
    return
  }
  try {
    const [detail, roles, options] = await Promise.all([
      getPerson(id),
      getPersonCharacters(id),
      listPersons(),
    ])
    person.value = detail
    characters.value = roles
    allPersons.value = options
  } catch (error) {
    notify.fromError(error, { context: '读取扮演者' })
    void router.replace('/persons')
  }
}

function onSaved(next: Person): void {
  person.value = next
  void load()
}

async function remove(): Promise<void> {
  if (!person.value) return
  try {
    await deletePerson(person.value.id)
    notify.toast.success('扮演者已删除')
    void router.push('/persons')
  } catch (error) {
    notify.fromError(error, { context: '删除扮演者' })
  }
}

async function merge(): Promise<void> {
  if (!person.value || mergeSourceId.value === null) return
  try {
    person.value = await mergePerson(person.value.id, mergeSourceId.value)
    mergeOpen.value = false
    mergeSourceId.value = null
    await load()
    notify.toast.success('扮演者已合并')
  } catch (error) {
    notify.fromError(error, { context: '合并扮演者' })
  }
}

watch(() => route.params.id, () => void load())
onMounted(() => void load())
</script>

<style scoped lang="less">
.person-detail {
  height: 100%;
  overflow: auto;
  padding: 20px;
}

.person-detail__head {
  display: flex;
  align-items: flex-start;
  gap: 16px;
}

.person-detail__cover {
  width: 112px;
  height: 112px;
  object-fit: cover;
  border-radius: 12px;
  background: var(--sm-color-bg-muted, #f1f1f1);
}

.person-detail__identity {
  flex: 1;
  min-width: 0;

  h2 { margin: 0; font-size: 20px; }
  p { margin: 5px 0 0; color: var(--sm-color-text-muted); font-size: 12px; }
}

.person-detail__description { max-width: 760px; line-height: 1.6; white-space: pre-wrap; }
.person-detail__count { display: inline-block; margin-top: 8px; color: var(--sm-color-text-muted); font-size: 11px; }
.person-detail__actions { display: flex; flex-wrap: wrap; gap: 8px; }

.person-detail__characters {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin-top: 14px;
  color: var(--sm-color-text-muted);
  font-size: 12px;
}

.person-detail__character {
  padding: 3px 9px;
  border: 1px solid var(--sm-color-border);
  border-radius: 999px;
  background: transparent;
  color: var(--sm-color-text);
  cursor: pointer;
}

.person-detail__body { height: min(680px, 72vh); min-height: 360px; margin-top: 14px; }
.person-detail__merge-hint { color: var(--sm-color-text-muted); font-size: 12px; line-height: 1.6; }
.person-detail__merge-actions { display: flex; justify-content: flex-end; gap: 8px; }
</style>
