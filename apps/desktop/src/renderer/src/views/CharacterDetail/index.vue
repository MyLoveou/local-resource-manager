<template>
  <div v-if="character" class="character-detail">
    <header class="character-detail__head">
      <img
        v-if="character.coverPath"
        class="character-detail__cover"
        :src="resolveLibraryMediaUrl(character.coverPath)"
        alt=""
      />
      <div class="character-detail__identity">
        <h2>{{ character.name }}</h2>
        <p v-if="character.workName">作品：{{ character.workName }}</p>
        <p v-if="character.aliases.length">别名：{{ character.aliases.join('、') }}</p>
        <p v-if="character.description" class="character-detail__description">
          {{ character.description }}
        </p>
        <span class="character-detail__count">{{ character.resourceCount }} 项资源</span>
      </div>
      <div class="character-detail__actions">
        <n-button size="small" @click="editOpen = true">编辑</n-button>
        <n-button size="small" @click="mergeOpen = true">合并</n-button>
        <n-popconfirm
          positive-text="删除"
          negative-text="取消"
          @positive-click="remove"
        >
          <template #trigger>
            <n-button size="small" type="error" ghost>删除</n-button>
          </template>
          删除角色不会删除资源。
        </n-popconfirm>
        <n-button size="small" @click="router.push('/characters')">返回</n-button>
      </div>
    </header>

    <div class="character-detail__bar">
      <n-button-group size="small">
        <n-button :type="layout === 'stream' ? 'primary' : 'default'" @click="layout = 'stream'">
          时间线
        </n-button>
        <n-button :type="layout === 'grid' ? 'primary' : 'default'" @click="layout = 'grid'">
          网格
        </n-button>
      </n-button-group>
    </div>

    <div class="character-detail__body">
      <PhotoTimeline
        :key="`${character.id}-${layout}`"
        :character-ids="[character.id]"
        scope="media"
        :layout="layout"
        hide-filters
      />
    </div>

    <section v-if="collections.length" class="character-detail__collections">
      <h3>所在合集</h3>
      <div class="character-detail__collection-grid">
        <CollectionCard
          v-for="collection in collections"
          :key="collection.id"
          :title="collection.title"
          :member-count="collection.memberCount"
          :previews="collection.previewThumbnails ?? []"
          @open="router.push(`/collections/${collection.id}`)"
        />
      </div>
    </section>

    <CharacterEditorModal
      v-model:show="editOpen"
      :character="character"
      @saved="onSaved"
    />

    <n-modal
      v-model:show="mergeOpen"
      preset="card"
      title="合并角色"
      style="width: 440px"
    >
      <p class="character-detail__merge-hint">
        将另一个角色合并到「{{ character.name }}」，资源关联和别名会转移，来源角色删除。
      </p>
      <n-select
        v-model:value="mergeSourceId"
        filterable
        placeholder="选择要合并的角色"
        :options="mergeOptions"
      />
      <template #footer>
        <div class="character-detail__merge-actions">
          <n-button @click="mergeOpen = false">取消</n-button>
          <n-button type="primary" :disabled="mergeSourceId === null" @click="merge">
            合并
          </n-button>
        </div>
      </template>
    </n-modal>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NButton, NButtonGroup, NModal, NPopconfirm, NSelect } from 'naive-ui'
import CharacterEditorModal from '@/components/CharacterEditorModal/index.vue'
import CollectionCard from '@/components/CollectionCard/index.vue'
import PhotoTimeline from '@/components/PhotoTimeline/index.vue'
import { notify } from '@/application/notify'
import {
  deleteCharacter,
  getCharacter,
  getCharacterCollections,
  listCharacters,
  mergeCharacter,
  resolveLibraryMediaUrl,
} from '@/infrastructure/http'
import type { Character, Collection } from '@/domain'

const route = useRoute()
const router = useRouter()
const character = ref<Character | null>(null)
const collections = ref<Collection[]>([])
const allCharacters = ref<Character[]>([])
const layout = ref<'stream' | 'grid'>('grid')
const editOpen = ref(false)
const mergeOpen = ref(false)
const mergeSourceId = ref<number | null>(null)

const mergeOptions = computed(() =>
  allCharacters.value
    .filter((item) => item.id !== character.value?.id)
    .map((item) => ({
      label: item.workName ? `${item.name} · ${item.workName}` : item.name,
      value: item.id,
    })),
)

async function load(): Promise<void> {
  const id = Number(route.params.id)
  if (!Number.isFinite(id)) {
    void router.replace('/characters')
    return
  }
  try {
    const [detail, cards, options] = await Promise.all([
      getCharacter(id),
      getCharacterCollections(id),
      listCharacters(),
    ])
    character.value = detail
    collections.value = cards
    allCharacters.value = options
  } catch (error) {
    notify.fromError(error, { context: '读取角色' })
    void router.replace('/characters')
  }
}

function onSaved(next: Character): void {
  character.value = next
  void load()
}

async function remove(): Promise<void> {
  if (!character.value) return
  try {
    await deleteCharacter(character.value.id)
    notify.toast.success('角色已删除')
    void router.push('/characters')
  } catch (error) {
    notify.fromError(error, { context: '删除角色' })
  }
}

async function merge(): Promise<void> {
  if (!character.value || mergeSourceId.value === null) return
  try {
    const merged = await mergeCharacter(character.value.id, mergeSourceId.value)
    character.value = merged
    mergeOpen.value = false
    mergeSourceId.value = null
    await load()
    notify.toast.success('角色已合并')
  } catch (error) {
    notify.fromError(error, { context: '合并角色' })
  }
}

watch(() => route.params.id, () => void load())

onMounted(() => {
  void load()
})
</script>

<style scoped lang="less">
.character-detail {
  height: 100%;
  overflow: auto;
  padding: 20px;
}

.character-detail__head {
  display: flex;
  align-items: flex-start;
  gap: 16px;
}

.character-detail__cover {
  width: 112px;
  height: 112px;
  object-fit: cover;
  border-radius: 12px;
  background: var(--sm-color-bg-muted, #f1f1f1);
}

.character-detail__identity {
  flex: 1;
  min-width: 0;

  h2 {
    margin: 0;
    font-size: 20px;
  }

  p {
    margin: 5px 0 0;
    color: var(--sm-color-text-muted);
    font-size: 12px;
  }
}

.character-detail__description {
  max-width: 760px;
  line-height: 1.6;
  white-space: pre-wrap;
}

.character-detail__count {
  display: inline-block;
  margin-top: 8px;
  color: var(--sm-color-text-muted);
  font-size: 11px;
}

.character-detail__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.character-detail__bar {
  display: flex;
  justify-content: flex-end;
  padding: 16px 0 8px;
}

.character-detail__body {
  height: min(680px, 72vh);
  min-height: 360px;
}

.character-detail__collections {
  margin-top: 24px;

  h3 {
    margin: 0 0 10px;
    font-size: 14px;
  }
}

.character-detail__collection-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 12px;
}

.character-detail__merge-hint {
  color: var(--sm-color-text-muted);
  font-size: 12px;
  line-height: 1.6;
}

.character-detail__merge-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
</style>
