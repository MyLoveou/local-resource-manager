import { patchResource as patchResourceApi, postResourceCover as postCoverApi, deleteResource as deleteResourceApi } from '@/infrastructure/http'
import type { Resource } from '@/domain'
import type { ResourcePatch } from '@/infrastructure/http/resources'

export function useResourceHandle() {
  const patchResource = (resourceId: number, patch: ResourcePatch): Promise<Resource> => {
    return patchResourceApi(resourceId, patch)
  }

  const replaceCover = (resourceId: number, path: string): Promise<Resource> => {
    return postCoverApi(resourceId, path)
  }

  const deleteResource = (resourceId: number): Promise<Resource> => {
    return deleteResourceApi(resourceId)
  }

  return {
    patchResource,
    replaceCover,
    deleteResource,
  }
}
