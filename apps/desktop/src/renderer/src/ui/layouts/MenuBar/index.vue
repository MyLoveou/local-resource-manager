<template>
  <nav class="menu-bar" :class="{ collapsed }">
    <n-menu :options="menuOptions" :value="activeKey" :collapsed="collapsed" :collapsed-width="64"
      :collapsed-icon-size="22" @update:value="onSelect" />
  </nav>
</template>

<script setup lang="ts">
import { computed, h } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { NMenu, type MenuOption } from 'naive-ui'
import { Icon } from '@iconify/vue'
import type { MenuItem } from '@/domain/menu'

const props = defineProps<{
  items: MenuItem[]
  collapsed?: boolean
}>()

const route = useRoute()
const router = useRouter()

const activeKey = computed(() => route.path)

const menuOptions = computed<MenuOption[]>(() => props.items.map(toMenuOption))
console.log(menuOptions.value)

function toMenuOption(item: MenuItem): MenuOption {
  return {
    key: item.key,
    label: item.label,
    disabled: item.disabled,
    icon: item.icon ? () => h(Icon, { icon: `mdi:${item.icon}` }) : undefined,
    children: item.children?.map(toMenuOption),
  }
}

function onSelect(key: string): void {
  if (key.startsWith('/')) router.push(key)
}
</script>

<style scoped lang="less">
@import '@/ui/styles/variables.less';

.menu-bar {
  width: 200px;
  height: 100%;
  border-right: 1px solid @border;
  box-sizing: border-box;
  overflow: hidden;
  transition: width 0.2s ease;

  &.collapsed {
    width: 64px;
  }
}
</style>
