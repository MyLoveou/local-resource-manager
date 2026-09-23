import assert from 'node:assert/strict'
import { describe, it } from 'node:test'
import { mapHttpError } from './mapHttpError.ts'

describe('mapHttpError', () => {
  it('maps network failure', () => {
    const mapped = mapHttpError({ message: 'Network Error' }, '获取首页概览')
    assert.equal(mapped.title, '获取首页概览失败')
    assert.match(mapped.description ?? '', /无法连接后端/)
  })

  it('maps timeout', () => {
    const mapped = mapHttpError({ code: 'ECONNABORTED', message: 'timeout' })
    assert.match(mapped.description ?? '', /超时/)
  })

  it('maps 404', () => {
    const mapped = mapHttpError({ response: { status: 404, data: {} } })
    assert.match(mapped.description ?? '', /不存在/)
  })

  it('maps 5xx', () => {
    const mapped = mapHttpError({ response: { status: 502, data: {} } })
    assert.match(mapped.description ?? '', /服务异常/)
  })

  it('maps fastapi detail string and array', () => {
    assert.equal(
      mapHttpError({ response: { status: 400, data: { detail: '无法识别' } } }).description,
      '无法识别'
    )
    assert.equal(
      mapHttpError({ response: { status: 422, data: { detail: [{ msg: '字段缺失' }] } } }).description,
      '字段缺失'
    )
  })
})
