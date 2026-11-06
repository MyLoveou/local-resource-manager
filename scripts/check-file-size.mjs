import { readFileSync, readdirSync, statSync, writeFileSync } from 'node:fs'
import { dirname, join, relative, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const BASELINE = join(ROOT, 'scripts', 'file-size-baseline.json')
const UPDATE = process.argv.includes('--update-baseline')

const roots = [
  { path: 'apps/backend/app', test: false },
  { path: 'apps/backend/tests', test: true },
  { path: 'apps/desktop/src/renderer/src', test: false },
  { path: 'apps/desktop/src/main', test: false },
]
const extensions = new Set(['.py', '.ts', '.tsx', '.vue'])
const excludedDirs = new Set([
  '__pycache__',
  'node_modules',
  'out',
  'dist',
  'build',
  'migrations',
  '.pytest_cache',
])

function walk(dir, out = []) {
  for (const entry of readdirSync(dir, { withFileTypes: true })) {
    if (entry.name.startsWith('.') && entry.name !== '.') continue
    if (entry.isDirectory()) {
      if (excludedDirs.has(entry.name)) continue
      walk(join(dir, entry.name), out)
    } else if (extensions.has(entry.name.slice(entry.name.lastIndexOf('.')))) {
      out.push(join(dir, entry.name))
    }
  }
  return out
}

function countLines(path, test) {
  const text = readFileSync(path, 'utf8')
  const body = path.endsWith('.vue')
    ? text.replace(/<style\b[\s\S]*?<\/style>\s*/gi, '\n')
    : text
  const lines = body.split(/\r?\n/).length
  return {
    lines,
    target: test ? 700 : 500,
    hard: test ? 1000 : 800,
  }
}

const baseline = (() => {
  try {
    return JSON.parse(readFileSync(BASELINE, 'utf8'))
  } catch {
    return {}
  }
})()

const files = roots.flatMap((root) =>
  walk(join(ROOT, root.path)).map((path) => ({
    path,
    rel: relative(ROOT, path).replaceAll('\\', '/'),
    test: root.test || /\.test\.[cm]?[jt]sx?$/.test(path),
  })),
)

const results = files
  .map((file) => ({ ...file, ...countLines(file.path, file.test) }))
  .filter((file) => file.lines > file.target)
  .sort((a, b) => b.lines - a.lines)

if (UPDATE) {
  const next = {}
  for (const file of results) next[file.rel] = file.lines
  writeFileSync(BASELINE, `${JSON.stringify(next, null, 2)}\n`, 'utf8')
  console.log(`[file-size] baseline updated: ${results.length} files`)
  process.exit(0)
}

const errors = []
for (const file of results) {
  const allowed = baseline[file.rel]
  if (allowed === undefined) {
    errors.push(`${file.rel}: ${file.lines} 行，超过目标 ${file.target}`)
  } else if (file.lines > allowed) {
    errors.push(`${file.rel}: ${file.lines} 行，超过基线 ${allowed}`)
  }
  if (file.lines > file.hard && allowed === undefined) {
    errors.push(`${file.rel}: ${file.lines} 行，超过硬上限 ${file.hard}`)
  }
}

if (errors.length) {
  console.error('[file-size] FAIL')
  for (const error of errors) console.error(`  - ${error}`)
  console.error('新增/增长文件请拆分；存量文件基线见 scripts/file-size-baseline.json')
  process.exit(1)
}

console.log(`[file-size] OK: ${results.length} 个文件超过软目标，但未超过基线`)
