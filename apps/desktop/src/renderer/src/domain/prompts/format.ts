/** 提示词工作台的纯函数：拼接、热度压缩、拼音、图片缩放。 */

export interface PickedTag {
  en: string
  zh: string
  weight: number
}

/** 模型前缀可能以逗号结尾，拼上前要先清理，否则出现双重逗号。 */
export function trimEnd(text: string): string {
  return text.replace(/[\s,，]+$/, '')
}

/** 把已选标签拼成提示词；权重不为 1 时写成 (tag:1.2)。 */
export function compose(list: PickedTag[], head: string): string {
  const body = list
    .map((item) => (item.weight === 1 ? item.en : `(${item.en}:${item.weight.toFixed(1)})`))
    .join(', ')
  if (!head) return body
  return body ? `${head}, ${body}` : head
}

/** 使用量显示：5975112 → 6.0M，106043 → 106K。 */
export function compact(value: number): string {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`
  if (value >= 1_000) return `${(value / 1_000).toFixed(0)}K`
  return String(value)
}

/** 用内置拼音表把中文转成全拼，用于首字母/全拼搜索。 */
export function pinyinOf(zh: string, dict: Record<string, string>): string {
  let out = ''
  for (const char of zh) out += dict[char]?.split(',')[0] ?? char
  return out
}

/** 缩到 max 边长的 JPEG data URL，避免存档列表被大图撑爆。 */
export function shrinkImage(file: File, max = 384): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onerror = () => reject(new Error('读取图片失败'))
    reader.onload = () => {
      const image = new Image()
      image.onerror = () => reject(new Error('解析图片失败'))
      image.onload = () => {
        const scale = Math.min(1, max / Math.max(image.width, image.height))
        const canvas = document.createElement('canvas')
        canvas.width = Math.round(image.width * scale)
        canvas.height = Math.round(image.height * scale)
        const ctx = canvas.getContext('2d')
        if (!ctx) {
          reject(new Error('画布不可用'))
          return
        }
        ctx.drawImage(image, 0, 0, canvas.width, canvas.height)
        resolve(canvas.toDataURL('image/jpeg', 0.82))
      }
      image.src = String(reader.result)
    }
    reader.readAsDataURL(file)
  })
}
