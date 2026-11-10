<template>
  <n-modal
    :show="show"
    preset="card"
    :title="character ? '编辑角色' : '新建角色'"
    style="width: 560px"
    :mask-closable="!busy"
    @update:show="(value: boolean) => $emit('update:show', value)"
  >
    <div class="character-editor">
      <n-input v-model:value="name" placeholder="角色名" />
      <n-input v-model:value="workName" placeholder="所属作品（可新建）" />
      <n-input
        v-model:value="aliasesText"
        placeholder="别名，用逗号分隔"
      />
      <n-input
        v-model:value="description"
        type="textarea"
        :autosize="{ minRows: 3, maxRows: 8 }"
        placeholder="简介"
      />
      <n-select
        v-if="character && coverOptions.length"
        v-model:value="coverResourceId"
        clearable
        filterable
        placeholder="封面（可选，默认取最近关联资源）"
        :options="coverOptions"
      />
      <p v-if="!character" class="character-editor__hint">
        封面会默认使用该角色最近关联的图片；关联资源后可在编辑中选择封面。
      </p>
      <div class="character-editor__actions">
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
import {
  createCharacter,
  getResources,
  patchCharacter,
} from '@/infrastructure/http'
import type { Character, Resource } from '@/domain'

const props = defineProps<{
  show: boolean
  character?: Character | null
}>()
const emit = defineEmits<{
  'update:show': [value: boolean]
  saved: [character: Character]
}>()

const name = ref('')
const workName = ref('')
const aliasesText = ref('')
const description = ref('')
const coverResourceId = ref<number | null>(null)
const coverOptions = ref<{ label: string; value: number }[]>([])
const busy = ref(false)

const character = computed(() => props.character ?? null)

function splitAliases(value: string): string[] {
  return value
    .split(/[,，、]/)
    .map((item) => item.trim())
    .filter(Boolean)
}

function reset(): void {
  const current = props.character
  name.value = current?.name ?? ''
  workName.value = current?.workName ?? ''
  aliasesText.value = (current?.aliases ?? []).join(', ')
  description.value = current?.description ?? ''
  coverResourceId.value = current?.coverResourceId ?? null
}

async function loadCoverOptions(): Promise<void> {
  if (!props.character?.id) {
    coverOptions.value = []
    return
  }
  try {
    const page = await getResources({
      characterIds: [props.character.id],
      status: 'active',
      limit: 80,
    })
    coverOptions.value = page.items.flatMap((item: Resource) =>
      item.id === undefined
        ? []
        : [{ label: item.title || `资源 ${item.id}`, value: item.id }],
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
      workName: workName.value.trim() || null,
      description: description.value.trim() || null,
      coverResourceId: coverResourceId.value,
      aliases: splitAliases(aliasesText.value),
    }
    const saved = props.character
      ? await patchCharacter(props.character.id, body)
      : await createCharacter(body)
    notify.toast.success(props.character ? '角色已保存' : '角色已创建')
    emit('saved', saved)
    emit('update:show', false)
  } catch (error) {
    notify.fromError(error, { context: '保存角色' })
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
.character-editor {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.character-editor__hint {
  margin: 0;
  color: var(--sm-color-text-muted);
  font-size: 11px;
}

.character-editor__actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding-top: 4px;
}
</style>
