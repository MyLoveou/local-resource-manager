/**
 * 首页概览端点（infrastructure/http · 后端 /library/overview）
 */
import client from './client'
import type { Overview } from '@/domain'

/** 获取首页概览：统计 + 最近添加 + 任务计数 */
export async function getOverview(): Promise<Overview> {
  const { data } = await client.get<Overview>('/library/overview')
  return data
}
