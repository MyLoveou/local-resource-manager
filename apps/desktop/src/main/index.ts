import { app, BrowserWindow, Menu, ipcMain, dialog } from 'electron'
import { basename, join } from 'path'
import { readFileSync } from 'fs'
import { startServices, stopServices } from './infrastructure/services/index'
import { registerShellOpenIpc } from './infrastructure/shellOpen'
import { registerThemeCssIpc } from './infrastructure/themeCss'
import { initUpdater, registerUpdateIpc } from './infrastructure/services/update'
import { initMainLog, log } from './log'

/** 打包态固定 userData 为 ASCII 目录（不随中文 productName 漂移，便于备份与脚本） */
if (app.isPackaged) {
  app.setPath('userData', join(app.getPath('appData'), 'local-resource-manager'))
}

/** 尽早初始化，否则启动失败写不进日志，渲染进程也无法用 electron-log */
initMainLog()

const BACKEND_FAILED = {
  level: 'error' as const,
  title: '后端服务启动失败',
  description: '请查看日志',
  duration: 0,
}

const BACKEND_STOPPED = {
  level: 'error' as const,
  title: '后端服务已停止',
  description: '请查看日志后重新打开应用',
  duration: 0,
}

function broadcastNotify(payload: typeof BACKEND_FAILED): void {
  for (const win of BrowserWindow.getAllWindows()) {
    const send = (): void => {
      win.webContents.send('app:notify', payload)
    }
    if (win.webContents.isLoading()) win.webContents.once('did-finish-load', send)
    else send()
  }
}

function registerDialogIpc(): void {
  ipcMain.handle(
    'dialog:selectFiles',
    async (_event, filters?: { name: string; extensions: string[] }[]): Promise<string[]> => {
      const options: Electron.OpenDialogOptions = {
        properties: ['openFile', 'multiSelections'],
        filters: filters && filters.length > 0 ? filters : undefined,
      }
      const win = BrowserWindow.getFocusedWindow() ?? BrowserWindow.getAllWindows()[0]
      const result = win
        ? await dialog.showOpenDialog(win, options)
        : await dialog.showOpenDialog(options)
      if (result.canceled) return []
      return result.filePaths
    }
  )
  ipcMain.handle(
    'dialog:selectImage',
    async (): Promise<{ name: string; dataBase64: string } | null> => {
      const options: Electron.OpenDialogOptions = {
        properties: ['openFile'],
        filters: [
          {
            name: 'Images',
            extensions: ['jpg', 'jpeg', 'png', 'webp', 'bmp', 'gif'],
          },
        ],
      }
      const win = BrowserWindow.getFocusedWindow() ?? BrowserWindow.getAllWindows()[0]
      const result = win
        ? await dialog.showOpenDialog(win, options)
        : await dialog.showOpenDialog(options)
      if (result.canceled || result.filePaths.length === 0) return null
      const path = result.filePaths[0]
      const data = readFileSync(path)
      if (data.length > 32 * 1024 * 1024) {
        throw new Error('文件超过 32 MB，无法导入')
      }
      return { name: basename(path), dataBase64: data.toString('base64') }
    }
  )
  ipcMain.handle('dialog:selectDirectory', async (): Promise<string | null> => {
    const options: Electron.OpenDialogOptions = { properties: ['openDirectory'] }
    const win = BrowserWindow.getFocusedWindow() ?? BrowserWindow.getAllWindows()[0]
    const result = win
      ? await dialog.showOpenDialog(win, options)
      : await dialog.showOpenDialog(options)
    if (result.canceled || result.filePaths.length === 0) return null
    return result.filePaths[0]
  })
  ipcMain.handle('app:relaunch', (): void => {
    app.relaunch()
    app.exit(0)
  })
}

/**
 * Electron 主进程（UI 层外壳）。
 * 职责：窗口生命周期、加载渲染进程、进程编排（拉起抓取/下载服务）。
 */
let backendUrl = 'http://127.0.0.1:8000'
let backendToken = ''

function createWindow(): void {
  const win = new BrowserWindow({
    width: 1280,
    height: 800,
    minWidth: 960,
    minHeight: 600,
    title: 'Source Manager',
    webPreferences: {
      preload: join(__dirname, '../preload/index.js'),
      sandbox: false,
      contextIsolation: true,
      // 通过命令行参数把后端地址/token 传给 preload（比 process.env 可靠）
      additionalArguments: [
        `--backend-url=${backendUrl}`,
        `--backend-token=${backendToken}`,
      ],
    },
  })
  if (process.env['ELECTRON_DEVTOOLS'] === '1') {
    win.webContents.openDevTools()
  }
  // 隐藏顶部菜单栏
  Menu.setApplicationMenu(null)

  if (process.env['ELECTRON_RENDERER_URL']) {
    win.loadURL(process.env['ELECTRON_RENDERER_URL'])
  } else {
    win.loadFile(join(__dirname, '../renderer/index.html'))
  }
}

app.whenReady().then(async () => {
  registerDialogIpc()
  registerShellOpenIpc()
  registerThemeCssIpc()
  registerUpdateIpc()
  try {
    log.info('[main] starting backend…')
    const backend = await startServices()
    backendUrl = backend.baseURL
    backendToken = backend.token
    log.info('[main] backend ready', backend.baseURL)
    backend.watchExit(() => {
      log.error('[main] backend exited unexpectedly')
      broadcastNotify(BACKEND_STOPPED)
    })
    createWindow()
    initUpdater()
  } catch (err) {
    log.error('[main] failed to start', err)
    createWindow()
    initUpdater()
    broadcastNotify(BACKEND_FAILED)
  }

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
  app.on('will-quit', () => {
    log.info('[main] stopping services')
    void stopServices()
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})
