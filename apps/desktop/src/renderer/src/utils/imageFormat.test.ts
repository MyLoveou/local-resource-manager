import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import { isAnimatedImageFormat, isLikelyUnsupportedInlineFormat, webpBytesAreAnimated } from './imageFormat.ts'

describe('imageFormat', () => {
  it('treats gif and webp as animated', () => {
    assert.equal(isAnimatedImageFormat('gif'), true)
    assert.equal(isAnimatedImageFormat('.WEBP'), true)
    assert.equal(isAnimatedImageFormat('jpg'), false)
  })

  it('detects animated webp chunks', () => {
    const animated = new TextEncoder().encode('RIFF1234WEBPVP8XANIM1234')
    const still = new TextEncoder().encode('RIFF1234WEBPVP8X12345678')
    assert.equal(webpBytesAreAnimated(animated.buffer), true)
    assert.equal(webpBytesAreAnimated(still.buffer), false)
    assert.equal(webpBytesAreAnimated(new TextEncoder().encode('nope').buffer), false)
  })

  it('flags heic/heif as likely unsupported inline', () => {
    assert.equal(isLikelyUnsupportedInlineFormat('heic'), true)
    assert.equal(isLikelyUnsupportedInlineFormat('HEIF'), true)
    assert.equal(isLikelyUnsupportedInlineFormat('avif'), false)
  })
})
