/**
 * 选中资源在磁盘上的定位路径。与消费方式无关。
 */
import { FILE_ROLE, type Resource, type ResourceFile } from '@/domain'

const REVEAL_SKIP_ROLES = new Set<string>([
  FILE_ROLE.COVER,
  FILE_ROLE.SUBTITLE,
  FILE_ROLE.THUMBNAIL,
])

const REVEAL_ROLE_ORDER = [
  FILE_ROLE.LAUNCH,
  FILE_ROLE.PRIMARY,
  FILE_ROLE.EPISODE,
  FILE_ROLE.EXTRA,
  FILE_ROLE.PAGE,
] as const

function firstPathWithRole(files: ResourceFile[], role: string): string | null {
  return files.find((file) => file.role === role && file.path)?.path ?? null
}

export function launchOrPrimaryPath(resource: Resource | null | undefined): string | null {
  const files = resource?.files ?? []
  return firstPathWithRole(files, FILE_ROLE.LAUNCH) ?? firstPathWithRole(files, FILE_ROLE.PRIMARY)
}

export function revealablePath(resource: Resource | null | undefined): string | null {
  const files = resource?.files ?? []
  for (const role of REVEAL_ROLE_ORDER) {
    const path = firstPathWithRole(files, role)
    if (path) return path
  }
  return files.find((file) => file.path && !REVEAL_SKIP_ROLES.has(file.role ?? ''))?.path ?? null
}
