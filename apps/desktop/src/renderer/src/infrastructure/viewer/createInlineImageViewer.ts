/**
 * Viewer.js 的唯一入口。业务组件只依赖本模块的 setSrc/destroy/resize，禁止直接 import viewerjs。
 */
import Viewer from 'viewerjs'
import 'viewerjs/dist/viewer.css'

export interface InlineImageViewer {
  setSrc: (url: string) => void
  resize: () => void
  destroy: () => void
}

type ViewerWithRender = Viewer & {
  render?: () => void
  initImage?: (done?: () => void) => void
  renderImage?: () => void
}

export function createInlineImageViewer(
  host: HTMLElement,
  hooks?: { onError?: () => void; onLoad?: () => void }
): InlineImageViewer {
  host.replaceChildren()
  const img = document.createElement('img')
  img.alt = ''
  img.className = 'image-viewer-source'
  host.appendChild(img)

  const options: Viewer.Options = {
    inline: true,
    navbar: false,
    title: false,
    tooltip: false,
    movable: true,
    zoomable: true,
    rotatable: true,
    scalable: true,
    fullscreen: false,
    button: false,
    backdrop: false,
    keyboard: false,
    focus: false,
    transition: false,
    slideOnTouch: false,
    zIndexInline: 1,
    minWidth: 0,
    minHeight: 0,
    toolbar: {
      zoomIn: 1,
      zoomOut: 1,
      oneToOne: 1,
      reset: 1,
      rotateLeft: 1,
      rotateRight: 1,
      flipHorizontal: 1,
      flipVertical: 1,
    },
  }

  let instance: ViewerWithRender | null = null

  function resize(): void {
    if (!instance) return
    instance.render?.()
    instance.initImage?.(() => {
      instance?.renderImage?.()
    })
  }

  function ensureInstance(): void {
    if (instance) return
    try {
      instance = new Viewer(img, options)
    } catch {
      instance = null
      hooks?.onError?.()
    }
  }

  img.addEventListener('error', () => {
    hooks?.onError?.()
  })
  img.addEventListener('load', () => {
    hooks?.onLoad?.()
  })

  function setSrc(url: string): void {
    const first = instance === null
    img.src = url
    ensureInstance()
    if (first || !instance) return
    instance.update()
  }

  function destroy(): void {
    instance?.destroy()
    instance = null
    host.replaceChildren()
  }

  return { setSrc, resize, destroy }
}
