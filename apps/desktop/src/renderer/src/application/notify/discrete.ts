import { createDiscreteApi, type DiscreteApi } from 'naive-ui'

let apis: DiscreteApi<'message' | 'notification' | 'dialog' | 'loadingBar'> | null = null

export function initNotify(): void {
  if (apis) return
  apis = createDiscreteApi(['message', 'notification', 'dialog', 'loadingBar'], {
    messageProviderProps: { max: 3, placement: 'top', duration: 3000 },
    notificationProviderProps: { max: 5, placement: 'bottom-right' },
  })
}

export function getDiscrete(): DiscreteApi<'message' | 'notification' | 'dialog' | 'loadingBar'> {
  if (!apis) initNotify()
  return apis!
}
