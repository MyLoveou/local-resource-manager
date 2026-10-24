/**
 * 发布产物校验：产物存在/版本命名 → 冻结后端启动 + /health 冒烟 → SHA256SUMS。
 * 退出码 0=通过；非 0=失败。
 */
import { spawn } from 'node:child_process'
import { createHash } from 'node:crypto'
import {
  createReadStream,
  existsSync,
  mkdtempSync,
  readFileSync,
  rmSync,
  statSync,
  writeFileSync,
} from 'node:fs'
import { createServer } from 'node:net'
import { tmpdir } from 'node:os'
import { basename, dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const VERSION = JSON.parse(
  readFileSync(join(ROOT, 'apps/desktop/package.json'), 'utf8')
).version
const RELEASE = join(ROOT, 'release')
const SETUP = join(RELEASE, `local-resource-manager-${VERSION}-win-x64-setup.exe`)
const ZIP = join(RELEASE, `local-resource-manager-${VERSION}-win-x64.zip`)
const UNPACKED = join(RELEASE, 'win-unpacked')
const ASAR = join(UNPACKED, 'resources', 'app.asar')
const BACKEND_DIR = join(UNPACKED, 'resources', 'backend')
const BACKEND = join(BACKEND_DIR, 'source-manager-backend.exe')
const LATEST = join(RELEASE, 'latest.yml')
const APP_UPDATE = join(UNPACKED, 'resources', 'app-update.yml')
const FFPROBE = join(UNPACKED, 'resources', 'ffprobe', 'ffprobe.exe')
const SUMS = join(RELEASE, 'SHA256SUMS.txt')

let failed = false
function fail(message) {
  failed = true
  console.error(`[verify] FAIL: ${message}`)
}

function assertFile(path, minBytes) {
  if (!existsSync(path)) {
    fail(`缺少产物 ${path}`)
    return false
  }
  const size = statSync(path).size
  if (size < minBytes) {
    fail(`产物过小 ${path}（${size} bytes < ${minBytes}）`)
    return false
  }
  console.log(`[verify] OK ${basename(path)} (${(size / 1024 / 1024).toFixed(1)} MB)`)
  return true
}

function freePort() {
  return new Promise((resolvePort, reject) => {
    const server = createServer()
    server.listen(0, '127.0.0.1', () => {
      const { port } = server.address()
      server.close(() => resolvePort(port))
    })
    server.on('error', reject)
  })
}

async function waitHealth(url, timeoutMs) {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    try {
      const res = await fetch(url)
      if (res.status === 200) return true
    } catch {
      /* 未就绪，继续轮询 */
    }
    await new Promise((r) => setTimeout(r, 300))
  }
  return false
}

async function smokeFrozenBackend() {
  const dir = mkdtempSync(join(tmpdir(), 'lrm-verify-'))
  const port = await freePort()
  const dbPath = join(dir, 'library.db')
  const child = spawn(
    BACKEND,
    ['--host', '127.0.0.1', '--port', String(port), '--no-access-log'],
    {
      cwd: dirname(BACKEND),
      env: {
        ...process.env,
        BACKEND_DB_PATH: dbPath,
        LOG_DIR: join(dir, 'logs'),
        BACKEND_TOKEN: 'verify-token',
        BACKEND_VERSION: VERSION,
        PYTHONIOENCODING: 'utf-8',
        PYTHONUTF8: '1',
      },
      stdio: ['ignore', 'pipe', 'pipe'],
      windowsHide: true,
    }
  )
  let output = ''
  child.stdout.on('data', (data) => {
    output += data.toString()
  })
  child.stderr.on('data', (data) => {
    output += data.toString()
  })

  try {
    const healthy = await waitHealth(`http://127.0.0.1:${port}/health`, 30000)
    if (!healthy) {
      fail(`冻结后端 /health 未在 30s 内返回 200\n${output.slice(-4000)}`)
      return false
    }
    if (!existsSync(dbPath) || statSync(dbPath).size === 0) {
      fail('冻结后端未创建数据库（migrations 未执行）')
      return false
    }
    console.log(`[verify] OK 冻结后端 /health 200，DB ${(statSync(dbPath).size / 1024).toFixed(0)} KB`)
    return true
  } finally {
    child.kill()
    await new Promise((r) => {
      if (child.exitCode !== null) return r()
      const timer = setTimeout(r, 5000)
      child.once('exit', () => {
        clearTimeout(timer)
        r()
      })
    })
    rmSync(dir, { recursive: true, force: true })
  }
}

function sha256(path) {
  return new Promise((resolveHash, reject) => {
    const hash = createHash('sha256')
    createReadStream(path)
      .on('data', (chunk) => hash.update(chunk))
      .on('end', () => resolveHash(hash.digest('hex')))
      .on('error', reject)
  })
}

async function main() {
  // 先清理旧校验和：失败时不得留下看似通过的旧文件
  rmSync(SUMS, { force: true })

  assertFile(SETUP, 10 * 1024 * 1024)
  assertFile(ZIP, 10 * 1024 * 1024)
  assertFile(ASAR, 1024 * 1024)
  assertFile(BACKEND, 1024 * 1024)
  assertFile(LATEST, 50)
  assertFile(APP_UPDATE, 20)
  assertFile(FFPROBE, 10 * 1024 * 1024)
  if (existsSync(LATEST)) {
    const latest = readFileSync(LATEST, 'utf8')
    if (!latest.includes(`version: ${VERSION}`)) {
      fail('latest.yml 版本与 package.json 不一致')
    }
    if (!latest.includes(`path: local-resource-manager-${VERSION}-win-x64-setup.exe`)) {
      fail('latest.yml 未指向当前安装包')
    }
  }
  if (existsSync(APP_UPDATE)) {
    const conf = readFileSync(APP_UPDATE, 'utf8')
    if (!conf.includes('provider: github')) {
      fail('app-update.yml 未配置 GitHub provider')
    }
  }
  if (!existsSync(join(BACKEND_DIR, '_internal'))) {
    fail('缺少冻结后端 _internal 目录')
  }
  if (failed) process.exit(1)

  if (!(await smokeFrozenBackend())) process.exit(1)

  const entries = await Promise.all(
    [SETUP, ZIP].map(async (path) => `${await sha256(path)}  ${basename(path)}`)
  )
  writeFileSync(SUMS, `${entries.join('\n')}\n`, 'utf8')
  console.log(`\n[verify] PASS → ${SUMS}\n${entries.join('\n')}`)
}

main().catch((error) => {
  fail(error instanceof Error ? error.message : String(error))
  process.exit(1)
})
