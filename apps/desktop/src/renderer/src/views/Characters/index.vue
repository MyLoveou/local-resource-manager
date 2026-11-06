<template>
  <div class="characters">
    <div class="characters__head">
      <h2>角色</h2>
      <n-button size="small" type="primary" @click="editorOpen = true">新建角色</n-button>
    </div>
    <p class="characters__hint">按角色、作品整理 cosplay 与图片；扮演者暂用标签过渡。</p>
    <div class="characters__toolbar">
      <n-input
        v-model:value="q"
        size="small"
        clearable
        placeholder="搜索角色 / 别名"
        @update:value="load"
      />
    </div>
    <div v-if="loading" class="characters__empty">加载中…</div>
    <div v-else-if="characters.length === 0" class="characters__empty">还没有角色</div>
    <div v-else class="characters__grid">
      <button
        v-for="character in characters"
        :key="character.id"
        type="button"
        class="characters__card"
        @click="router.push(`/characters/${character.id}`)"
      >
        <span class="characters__cover">
          <img
            v-if="character.coverPath"
            :src="resolveLibraryMediaUrl(character.coverPath)"
            alt=""
            loading="lazy"
          />
          <span v-else class="characters__placeholder">{{ character.name.slice(0, 1) }}</span>
        </span>
        <span class="characters__body">
          <strong>{{ character.name }}</strong>
          <span>{{ character.workName || '未指定作品' }}</span>
          <span>{{ character.resourceCount }} 项资源</span>
        </span>
      </button>
    </div>
    <CharacterEditorModal v-model:show="editorOpen" @saved="load" />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NInput } from 'naive-ui'
import CharacterEditorModal from '@/components/CharacterEditorModal/index.vue'
import { notify } from '@/application/notify'
import { listCharacters, resolveLibraryMediaUrl } from '@/infrastructure/http'
import type { Character } from '@/domain'

const router = useRouter()
const characters = ref<Character[]>([])
const q = ref('')
const loading = ref(false)
const editorOpen = ref(false)

async function load(): Promise<void> {
  loading.value = true
  try {
    characters.value = await listCharacters(q.value.trim() || undefined)
  } catch (error) {
    notify.fromError(error, { context: '读取角色' })
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  void load()
})
</script>

<style scoped lang="less">
.characters {
  height: 100%;
  overflow: auto;
  padding: 20px;
}

.characters__head {
  display: flex;
  align-items: center;
  justify-content: space-between;

  h2 {
    margin: 0;
    font-size: 18px;
  }
}

.characters__hint {
  margin: 8px 0 12px;
  color: var(--sm-color-text-muted);
  font-size: 12px;
}

.characters__toolbar {
  width: min(320px, 100%);
  margin-bottom: 14px;
}

.characters__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
  gap: 12px;
}

.characters__card {
  display: flex;
  gap: 10px;
  min-width: 0;
  padding: 8px;
  border: 1px solid var(--sm-color-border);
  border-radius: 12px;
  background: var(--sm-color-bg-surface);
  color: var(--sm-color-text);
  cursor: pointer;
  text-align: left;

  &:hover {
    border-color: var(--sm-color-primary);
  }
}

.characters__cover {
  flex: 0 0 72px;
  width: 72px;
  height: 72px;
  overflow: hidden;
  border-radius: 8px;
  background: var(--sm-color-bg-muted, #f1f1f1);

  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
}

.characters__placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  color: var(--sm-color-text-muted);
  font-size: 24px;
}

.characters__body {
  display: flex;
  min-width: 0;
  flex-direction: column;
  justify-content: center;
  gap: 3px;

  strong,
  span {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  strong {
    font-size: 14px;
  }

  span {
    color: var(--sm-color-text-muted);
    font-size: 11px;
  }
}

.characters__empty {
  padding: 20px;
  color: var(--sm-color-text-muted);
  font-size: 13px;
}
</style>
