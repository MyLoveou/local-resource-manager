import client from './client'
import type { CharacterBrief, Person, PersonInput } from '@/domain'

export async function listPersons(q?: string): Promise<Person[]> {
  const { data } = await client.get<{ items: Person[] }>('/library/persons', { params: { q } })
  return data.items
}

export async function getPerson(id: number): Promise<Person> {
  const { data } = await client.get<Person>(`/library/persons/${id}`)
  return data
}

export async function createPerson(body: PersonInput): Promise<Person> {
  const { data } = await client.post<Person>('/library/persons', body)
  return data
}

export async function patchPerson(id: number, body: Partial<PersonInput>): Promise<Person> {
  const { data } = await client.patch<Person>(`/library/persons/${id}`, body)
  return data
}

export async function deletePerson(id: number): Promise<void> {
  await client.delete(`/library/persons/${id}`)
}

export async function mergePerson(targetId: number, sourceId: number): Promise<Person> {
  const { data } = await client.post<Person>(`/library/persons/${targetId}/merge`, {
    sourceId,
  })
  return data
}

export async function getPersonCharacters(id: number): Promise<CharacterBrief[]> {
  const { data } = await client.get<CharacterBrief[]>(`/library/persons/${id}/characters`)
  return data
}
