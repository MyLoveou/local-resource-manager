/**
 * 后端服务启动/停止：拉起 uvicorn 子进程，健康检查就绪后返回。
 */
import { spawn } from 'child_process'
import type { ChildProcess } from 'child_process'
import { randomBytes } from 'crypto'
import http from 'http'
import { dirname, join } from 'path'
import { app } from 'electron'
import type { BackendConfig } from './config'
import { getFreePort } from './port'

/** 后端实例句柄 */
export interface BackendInstance {
  baseURL: string
  port: number
  token: string
  stop(): Promise<void>
  watchExit(listener: (code: number | null) => void): void
}

/**
 * 轮询健康检查：成功(200)resolve；网络错误/非 200 重试；超时 reject。
 */
function waitForHealth(url: string, timeoutMs: number, intervalMs: number): Promise<void> {
  return new Promise((resolve, reject) => {
    const deadline = Date.now() + timeoutMs

    const cleanup = (timer: NodeJS.Timeout | undefined): void => {
      if (timer) clearTimeout(timer)
    }

    const retry = (timer: NodeJS.Timeout | undefined): void => {
      if (Date.now() > deadline) {
        cleanup(timer)
        reject(new Error('后端健康检查超时'))
        return
      }
      setTimeout(attempt, intervalMs)
    }

    const attempt = (): void => {
      const req = http.get(url, (res) => {
        res.resume()
        if (res.statusCode === 200) {
          cleanup(timer)
          resolve()
        } else {
          retry(timer)
        }
      })
      req.on('error', () => retry(timer))
      req.setTimeout(intervalMs, () => {
        req.destroy()
        retry(timer)
      })
    }

    const timer = setTimeout(() => {
      cleanup(timer)
      reject(new Error('后端健康检查超时'))
    }, timeoutMs)

    attempt()
  })
}

/** 终止子进程并等待其退出（已退出则直接返回） */
function killProcess(child: ChildProcess): Promise<void> {
  return new Promise((resolve) => {
    if (child.exitCode !== null || child.killed) {
      resolve()
      return
    }
    child.once('exit', () => resolve())
    child.kill()
  })
}

/** 启动后端：找空闲端口 → spawn（dev: uvicorn / frozen: 随包 exe）→ 健康检查 → 返回实例 */
export async function startBackend(cfg: BackendConfig): Promise<BackendInstance> {
  const port = await getFreePort()
  const token = randomBytes(16).toString('hex')
  const baseEnv = {
    ...process.env,
    BACKEND_TOKEN: token,
    BACKEND_VERSION: app.getVersion(),
    PYTHONIOENCODING: 'utf-8',
    PYTHONUTF8: '1',
  }

  let command: string
  let args: string[]
  let cwd: string | undefined
  const env: NodeJS.ProcessEnv = { ...baseEnv }
  if (cfg.mode === 'frozen') {
    if (!cfg.backendExe) throw new Error('后端 exe 路径未配置')
    command = cfg.backendExe
    cwd = dirname(cfg.backendExe)
    args = ['--host', cfg.host, '--no-access-log', '--port', String(port)]
    env.BACKEND_DB_PATH = join(app.getPath('userData'), 'library.db')
    env.FFPROBE_BIN = join(process.resourcesPath, 'ffprobe', 'ffprobe.exe')
  } else {
    if (!cfg.pythonPath || !cfg.backendDir || !cfg.module) {
      throw new Error('开发态后端配置不完整')
    }
    command = cfg.pythonPath
    cwd = cfg.backendDir
    args = [
      '-m',
      'uvicorn',
      cfg.module,
      '--host',
      cfg.host,
      '--no-access-log',
      '--port',
      String(port),
    ]
  }

  // 启动后端
  const child = spawn(command, args, {
    cwd,
    env,
    stdio: ['ignore', 'pipe', 'pipe'],
    windowsHide: true,
  })
  // 管道转发：后端 stdout/stderr → electron-log（否则当前终端看不到）
  child.stdout?.on('data', (d) => {
    const line = d.toString().trimEnd()
    if (line) console.log(line)
  })
  child.stderr?.on('data', (d) => {
    const line = d.toString().trimEnd()
    if (line) console.error(line)
  })

  // 订阅子进程启动失败通知
  const spawnFailed = new Promise<never>((_, reject) => {
    child.once('error', reject)
  })
  // 健康检查
  const baseUrl = `http://${cfg.host}:${port}`
  const ready = waitForHealth(`${baseUrl}/health`, cfg.healthTimeoutMs, cfg.healthIntervalMs)

  try {
    await Promise.race([ready, spawnFailed])
  } catch (err) {
    killProcess(child).catch(() => { })
    throw err
  }

  let stopping = false
  const exitListeners: Array<(code: number | null) => void> = []
  child.on('exit', (code) => {
    if (stopping) return
    for (const listener of exitListeners) listener(code)
  })

  return {
    baseURL: baseUrl,
    port,
    token,
    watchExit(listener) {
      exitListeners.push(listener)
    },
    stop: () => {
      stopping = true
      return killProcess(child)
    },
  }
}
