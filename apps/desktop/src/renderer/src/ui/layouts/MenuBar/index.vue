<template>
  <nav
    class="menu-bar"
    :class="{ collapsed }"
  >
    <n-menu
      :options="menuOptions"
      :value="activeKey"
      :collapsed="collapsed"
      :collapsed-width="64"
      :collapsed-icon-size="22"
      @update:value="onSelect"
    />
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

const activeKey = computed(() => {
  if (route.path.startsWith('/library/')) return '/library'
  if (route.path.startsWith('/collections/')) return '/collections'
  if (route.path.startsWith('/timelines/')) return '/timelines'
  return route.path
})

const menuOptions = computed<MenuOption[]>(() => props.items.map(toMenuOption))

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
.menu-bar {
  flex: 0 0 200px;
  width: 200px;
  max-width: 200px;
  min-width: 0;
  height: 100%;
  background: var(--sm-color-bg-surface);
  border-right: 1px solid var(--sm-color-border);
  box-sizing: border-box;
  overflow: hidden;
  transition: width 0.2s ease;

  &.collapsed {
    flex-basis: 64px;
    width: 64px;
    max-width: 64px;
  }
}
</style>
