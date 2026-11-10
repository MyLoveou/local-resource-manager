/** 把当前平台的 ffprobe 复制到 build/ffprobe（打包 extraResources 用）。 */
import { createRequire } from 'node:module'
import { copyFileSync, mkdirSync } from 'node:fs'
import { dirname, join, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const ROOT = resolve(dirname(fileURLToPath(import.meta.url)), '..')
const require = createRequire(join(ROOT, 'apps/desktop/package.json'))
const ffprobe = require('@ffprobe-installer/ffprobe')
const dest = join(ROOT, 'apps/desktop/build/ffprobe/ffprobe.exe')
mkdirSync(dirname(dest), { recursive: true })
copyFileSync(ffprobe.path, dest)
console.log(`[ffprobe] ${ffprobe.version} -> ${dest}`)
