/**
 * 下载端点（/download）
 */
import client from './client'
import type { DownloadTask } from '@/domain'

export async function createDownloadTask(url: string): Promise<DownloadTask> {
  const { data } = await client.post<DownloadTask>('/download/tasks', { url })
  return data
}

export async function listDownloadTasks(): Promise<DownloadTask[]> {
  const { data } = await client.get<DownloadTask[]>('/download/tasks')
  return data
}

export async function pauseDownloadTask(id: number): Promise<DownloadTask> {
  const { data } = await client.post<DownloadTask>(`/download/tasks/${id}/pause`)
  return data
}

export async function resumeDownloadTask(id: number): Promise<DownloadTask> {
  const { data } = await client.post<DownloadTask>(`/download/tasks/${id}/resume`)
  return data
}

export async function cancelDownloadTask(id: number): Promise<DownloadTask> {
  const { data } = await client.post<DownloadTask>(`/download/tasks/${id}/cancel`)
  return data
}
