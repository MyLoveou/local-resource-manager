// 从 IIFE 内部抽取规则常量：按源码位置取对象/数组字面量，再按出现顺序求值。
import { readFileSync, writeFileSync } from 'node:fs'
import vm from 'node:vm'

const htmlPath = process.argv[2]
const outPath = process.argv[3]
const text = readFileSync(htmlPath, 'utf8')

const WANT = [
  'NEG_HUMAN', 'NEG_CORE', 'NEG_EXTRA', 'NEG_QUALITY', 'NEG_LIGHT', 'NEG_TEXT',
  'NEG_CAT', 'NEG_BY_CAT', 'NEG_COMPOSE', 'NEG_RULES', 'CONFLICTS', 'META_TAGS',
]

function literalAt(src, name) {
  const decl = new RegExp(`(?:const|let|var)\\s+${name}\\s*=`, 'g')
  const match = decl.exec(src)
  if (!match) return null
  let i = match.index + match[0].length
  while (i < src.length && /\s/.test(src[i])) i++
  const open = src[i]
  const close = open === '{' ? '}' : open === '[' ? ']' : null
  if (!close) return null
  let depth = 0
  let quote = null
  for (let j = i; j < src.length; j++) {
    const ch = src[j]
    if (quote) {
      if (ch === '\\') { j++; continue }
      if (ch === quote) quote = null
      continue
    }
    if (ch === '"' || ch === "'" || ch === '`') { quote = ch; continue }
    if (ch === open) depth++
    else if (ch === close) {
      depth--
      if (depth === 0) return { start: i, body: src.slice(i, j + 1) }
    }
  }
  return null
}

const found = []
for (const name of WANT) {
  const hit = literalAt(text, name)
  if (hit) found.push({ name, ...hit })
}
found.sort((a, b) => a.start - b.start)

const captured = {}
for (const item of found) {
  const code = `var __value = (${item.body})`
  try {
    const sandbox = { ...captured }
    vm.createContext(sandbox)
    vm.runInContext(code, sandbox, { timeout: 5000 })
    captured[item.name] = sandbox.__value
  } catch (error) {
    console.warn(`跳过 ${item.name}: ${error.message.slice(0, 60)}`)
  }
}

writeFileSync(outPath, JSON.stringify(captured, null, 1), 'utf8')
console.log('捕获:', Object.keys(captured).map((k) => {
  const v = captured[k]
  return `${k}(${Array.isArray(v) ? v.length : typeof v === 'object' ? Object.keys(v).length : typeof v})`
}).join(', '))
