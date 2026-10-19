import client from './client'
import type { HomeSummary } from '@/domain'

export async function getHome(): Promise<HomeSummary> {
  const { data } = await client.get<HomeSummary>('/library/home')
  return data
}
