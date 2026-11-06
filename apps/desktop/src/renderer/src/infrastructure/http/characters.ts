import client from './client'
import type { Character, CharacterInput, Collection, Work } from '@/domain'

export async function listCharacters(q?: string, workId?: number): Promise<Character[]> {
  const { data } = await client.get<{ items: Character[] }>('/library/characters', {
    params: { q, workId },
  })
  return data.items
}

export async function getCharacter(id: number): Promise<Character> {
  const { data } = await client.get<Character>(`/library/characters/${id}`)
  return data
}

export async function createCharacter(body: CharacterInput): Promise<Character> {
  const { data } = await client.post<Character>('/library/characters', body)
  return data
}

export async function patchCharacter(
  id: number,
  body: Partial<CharacterInput>,
): Promise<Character> {
  const { data } = await client.patch<Character>(`/library/characters/${id}`, body)
  return data
}

export async function deleteCharacter(id: number): Promise<void> {
  await client.delete(`/library/characters/${id}`)
}

export async function mergeCharacter(targetId: number, sourceId: number): Promise<Character> {
  const { data } = await client.post<Character>(`/library/characters/${targetId}/merge`, {
    sourceId,
  })
  return data
}

export async function getCharacterCollections(id: number): Promise<Collection[]> {
  const { data } = await client.get<Collection[]>(`/library/characters/${id}/collections`)
  return data
}

export async function listWorks(): Promise<Work[]> {
  const { data } = await client.get<{ items: Work[] }>('/library/characters/works')
  return data.items
}
