import type { CharacterBrief } from './character'

export interface PersonBrief {
  id: number
  name: string
}

export interface Person {
  id: number
  name: string
  description?: string | null
  coverResourceId?: number | null
  coverPath?: string | null
  aliases: string[]
  resourceCount: number
  characters?: CharacterBrief[]
  createdAt?: string | null
  updatedAt?: string | null
}

export interface PersonInput {
  name: string
  description?: string | null
  coverResourceId?: number | null
  aliases?: string[]
}
