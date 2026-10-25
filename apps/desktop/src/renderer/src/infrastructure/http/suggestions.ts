import client from './client'
import type {
  SuggestionApplyRequest,
  SuggestionApplyResult,
  SuggestionPage,
  SuggestionRejectRequest,
  SuggestionRejectResult,
  SuggestionSummary,
} from '@/domain/smartImport'

export async function getSuggestionGroups(
  jobId?: string | null,
  limit = 200,
): Promise<SuggestionPage> {
  const { data } = await client.get<SuggestionPage>('/library/import-suggestions', {
    params: jobId ? { jobId, limit } : { limit },
  })
  return data
}

export async function getSuggestionSummary(): Promise<SuggestionSummary> {
  const { data } = await client.get<SuggestionSummary>('/library/import-suggestions/summary')
  return data
}

export async function applySuggestions(
  body: SuggestionApplyRequest,
): Promise<SuggestionApplyResult> {
  const { data } = await client.post<SuggestionApplyResult>(
    '/library/import-suggestions/apply',
    body,
  )
  return data
}

export async function rejectSuggestions(
  body: SuggestionRejectRequest,
): Promise<SuggestionRejectResult> {
  const { data } = await client.post<SuggestionRejectResult>(
    '/library/import-suggestions/reject',
    body,
  )
  return data
}
