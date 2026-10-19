import client from './client'
import type { SavedView, SavedViewFilters, TimelineScope } from '@/domain'

export async function listSavedViews(scope?: TimelineScope): Promise<SavedView[]> {
  const { data } = await client.get<{ items: SavedView[] }>('/library/saved-views', {
    params: scope ? { scope } : undefined,
  })
  return data.items
}

export async function getSavedView(id: number): Promise<SavedView> {
  const { data } = await client.get<SavedView>(`/library/saved-views/${id}`)
  return data
}

export async function createSavedView(body: {
  scope: TimelineScope
  name: string
  filters: SavedViewFilters
  sort?: string
}): Promise<SavedView> {
  const { data } = await client.post<SavedView>('/library/saved-views', {
    kind: 'timeline',
    ...body,
  })
  return data
}

export async function patchSavedView(
  id: number,
  body: { scope?: TimelineScope; name?: string; filters?: SavedViewFilters; sort?: string },
): Promise<SavedView> {
  const { data } = await client.patch<SavedView>(`/library/saved-views/${id}`, body)
  return data
}

export async function deleteSavedView(id: number): Promise<void> {
  await client.delete(`/library/saved-views/${id}`)
}
