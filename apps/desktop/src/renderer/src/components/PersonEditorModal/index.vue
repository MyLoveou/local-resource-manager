<template>
  <n-modal
    :show="show"
    preset="card"
    :title="person ? '编辑扮演者' : '新建扮演者'"
    style="width: 560px"
    :mask-closable="!busy"
    @update:show="(value: boolean) => $emit('update:show', value)"
  >
    <div class="person-editor">
      <n-input v-model:value="name" placeholder="扮演者名称" />
      <n-input v-model:value="aliasesText" placeholder="别名，用逗号分隔" />
      <n-input
        v-model:value="description"
        type="textarea"
        :autosize="{ minRows: 3, maxRows: 8 }"
        placeholder="简介"
      />
      <n-select
        v-if="person && coverOptions.length"
        v-model:value="coverResourceId"
        clearable
        filterable
        placeholder="封面（可选，默认取最近关联资源）"
        :options="coverOptions"
      />
      <div class="person-editor__actions">
        <n-button :disabled="busy" @click="$emit('update:show', false)">取消</n-button>
        <n-button type="primary" :loading="busy" :disabled="!name.trim()" @click="save">
          保存
        </n-button>
      </div>
    </div>
  </n-modal>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { NButton, NInput, NModal, NSelect } from 'naive-ui'
import { notify } from '@/application/notify'
import { createPerson, getResources, patchPerson } from '@/infrastructure/http'
import type { Person } from '@/domain'

const props = defineProps<{
  show: boolean
  person?: Person | null
}>()
const emit = defineEmits<{
  'update:show': [value: boolean]
  saved: [person: Person]
}>()

const name = ref('')
const aliasesText = ref('')
const description = ref('')
const coverResourceId = ref<number | null>(null)
const coverOptions = ref<{ label: string; value: number }[]>([])
const busy = ref(false)
const person = computed(() => props.person ?? null)

function splitAliases(value: string): string[] {
  return value.split(/[,，、]/).map((item) => item.trim()).filter(Boolean)
}

function reset(): void {
  const current = props.person
  name.value = current?.name ?? ''
  aliasesText.value = (current?.aliases ?? []).join(', ')
  description.value = current?.description ?? ''
  coverResourceId.value = current?.coverResourceId ?? null
}

async function loadCoverOptions(): Promise<void> {
  if (!props.person?.id) {
    coverOptions.value = []
    return
  }
  try {
    const page = await getResources({
      personIds: [props.person.id],
      status: 'active',
      limit: 80,
    })
    coverOptions.value = page.items.flatMap((item) =>
      item.id === undefined ? [] : [{ label: item.title || `资源 ${item.id}`, value: item.id }],
    )
  } catch {
    coverOptions.value = []
  }
}

async function save(): Promise<void> {
  const title = name.value.trim()
  if (!title) return
  busy.value = true
  try {
    const body = {
      name: title,
      description: description.value.trim() || null,
      coverResourceId: coverResourceId.value,
      aliases: splitAliases(aliasesText.value),
    }
    const saved = props.person
      ? await patchPerson(props.person.id, body)
      : await createPerson(body)
    notify.toast.success(props.person ? '扮演者已保存' : '扮演者已创建')
    emit('saved', saved)
    emit('update:show', false)
  } catch (error) {
    notify.fromError(error, { context: '保存扮演者' })
  } finally {
    busy.value = false
  }
}

watch(
  () => props.show,
  async (show) => {
    if (!show) return
    reset()
    await loadCoverOptions()
  },
)
</script>

<style scoped lang="less">
.person-editor {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.person-editor__actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding-top: 4px;
}
</style>
