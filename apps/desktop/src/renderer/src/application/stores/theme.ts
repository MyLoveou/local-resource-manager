import { defineStore } from 'pinia'
import { ref } from 'vue'
import 'pinia-plugin-persistedstate' // 类型增强；pinia.use 在 main.ts
import { applyBuiltinTheme, applyUserThemeCss } from '@/ui/theme/applyTheme'

export type BuiltinThemeId = 'default' | 'dark'

export type ThemePack =
  | { kind: 'builtin'; id: BuiltinThemeId; builtinId: BuiltinThemeId }
  | { kind: 'file'; id: 'custom'; filePath: string }

function defaultPack(): ThemePack {
  return { kind: 'builtin', id: 'default', builtinId: 'default' }
}

export const useThemeStore = defineStore(
  'theme',
  () => {
    const pack = ref<ThemePack>(defaultPack())
    const revision = ref(0)
    const hydrateWarning = ref<string | null>(null)

    function bump(): void {
      revision.value += 1
    }

    function applyBuiltin(id: BuiltinThemeId): void {
      applyBuiltinTheme(id)
      pack.value = { kind: 'builtin', id, builtinId: id }
      hydrateWarning.value = null
      bump()
    }

    async function applyFile(filePath: string): Promise<string | null> {
      const api = window.electron
      if (!api?.readThemeCss) {
        return '无法读取主题文件'
      }
      const result = await api.readThemeCss(filePath)
      if (!result.ok) return result.message
      try {
        applyUserThemeCss(result.css)
      } catch {
        return '无法应用主题文件'
      }
      pack.value = { kind: 'file', id: 'custom', filePath }
      hydrateWarning.value = null
      bump()
      return null
    }

    async function pickFile(): Promise<string | null> {
      const api = window.electron
      if (!api?.selectThemeCss || !api.readThemeCss) {
        return '无法选择主题文件'
      }
      const filePath = await api.selectThemeCss()
      if (!filePath) return null
      return applyFile(filePath)
    }

    async function hydrate(): Promise<void> {
      try {
        const current = pack.value
        if (current.kind !== 'file') {
          applyBuiltinTheme(current.builtinId)
          bump()
          return
        }
        const error = await applyFile(current.filePath)
        if (error) {
          applyBuiltin('default')
          hydrateWarning.value = error
        }
      } catch {
        applyBuiltin('default')
        hydrateWarning.value = '无法读取主题文件'
      }
    }

    function consumeHydrateWarning(): string | null {
      const text = hydrateWarning.value
      hydrateWarning.value = null
      return text
    }

    return { pack, revision, hydrateWarning, applyBuiltin, pickFile, hydrate, consumeHydrateWarning }
  },
  {
    persist: {
      pick: ['pack'],
    },
  }
)
