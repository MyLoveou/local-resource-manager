/**
 * 除查看器外只用缩略图。
 */
import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import { withMediaCacheBust } from './mediaUrl.ts'

describe('withMediaCacheBust', () => {
  it('appends revision query', () => {
    assert.equal(
      withMediaCacheBust('/library/resources/1/files/2/content', '2026-09-22T01:00:00'),
      '/library/resources/1/files/2/content?v=2026-09-22T01%3A00%3A00'
    )
  })
  it('keeps empty url', () => {
    assert.equal(withMediaCacheBust('', 'x'), '')
  })
})
