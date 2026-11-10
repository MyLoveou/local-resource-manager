/** 提示词工作台的设置读写。 */
import { putPromptSettings } from '@/infrastructure/http/prompts'

export async function persistShowNsfw(value: boolean): Promise<void> {
  await putPromptSettings({ showNsfw: value })
}
