/**
 * 除查看器外只用缩略图。
 */
import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import { withMediaCacheBust, resolveLibraryMediaUrl } from './mediaUrl.ts'
import { resolveCardImageUrl } from './mediaUrl.ts'

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
  it('keeps a server-signed media url intact', () => {
    const globalWithWindow = globalThis as unknown as {
      window?: { electron?: { backend?: { baseUrl?: string } } }
    }
    const previous = globalWithWindow.window
    globalWithWindow.window = {
      electron: { backend: { baseUrl: 'http://127.0.0.1:1234' } },
    }
    try {
      assert.equal(
        resolveLibraryMediaUrl('/library/resources/1/content?exp=123&sig=abc'),
        'http://127.0.0.1:1234/library/resources/1/content?exp=123&sig=abc',
      )
    } finally {
      globalWithWindow.window = previous
    }
  })
  it('falls back to coverPath when thumbnail is missing', () => {
    assert.equal(
      resolveCardImageUrl({
        thumbnailPath: null,
        coverPath: 'data:image/png;base64,cover',
      }),
      'data:image/png;base64,cover',
    )
  })
})
