export interface CharacterBrief {
  id: number
  name: string
  workId?: number | null
  workName?: string | null
}

export interface Character {
  id: number
  name: string
  workId?: number | null
  workName?: string | null
  description?: string | null
  coverResourceId?: number | null
  coverPath?: string | null
  aliases: string[]
  resourceCount: number
  createdAt?: string | null
  updatedAt?: string | null
}

export interface Work {
  id: number
  name: string
  description?: string | null
}

export interface CharacterInput {
  name: string
  workName?: string | null
  description?: string | null
  coverResourceId?: number | null
  aliases?: string[]
}
