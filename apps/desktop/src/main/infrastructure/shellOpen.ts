/**
 * 用系统资源管理器定位文件，或用默认/其他应用打开。路径必须是已存在的本地文件。
 */
import { execFile } from 'node:child_process'
import { promisify } from 'node:util'
import { BrowserWindow, dialog, ipcMain, shell } from 'electron'
import { resolveExistingFile } from './existingFile'

const execFileAsync = promisify(execFile)

export type ShellOpenResult =
  | { ok: true; canceled?: boolean }
  | { ok: false; message: string }

function fail(message: string): ShellOpenResult {
  return { ok: false, message }
}

function ok(canceled = false): ShellOpenResult {
  return canceled ? { ok: true, canceled: true } : { ok: true }
}

function parsePath(raw: unknown): string {
  if (raw !== null && typeof raw === 'object' && 'path' in raw) {
    return resolveExistingFile((raw as { path: unknown }).path)
  }
  return resolveExistingFile(raw)
}

async function openWithOther(filePath: string): Promise<ShellOpenResult> {
  const win = BrowserWindow.getFocusedWindow() ?? BrowserWindow.getAllWindows()[0]
  if (process.platform === 'win32') {
    await execFileAsync('rundll32.exe', ['shell32.dll,OpenAs_RunDLL', filePath])
    return ok()
  }
  if (process.platform === 'darwin') {
    const result = win
      ? await dialog.showOpenDialog(win, {
          properties: ['openFile'],
          defaultPath: '/Applications',
          filters: [{ name: 'Applications', extensions: ['app'] }],
        })
      : await dialog.showOpenDialog({
          properties: ['openFile'],
          defaultPath: '/Applications',
          filters: [{ name: 'Applications', extensions: ['app'] }],
        })
    if (result.canceled || result.filePaths.length === 0) return ok(true)
    await execFileAsync('open', ['-a', result.filePaths[0], filePath])
    return ok()
  }
  const result = win
    ? await dialog.showOpenDialog(win, { properties: ['openFile'] })
    : await dialog.showOpenDialog({ properties: ['openFile'] })
  if (result.canceled || result.filePaths.length === 0) return ok(true)
  await execFileAsync(result.filePaths[0], [filePath], { windowsHide: true })
  return ok()
}

export function registerShellOpenIpc(): void {
  ipcMain.handle('shell:showItemInFolder', async (_event, payload: unknown): Promise<ShellOpenResult> => {
    try {
      shell.showItemInFolder(parsePath(payload))
      return ok()
    } catch (err) {
      return fail(err instanceof Error ? err.message : 'showItemInFolder failed')
    }
  })

  ipcMain.handle('shell:openPath', async (_event, payload: unknown): Promise<ShellOpenResult> => {
    try {
      const message = await shell.openPath(parsePath(payload))
      return message ? fail(message) : ok()
    } catch (err) {
      return fail(err instanceof Error ? err.message : 'openPath failed')
    }
  })

  ipcMain.handle('shell:openWith', async (_event, payload: unknown): Promise<ShellOpenResult> => {
    try {
      return await openWithOther(parsePath(payload))
    } catch (err) {
      return fail(err instanceof Error ? err.message : 'openWith failed')
    }
  })
}
