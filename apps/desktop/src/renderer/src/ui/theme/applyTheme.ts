import type { GlobalThemeOverrides } from 'naive-ui'

const USER_THEME_STYLE_ID = 'sm-user-theme'

function token(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim()
}

export function applyBuiltinTheme(id: 'default' | 'dark'): void {
  document.getElementById(USER_THEME_STYLE_ID)?.remove()
  document.documentElement.dataset.theme = id
}

export function applyUserThemeCss(css: string): void {
  const prevTheme = document.documentElement.dataset.theme
  const existing = document.getElementById(USER_THEME_STYLE_ID) as HTMLStyleElement | null
  const prevCss = existing?.textContent ?? null
  try {
    document.documentElement.dataset.theme = 'custom'
    let el = existing
    if (!el) {
      el = document.createElement('style')
      el.id = USER_THEME_STYLE_ID
      document.head.appendChild(el)
    }
    el.textContent = css
  } catch (error) {
    if (prevTheme) document.documentElement.dataset.theme = prevTheme
    else delete document.documentElement.dataset.theme
    const el = document.getElementById(USER_THEME_STYLE_ID)
    if (prevCss == null) {
      el?.remove()
    } else if (el) {
      el.textContent = prevCss
    }
    throw error
  }
}

export function readNaiveOverrides(): GlobalThemeOverrides {
  const primary = token('--sm-color-primary')
  const text = token('--sm-color-text')
  const page = token('--sm-color-bg-page')
  const surface = token('--sm-color-bg-surface')
  const border = token('--sm-color-border')
  const radius = Number.parseFloat(token('--sm-radius-control')) || 6
  return {
    common: {
      primaryColor: primary,
      primaryColorHover: primary,
      primaryColorPressed: primary,
      textColorBase: text,
      bodyColor: page,
      cardColor: surface,
      modalColor: surface,
      popoverColor: surface,
      borderColor: border,
      borderRadius: `${radius}px`,
    },
  }
}
