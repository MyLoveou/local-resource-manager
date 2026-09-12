/**
 * 校验本地文件路径。只判断存在且为文件，供 shell 打开用。
 */
import { statSync } from 'node:fs'
import { resolve } from 'node:path'

export function resolveExistingFile(raw: unknown): string {
  if (typeof raw !== 'string' || raw.trim() === '') {
    throw new Error('invalid path')
  }
  const resolved = resolve(raw)
  let st
  try {
    st = statSync(resolved)
  } catch {
    throw new Error('file not found')
  }
  if (!st.isFile()) {
    throw new Error('not a file')
  }
  return resolved
}
