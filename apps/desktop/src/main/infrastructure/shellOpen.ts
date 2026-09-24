/**
 * 用系统资源管理器定位文件，或用默认/其他应用打开。路径必须是已存在的本地文件。
 */
import { execFile, spawn } from 'node:child_process'
import { existsSync, statSync } from 'node:fs'
import path from 'node:path'
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

function resolveExistingTarget(raw: unknown): string {
  const value = raw !== null && typeof raw === 'object' && 'path' in raw ? (raw as { path: unknown }).path : raw
  if (typeof value !== 'string' || value.trim() === '') throw new Error('invalid path')
  const resolved = path.resolve(value)
  if (!existsSync(resolved)) throw new Error('file not found')
  const st = statSync(resolved)
  if (!st.isFile() && !st.isDirectory()) throw new Error('not a file')
  return resolved
}

function failCommand(message: string): { ok: false; message: string } {
  return { ok: false, message }
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
      shell.showItemInFolder(resolveExistingTarget(payload))
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

  ipcMain.handle('shell:openAny', async (_event, payload: unknown): Promise<ShellOpenResult> => {
    try {
      const target = resolveExistingTarget(payload)
      const error = await shell.openPath(target)
      return error ? fail(error) : ok()
    } catch (err) {
      return fail(err instanceof Error ? err.message : 'openAny failed')
    }
  })

  ipcMain.handle('shell:runCommand', async (_event, payload: unknown) => {
    try {
      const body = payload as { template?: string; path?: string }
      const template = String(body?.template ?? '').trim()
      if (!template.includes('{path}')) return failCommand('命令须包含 {path}')
      const target = resolveExistingTarget(body.path)
      const tokens = template.split(/\s+/).map((token) => token.split('{path}').join(target))
      const exe = tokens[0]
      if (!exe) return failCommand('命令为空')
      return await new Promise<{ ok: true } | { ok: false; message: string }>((resolve) => {
        const child = spawn(exe, tokens.slice(1), {
          detached: true,
          stdio: 'ignore',
          windowsHide: true,
        })
        child.once('error', (err) => {
          const code = (err as NodeJS.ErrnoException).code
          resolve(
            failCommand(
              code === 'ENOENT' ? '找不到命令，请到设置 → 消费渠道配置打开方式' : err.message,
            ),
          )
        })
        child.once('spawn', () => {
          child.unref()
          resolve({ ok: true })
        })
      })
    } catch (err) {
      return failCommand(err instanceof Error ? err.message : 'runCommand failed')
    }
  })
}
