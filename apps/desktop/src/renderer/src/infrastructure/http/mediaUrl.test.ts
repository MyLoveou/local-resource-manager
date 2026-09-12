/**
 * 除查看器外只用缩略图。
 */
import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

function resolveCardImageUrl(resource: { thumbnailPath?: string | null }): string {
  return resource.thumbnailPath ?? ''
}

describe('resolveCardImageUrl', () => {
  it('uses thumbnail only', () => {
    assert.equal(resolveCardImageUrl({ thumbnailPath: '/library/resources/1/files/2/content' }), '/library/resources/1/files/2/content')
  })
  it('does not fall back to cover', () => {
    assert.equal(resolveCardImageUrl({}), '')
  })
})
