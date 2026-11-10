<template>
  <div class="persons">
    <div class="persons__head">
      <h2>扮演者</h2>
      <n-button size="small" type="primary" @click="editorOpen = true">新建扮演者</n-button>
    </div>
    <p class="persons__hint">现实中的 coser/出镜者；角色与扮演者是不同维度。</p>
    <div class="persons__toolbar">
      <n-input v-model:value="q" size="small" clearable placeholder="搜索扮演者 / 别名" @update:value="load" />
    </div>
    <div v-if="loading" class="persons__empty">加载中…</div>
    <div v-else-if="persons.length === 0" class="persons__empty">还没有扮演者</div>
    <div v-else class="persons__grid">
      <button
        v-for="person in persons"
        :key="person.id"
        type="button"
        class="persons__card"
        @click="router.push(`/persons/${person.id}`)"
      >
        <span class="persons__cover">
          <img v-if="person.coverPath" :src="resolveLibraryMediaUrl(person.coverPath)" alt="" loading="lazy" />
          <span v-else class="persons__placeholder">{{ person.name.slice(0, 1) }}</span>
        </span>
        <span class="persons__body">
          <strong>{{ person.name }}</strong>
          <span>{{ person.resourceCount }} 项资源</span>
        </span>
      </button>
    </div>
    <PersonEditorModal v-model:show="editorOpen" @saved="load" />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { NButton, NInput } from 'naive-ui'
import PersonEditorModal from '@/components/PersonEditorModal/index.vue'
import { notify } from '@/application/notify'
import { listPersons, resolveLibraryMediaUrl } from '@/infrastructure/http'
import type { Person } from '@/domain'

const router = useRouter()
const persons = ref<Person[]>([])
const q = ref('')
const loading = ref(false)
const editorOpen = ref(false)

async function load(): Promise<void> {
  loading.value = true
  try {
    persons.value = await listPersons(q.value.trim() || undefined)
  } catch (error) {
    notify.fromError(error, { context: '读取扮演者' })
  } finally {
    loading.value = false
  }
}

onMounted(() => void load())
</script>

<style scoped lang="less">
.persons {
  height: 100%;
  overflow: auto;
  padding: 20px;
}

.persons__head {
  display: flex;
  align-items: center;
  justify-content: space-between;

  h2 { margin: 0; font-size: 18px; }
}

.persons__hint {
  margin: 8px 0 12px;
  color: var(--sm-color-text-muted);
  font-size: 12px;
}

.persons__toolbar {
  width: min(320px, 100%);
  margin-bottom: 14px;
}

.persons__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
  gap: 12px;
}

.persons__card {
  display: flex;
  gap: 10px;
  padding: 8px;
  border: 1px solid var(--sm-color-border);
  border-radius: 12px;
  background: var(--sm-color-bg-surface);
  color: var(--sm-color-text);
  cursor: pointer;
  text-align: left;

  &:hover { border-color: var(--sm-color-primary); }
}

.persons__cover {
  flex: 0 0 72px;
  width: 72px;
  height: 72px;
  overflow: hidden;
  border-radius: 8px;
  background: var(--sm-color-bg-muted, #f1f1f1);

  img { width: 100%; height: 100%; object-fit: cover; }
}

.persons__placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  color: var(--sm-color-text-muted);
  font-size: 24px;
}

.persons__body {
  display: flex;
  min-width: 0;
  flex-direction: column;
  justify-content: center;
  gap: 3px;

  strong, span {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  strong { font-size: 14px; }
  span { color: var(--sm-color-text-muted); font-size: 11px; }
}

.persons__empty {
  padding: 20px;
  color: var(--sm-color-text-muted);
  font-size: 13px;
}
</style>
