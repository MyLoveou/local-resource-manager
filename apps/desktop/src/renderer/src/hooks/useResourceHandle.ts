import {
  patchResource as patchResourceApi,
  postResourceCover as postCoverApi,
  postResourceSubtitle as postSubtitleApi,
  postResourceTodo as postTodoApi,
  patchResourceTodo as patchTodoApi,
  deleteResourceTodo as deleteTodoApi,
  deleteResource as deleteResourceApi,
  restoreResource as restoreResourceApi,
  purgeResource as purgeResourceApi,
  batchResources as batchResourcesApi,
} from '@/infrastructure/http'
import type { Resource } from '@/domain'
import type { ResourcePatch, TodoPatch, ResourceBatchAction, ResourceBatchResult } from '@/infrastructure/http/resources'

export function useResourceHandle() {
  const patchResource = (resourceId: number, patch: ResourcePatch): Promise<Resource> => {
    return patchResourceApi(resourceId, patch)
  }

  const replaceCover = (resourceId: number, path: string): Promise<Resource> => {
    return postCoverApi(resourceId, path)
  }

  const addSubtitle = (resourceId: number, path: string): Promise<Resource> => {
    return postSubtitleApi(resourceId, path)
  }

  const addTodo = (resourceId: number, content: string): Promise<Resource> => {
    return postTodoApi(resourceId, content)
  }

  const patchTodo = (resourceId: number, todoId: number, patch: TodoPatch): Promise<Resource> => {
    return patchTodoApi(resourceId, todoId, patch)
  }

  const removeTodo = (resourceId: number, todoId: number): Promise<Resource> => {
    return deleteTodoApi(resourceId, todoId)
  }

  const deleteResource = (resourceId: number): Promise<Resource> => {
    return deleteResourceApi(resourceId)
  }

  const restoreResource = (resourceId: number): Promise<Resource> => {
    return restoreResourceApi(resourceId)
  }

  const purgeResource = (resourceId: number): Promise<{ ok: boolean }> => {
    return purgeResourceApi(resourceId)
  }

  const batchResources = (
    action: ResourceBatchAction,
    ids: number[],
    tagNames?: string[],
  ): Promise<ResourceBatchResult> => {
    return batchResourcesApi(action, ids, tagNames)
  }

  return {
    patchResource,
    replaceCover,
    addSubtitle,
    addTodo,
    patchTodo,
    removeTodo,
    deleteResource,
    restoreResource,
    purgeResource,
    batchResources,
  }
}
