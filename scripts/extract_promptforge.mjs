// 从 PromptForge 单文件 HTML 中抽取内置数据（window.PG_*）为 JSON。
// 用法：node scripts/extract_promptforge.mjs "<html路径>" "<输出目录>"
import { readFileSync, writeFileSync, mkdirSync } from 'node:fs'
import { dirname, resolve } from 'node:path'
import vm from 'node:vm'

const htmlPath = process.argv[2]
const outDir = process.argv[3]
if (!htmlPath || !outDir) {
  console.error('用法: node scripts/extract_promptforge.mjs <html> <outDir>')
  process.exit(1)
}

const html = readFileSync(htmlPath, 'utf8')
const blocks = [...html.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/g)].map((m) => m[1])
console.log(`script 块: ${blocks.length}`)

const store = new Map()
const stubElement = () => ({
  style: {},
  classList: { add() {}, remove() {}, toggle() {}, contains: () => false },
  appendChild() {},
  removeChild() {},
  setAttribute() {},
  addEventListener() {},
  removeEventListener() {},
  querySelector: () => null,
  querySelectorAll: () => [],
  innerHTML: '',
  textContent: '',
  dataset: {},
})

const sandbox = {
  console,
  setTimeout,
  clearTimeout,
  setInterval: () => 0,
  clearInterval: () => {},
  fetch: () => Promise.reject(new Error('offline')),
  requestAnimationFrame: () => 0,
  cancelAnimationFrame: () => {},
  navigator: { userAgent: 'node', clipboard: { writeText: async () => {} } },
  localStorage: {
    getItem: (k) => (store.has(k) ? store.get(k) : null),
    setItem: (k, v) => store.set(k, String(v)),
    removeItem: (k) => store.delete(k),
  },
  document: {
    documentElement: stubElement(),
    body: stubElement(),
    head: stubElement(),
    createElement: stubElement,
    querySelector: () => null,
    querySelectorAll: () => [],
    addEventListener() {},
    getElementById: () => null,
  },
  matchMedia: () => ({ matches: false, addEventListener() {} }),
  location: { href: 'http://127.0.0.1/', origin: 'http://127.0.0.1' },
  alert: () => {},
  URL: { createObjectURL: () => '', revokeObjectURL: () => {} },
  Blob: class {},
}
sandbox.window = sandbox
sandbox.globalThis = sandbox
sandbox.self = sandbox
const context = vm.createContext(sandbox)

let ok = 0
for (const block of blocks) {
  try {
    vm.runInContext(block, context, { timeout: 20000 })
    ok++
  } catch {
    // 依赖 DOM 交互的块会失败，数据块通常在失败之前已经执行过
  }
}
console.log(`成功执行: ${ok}/${blocks.length}`)

const keys = Object.keys(sandbox).filter((k) => k.startsWith('PG_'))
const summary = {}
for (const key of keys) {
  const value = sandbox[key]
  if (Array.isArray(value)) summary[key] = `array(${value.length})`
  else if (value && typeof value === 'object') summary[key] = `object(${Object.keys(value).length})`
  else summary[key] = String(value)
}
console.log('捕获到的 PG_*：')
for (const [key, info] of Object.entries(summary).sort()) console.log(`  ${key}: ${info}`)

mkdirSync(outDir, { recursive: true })
let written = 0
for (const key of keys) {
  const value = sandbox[key]
  if (value === undefined || typeof value === 'function') continue
  const name = key.replace(/^PG_/, '').toLowerCase()
  const file = resolve(outDir, `${name}.json`)
  mkdirSync(dirname(file), { recursive: true })
  writeFileSync(file, JSON.stringify(value, null, 1), 'utf8')
  written++
}
console.log(`已写出 ${written} 个 JSON 到 ${outDir}`)
