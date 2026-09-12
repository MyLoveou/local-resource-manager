import { mkdtempSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join, resolve } from 'node:path'
import { describe, it } from 'node:test'
import assert from 'node:assert/strict'
import { resolveExistingFile } from './existingFile.ts'

describe('resolveExistingFile', () => {
  it('rejects missing paths', () => {
    assert.throws(() => resolveExistingFile('D:\\definitely-not-a-file-9f3a.xyz'), /file not found/)
  })

  it('rejects empty and non-string', () => {
    assert.throws(() => resolveExistingFile(''), /invalid path/)
    assert.throws(() => resolveExistingFile(null), /invalid path/)
  })

  it('rejects directories', () => {
    assert.throws(() => resolveExistingFile(tmpdir()), /not a file/)
  })

  it('returns resolved existing files', () => {
    const dir = mkdtempSync(join(tmpdir(), 'sm-file-'))
    const file = join(dir, 'a.bin')
    writeFileSync(file, 'x')
    try {
      assert.equal(resolveExistingFile(file), resolve(file))
    } finally {
      rmSync(dir, { recursive: true, force: true })
    }
  })
})
