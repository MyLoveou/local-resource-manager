/**
 * 查看器是否还能前进（含尚未加载的下一页）。
 */
import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import { canGoNext } from './imageViewerNav.ts'

describe('canGoNext', () => {
  it('advances inside loaded playlist', () => {
    assert.equal(canGoNext(0, 80, false, false), true)
  })
  it('stops at last when no more pages', () => {
    assert.equal(canGoNext(79, 80, false, false), false)
  })
  it('allows last when hasMore', () => {
    assert.equal(canGoNext(79, 80, true, false), true)
  })
  it('allows last while loadingMore', () => {
    assert.equal(canGoNext(0, 1, false, true), true)
  })
  it('rejects missing current', () => {
    assert.equal(canGoNext(-1, 80, true, false), false)
  })
})
