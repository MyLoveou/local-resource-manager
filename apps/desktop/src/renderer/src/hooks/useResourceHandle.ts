import {
  patchResource as patchResourceApi,
  postResourceCover as postCoverApi,
  postResourceSubtitle as postSubtitleApi,
  postResourceTodo as postTodoApi,
  patchResourceTodo as patchTodoApi,
  deleteResourceTodo as deleteTodoApi,
  deleteResource as deleteResourceApi,
} from '@/infrastructure/http'
import type { Resource } from '@/domain'
import type { ResourcePatch, TodoPatch } from '@/infrastructure/http/resources'

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

  return {
    patchResource,
    replaceCover,
    addSubtitle,
    addTodo,
    patchTodo,
    removeTodo,
    deleteResource,
  }
}
