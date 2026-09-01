import { app } from 'electron'
import { join, resolve } from 'path'

/** 主进程后端编排配置（静态前置；端口/token 为运行时产物，不在此配置） */
export interface BackendConfig {
  /** python 可执行文件（uvicorn 所在 venv） */
  pythonPath: string
  /** 后端项目目录（uvicorn 的 cwd，含 app/main.py） */
  backendDir: string
  /** uvicorn 启动模块 */
  module: string
  /** 绑定主机 */
  host: string
  /** 健康检查等待上限（ms） */
  healthTimeoutMs: number
  /** 健康检查轮询间隔（ms） */
  healthIntervalMs: number
}

/**
 * 项目根目录。
 * dev：app.getAppPath() = apps/desktop，上两级即仓库根；可被 PROJECT_ROOT 覆盖。
 */
function resolveProjectRoot(): string {
  return process.env.PROJECT_ROOT ?? resolve(app.getAppPath(), '../..')
}

/** 默认 venv python 路径（Windows 在 Scripts/，POSIX 在 bin/） */
function defaultPythonPath(root: string): string {
  return process.platform === 'win32'
    ? join(root, 'apps/backend/.venv/Scripts/python.exe')
    : join(root, 'apps/backend/.venv/bin/python')
}

/**
 * 加载配置：BACKEND_ 前缀环境变量优先，开发默认值兜底。
 */
export function loadBackendConfig(): BackendConfig {
  const root = resolveProjectRoot()
  return {
    pythonPath: process.env.BACKEND_PYTHON_PATH ?? defaultPythonPath(root),
    backendDir: process.env.BACKEND_DIR ?? join(root, 'apps/backend'),
    module: process.env.BACKEND_MODULE ?? 'app.main:app',
    host: process.env.BACKEND_HOST ?? '127.0.0.1',
    healthTimeoutMs: Number(process.env.BACKEND_HEALTH_TIMEOUT ?? 15000),
    healthIntervalMs: Number(process.env.BACKEND_HEALTH_INTERVAL ?? 300),
  }
}
