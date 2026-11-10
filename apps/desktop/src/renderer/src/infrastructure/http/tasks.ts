/** 任务中心 HTTP 客户端 */
import client from './client'

export interface TaskItem {
  id: string
  kind: string
  resourceId?: number | null
  title: string
  state: string
  done: number
  total: number
  percent: number
  attempts: number
  error?: string | null
  createdAt?: string | null
  startedAt?: string | null
  finishedAt?: string | null
}

export async function listTasks(params: { active?: boolean; state?: string } = {}): Promise<TaskItem[]> {
  const { data } = await client.get<{ items: TaskItem[] }>('/tasks', { params })
  return data.items
}

export async function cancelTask(id: string): Promise<TaskItem> {
  const { data } = await client.post<TaskItem>(`/tasks/${id}/cancel`)
  return data
}

export async function retryTask(id: string): Promise<TaskItem> {
  const { data } = await client.post<TaskItem>(`/tasks/${id}/retry`)
  return data
}

export function taskKindLabel(kind: string): string {
  switch (kind) {
    case 'scrape':
      return '刮削'
    case 'import':
      return '导入'
    case 'ai_index':
      return 'AI 索引'
    case 'cover':
      return '封面'
    default:
      return kind
  }
}
