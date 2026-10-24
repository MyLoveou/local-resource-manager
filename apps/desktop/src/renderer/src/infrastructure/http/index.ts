/**
 * HTTP 层统一出口
 * 用法：import { getOverview } from '@/infrastructure/http'
 */
export { default as client } from './client'
export { getOverview } from './overview'
export { getHome } from './home'
export {
  listCharacters,
  getCharacter,
  createCharacter,
  patchCharacter,
  deleteCharacter,
  mergeCharacter,
  getCharacterCollections,
  listWorks,
} from './characters'
export {
  listPersons,
  getPerson,
  createPerson,
  patchPerson,
  deletePerson,
  mergePerson,
  getPersonCharacters,
} from './persons'
export {
  getCategoryTree,
  createCategory,
  patchCategory,
  deleteCategory,
} from './categories'
export {
  listSavedViews,
  getSavedView,
  createSavedView,
  patchSavedView,
  deleteSavedView,
} from './savedViews'
export {
  getDateNotes,
  getDateNote,
  upsertDateNote,
  deleteDateNote,
  getSavedViewNote,
  upsertSavedViewNote,
  deleteSavedViewNote,
  type TimelineNote,
  type TimelineNoteUpsert,
} from './timelineNotes'
export {
  getResources,
  getResource,
  invalidateResourceCache,
  patchResource,
  postResourceCover,
  postResourceSubtitle,
  postResourceTodo,
  patchResourceTodo,
  deleteResourceTodo,
  deleteResource,
  restoreResource,
  purgeResource,
  batchResources,
} from './resources'
export { createImport, getImportJob } from './imports'
export { getPhotoTimeline, backfillPhotos, backfillThumbnails, rebuildThumbnail } from './photos'
export { getTags, invalidateTags } from './vocab'
export { resolveLibraryMediaUrl, resolveCardImageUrl } from './mediaUrl'
export type { ResourcePatch, TodoPatch, ResourceBatchAction, ResourceBatchResult } from './resources'
export type { ImportCreate, ImportJob, ImportJobCreated, ImportSourceKind } from './imports'
export {
  getSettings,
  patchScrapeSettings,
  backupLibrary,
  prepareRestore,
} from './settings'
export {
  createScrapeJob,
  getScrapeJob,
  listScrapeCandidates,
  previewScrapeCandidate,
  scrapeImageSrc,
  selectScrapeCandidate,
  getLatestScrapeJob,
} from './scrape'
export {
  getAIStatus,
  getAIPerformance,
  updateAIPerformance,
  installAIModel,
  installAnimeTagger,
  buildAIIndex,
  getAIJob,
  searchAI,
  sendAIFeedback,
  removeAIFeedback,
  getAISimilar,
  searchAISimilarFile,
  searchAIFusion,
  analyzeAIImages,
  clearAIJobs,
  getAIJobs,
  getAISuggestions,
  getVLMRuntime,
  selectOllamaBinary,
  startOllamaRuntime,
  selectVLMModel,
  pullVLMModel,
  type AIModelInfo,
  type AIStatus,
  type AIDeviceInfo,
  type AIPerformance,
  type AIJob,
  type AIVLMModelInfo,
  type AIVLMRuntime,
  type AISuggestionItem,
  type AIEntitySuggestion,
  type AISearchResult,
  type AISimilarResult,
  type AIQueryInsight,
  type AIMatchExplanation,
  type AIFusionResult,
  type AIFusionOptions,
} from './ai'
