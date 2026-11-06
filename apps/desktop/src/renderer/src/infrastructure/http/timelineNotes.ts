import client from './client'

export type TimelineNoteScope = 'date' | 'saved_view'

export interface TimelineNote {
  id: number
  scope: TimelineNoteScope
  date?: string | null
  savedViewId?: number | null
  title: string
  body?: string | null
  locationName?: string | null
  createdAt?: string | null
  updatedAt?: string | null
}

export interface TimelineNoteUpsert {
  title?: string
  body?: string | null
  locationName?: string | null
}

export async function getDateNotes(
  dateFrom?: string,
  dateTo?: string,
): Promise<TimelineNote[]> {
  const { data } = await client.get<{ items: TimelineNote[] }>('/library/timeline-notes', {
    params: { dateFrom, dateTo },
  })
  return data.items
}

export async function getDateNote(date: string): Promise<TimelineNote | null> {
  const { data } = await client.get<TimelineNote | null>(
    `/library/timeline-notes/date/${encodeURIComponent(date)}`,
  )
  return data
}

export async function upsertDateNote(
  date: string,
  body: TimelineNoteUpsert,
): Promise<TimelineNote> {
  const { data } = await client.put<TimelineNote>(
    `/library/timeline-notes/date/${encodeURIComponent(date)}`,
    body,
  )
  return data
}

export async function deleteDateNote(date: string): Promise<void> {
  await client.delete(`/library/timeline-notes/date/${encodeURIComponent(date)}`)
}

export async function getSavedViewNote(savedViewId: number): Promise<TimelineNote | null> {
  const { data } = await client.get<TimelineNote | null>(
    `/library/timeline-notes/saved-view/${savedViewId}`,
  )
  return data
}

export async function upsertSavedViewNote(
  savedViewId: number,
  body: TimelineNoteUpsert,
): Promise<TimelineNote> {
  const { data } = await client.put<TimelineNote>(
    `/library/timeline-notes/saved-view/${savedViewId}`,
    body,
  )
  return data
}

export async function deleteSavedViewNote(savedViewId: number): Promise<void> {
  await client.delete(`/library/timeline-notes/saved-view/${savedViewId}`)
}
