import { BrowserWindow, dialog, ipcMain } from 'electron'
import { isAbsolute } from 'path'
import { promises as fs } from 'fs'

const MAX_THEME_CSS_BYTES = 262144

export type ThemeCssResult = { ok: true; css: string } | { ok: false; message: string }

export async function readThemeCssFile(filePath: unknown): Promise<ThemeCssResult> {
  if (typeof filePath !== 'string' || filePath.length === 0 || !isAbsolute(filePath)) {
    return { ok: false, message: '路径无效' }
  }
  if (!filePath.toLowerCase().endsWith('.css')) {
    return { ok: false, message: '仅支持 .css 文件' }
  }
  try {
    const stat = await fs.stat(filePath)
    if (!stat.isFile()) {
      return { ok: false, message: '不是文件' }
    }
    if (stat.size > MAX_THEME_CSS_BYTES) {
      return { ok: false, message: '主题文件超过 256KB' }
    }
    const raw = await fs.readFile(filePath, 'utf8')
    const css = raw.replace(/^\uFEFF/, '').trim()
    if (!css) {
      return { ok: false, message: '主题文件为空' }
    }
    return { ok: true, css }
  } catch {
    return { ok: false, message: '无法读取主题文件' }
  }
}

export function registerThemeCssIpc(): void {
  ipcMain.handle('dialog:selectThemeCss', async (): Promise<string | null> => {
    const options: Electron.OpenDialogOptions = {
      properties: ['openFile'],
      filters: [{ name: 'CSS', extensions: ['css'] }],
    }
    const win = BrowserWindow.getFocusedWindow() ?? BrowserWindow.getAllWindows()[0]
    const result = win
      ? await dialog.showOpenDialog(win, options)
      : await dialog.showOpenDialog(options)
    if (result.canceled || result.filePaths.length === 0) return null
    return result.filePaths[0] ?? null
  })
  ipcMain.handle('theme:readCss', async (_event, filePath: unknown): Promise<ThemeCssResult> => {
    return readThemeCssFile(filePath)
  })
}
