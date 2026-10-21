import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import { isAnimatedImageFormat, isLikelyUnsupportedInlineFormat } from './imageFormat.ts'

describe('imageFormat', () => {
  it('treats gif and webp as animated', () => {
    assert.equal(isAnimatedImageFormat('gif'), true)
    assert.equal(isAnimatedImageFormat('.WEBP'), true)
    assert.equal(isAnimatedImageFormat('jpg'), false)
  })

  it('flags heic/heif as likely unsupported inline', () => {
    assert.equal(isLikelyUnsupportedInlineFormat('heic'), true)
    assert.equal(isLikelyUnsupportedInlineFormat('HEIF'), true)
    assert.equal(isLikelyUnsupportedInlineFormat('avif'), false)
  })
})
