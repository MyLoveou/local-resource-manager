/**
 * 刮削端点（/scrape）
 */
import client from './client'
import type { Candidate, ScrapeJob, ScrapePreview, ScrapeSelect } from '@/domain'

const scrapeOpts = { timeout: 60000 }

export function scrapeImageSrc(url: string): string {
  const base = String(client.defaults.baseURL ?? '').replace(/\/$/, '')
  return `${base}/scrape/proxy-image?url=${encodeURIComponent(url)}`
}

export async function createScrapeJob(
  resourceId: number,
  force = false,
  query?: string
): Promise<ScrapeJob> {
  const trimmed = query?.trim()
  const { data } = await client.post<ScrapeJob>(
    '/scrape/jobs',
    { resourceId, query: trimmed || undefined },
    { params: { force: force || Boolean(trimmed) }, ...scrapeOpts }
  )
  return data
}

export async function getScrapeJob(jobId: number): Promise<ScrapeJob> {
  const { data } = await client.get<ScrapeJob>(`/scrape/jobs/${jobId}`, scrapeOpts)
  return data
}

export async function listScrapeCandidates(jobId: number): Promise<Candidate[]> {
  const { data } = await client.get<Candidate[]>(`/scrape/jobs/${jobId}/candidates`, scrapeOpts)
  return data
}

export async function previewScrapeCandidate(jobId: number, candidateId: number): Promise<ScrapePreview> {
  const { data } = await client.get<ScrapePreview>(
    `/scrape/jobs/${jobId}/candidates/${candidateId}/preview`,
    scrapeOpts
  )
  return data
}

export async function selectScrapeCandidate(jobId: number, body: ScrapeSelect): Promise<ScrapeJob> {
  const { data } = await client.post<ScrapeJob>(`/scrape/jobs/${jobId}/select`, body, scrapeOpts)
  return data
}

export async function getLatestScrapeJob(resourceId: number): Promise<ScrapeJob> {
  const { data } = await client.get<ScrapeJob>(`/scrape/resources/${resourceId}/latest-job`, scrapeOpts)
  return data
}
