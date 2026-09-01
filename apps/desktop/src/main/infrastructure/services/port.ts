import { createServer } from 'net'
import type { AddressInfo } from 'net'

/**
 * 获取一个空闲端口：临时监听 0（系统分配），取号后立即释放。
 */
export function getFreePort(): Promise<number> {
  return new Promise((resolve, reject) => {
    const srv = createServer()
    srv.listen(0, '127.0.0.1', () => {
      const port = (srv.address() as AddressInfo).port
      srv.close(() => resolve(port))
    })
    srv.on('error', reject)
  })
}
