<template>
  <section v-if="active.length" class="home__section">
    <div class="home__section-head">
      <h2>进行中 {{ active.length }}</h2>
      <button type="button" class="home__more" @click="load">刷新</button>
    </div>
    <ul class="home-tasks">
      <li v-for="task in active" :key="task.id" class="home-tasks__row">
        <span class="home-tasks__kind">{{ taskKindLabel(task.kind) }}</span>
        <span class="home-tasks__title" :title="task.title">{{ task.title }}</span>
        <n-progress
          class="home-tasks__bar"
          type="line"
          :percentage="Math.round(task.percent)"
          :show-indicator="false"
          :height="6"
        />
        <span class="home-tasks__percent">{{ Math.round(task.percent) }}%</span>
        <n-button size="tiny" :disabled="busyId === task.id" @click="cancel(task.id)">取消</n-button>
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { NButton, NProgress } from 'naive-ui'
import { cancelTask, listTasks, taskKindLabel, type TaskItem } from '@/infrastructure/http/tasks'
import { notify } from '@/application/notify'

const active = ref<TaskItem[]>([])
const busyId = ref('')
let timer: number | null = null

async function load(): Promise<void> {
  try {
    active.value = await listTasks({ active: true })
  } catch {
    active.value = []
  }
}

async function cancel(id: string): Promise<void> {
  busyId.value = id
  try {
    await cancelTask(id)
    notify.toast.success('已请求取消')
    await load()
  } catch {
    notify.toast.error('取消失败')
  } finally {
    busyId.value = ''
  }
}

onMounted(() => {
  void load()
  timer = window.setInterval(load, 2000)
})

onBeforeUnmount(() => {
  if (timer !== null) window.clearInterval(timer)
})
</script>

<style scoped lang="less">
.home-tasks {
  margin: 0;
  padding: 0;
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.home-tasks__row {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
}

.home-tasks__kind {
  flex-shrink: 0;
  padding: 0 6px;
  border-radius: 999px;
  background: var(--sm-color-bg-muted, #eee);
}

.home-tasks__title {
  flex: 1;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.home-tasks__bar {
  width: 160px;
  flex-shrink: 0;
}

.home-tasks__percent {
  width: 36px;
  text-align: right;
  color: var(--sm-color-text-muted, #6b7280);
}
</style>
