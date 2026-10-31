/**
 * Windows 发布编排（组合根）：
 * 门禁 → 前端构建 → 后端冻结 → electron-builder → 校验（产物/冒烟/SHA256）。
 * 任一步失败即非零退出。
 */
import { spawnSync } from 'node:child_process'
import { existsSync, rmSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const IS_WIN = process.platform === 'win32'

// electron-builder downloads Electron from GitHub by default, which is often
// slow or blocked on Windows. Keep the build reproducible with the mirror used
// by this project, while allowing an explicit override.
if (IS_WIN && !process.env.ELECTRON_MIRROR) {
  process.env.ELECTRON_MIRROR = 'https://npmmirror.com/mirrors/electron/'
}

function run(label, command, args, opts = {}) {
  console.log(`\n==> ${label}`)
  const result = spawnSync(command, args, {
    cwd: ROOT,
    stdio: 'inherit',
    shell: IS_WIN,
    ...opts,
  })
  if (result.error) {
    throw new Error(`${label} 启动失败: ${result.error.message}`)
  }
  if (result.status !== 0) {
    throw new Error(`${label} 失败（exit ${result.status}）`)
  }
}

function venvPython() {
  if (process.env.PYTHON) return process.env.PYTHON
  const candidate = IS_WIN
    ? join(ROOT, 'apps/backend/.venv/Scripts/python.exe')
    : join(ROOT, 'apps/backend/.venv/bin/python')
  if (!existsSync(candidate)) {
    throw new Error(`未找到后端 venv：${candidate}（先跑 pnpm backend:install）`)
  }
  return candidate
}

const python = venvPython()

try {
  console.log('==> 清理旧产物')
  for (const dir of ['release', 'apps/backend/build', 'apps/backend/dist']) {
    rmSync(join(ROOT, dir), { recursive: true, force: true })
  }

  run('类型检查', 'pnpm', ['--filter', 'desktop', 'typecheck'])
  run('文件规模', 'pnpm', ['check:file-size'])
  run('前端测试', 'pnpm', ['--filter', 'desktop', 'test'])
  run('Lint', 'pnpm', ['--filter', 'desktop', 'lint'])
  run('后端测试', python, ['-m', 'pytest', '-q', 'tests'], {
    cwd: join(ROOT, 'apps/backend'),
    shell: false,
  })
  run('前端构建', 'pnpm', ['--filter', 'desktop', 'build'])
  run(
    '冻结后端',
    python,
    [
      '-m',
      'PyInstaller',
      '--noconfirm',
      '--clean',
      '--distpath',
      join(ROOT, 'apps/backend/dist'),
      '--workpath',
      join(ROOT, 'apps/backend/build'),
      join(ROOT, 'apps/backend/packaging/backend.spec'),
    ],
    { shell: false }
  )
  run('ffprobe', 'node', [join(ROOT, 'scripts/copy-ffprobe.mjs')])
  run('打包安装包', 'pnpm', ['exec', 'electron-builder', '--win', '--x64', '--publish', 'never'], {
    cwd: join(ROOT, 'apps/desktop'),
  })
  run('校验产物', 'node', [join(ROOT, 'scripts/verify-release.mjs')])
  console.log('\n==> 发布完成：release/')
} catch (error) {
  console.error(`\n[release] 失败：${error.message}`)
  process.exit(1)
}
