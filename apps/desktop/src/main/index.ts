import { app, BrowserWindow, Menu } from 'electron'
import { join } from 'path'
import { startServices, stopServices } from './infrastructure/services/index'
import { initMainLog, log } from './log'

/** 尽早初始化，否则启动失败写不进日志，渲染进程也无法用 electron-log */
initMainLog()

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
  win.webContents.openDevTools();
  // 隐藏顶部菜单栏
  Menu.setApplicationMenu(null)

  if (process.env['ELECTRON_RENDERER_URL']) {
    win.loadURL(process.env['ELECTRON_RENDERER_URL'])
  } else {
    win.loadFile(join(__dirname, '../renderer/index.html'))
  }
}

app.whenReady().then(async () => {
  try {
    log.info('[main] starting backend…')
    const backend = await startServices()
    backendUrl = backend.baseURL
    backendToken = backend.token
    log.info('[main] backend ready', backend.baseURL)
    createWindow()
  } catch (err) {
    log.error('[main] failed to start', err)
    throw err
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
