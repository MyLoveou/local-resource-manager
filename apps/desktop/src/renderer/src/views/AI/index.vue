<template>
  <div class="ai-center">
    <header class="ai-center__head">
      <div>
        <h2>AI 中心</h2>
        <p>本地中文搜图、模型与索引任务；图片不会上传。</p>
      </div>
      <n-tag :type="statusTagType" size="small" :bordered="false">{{ statusLabel }}</n-tag>
    </header>

    <n-button-group class="ai-center__tabs" size="small">
      <n-button
        v-for="tab in tabs"
        :key="tab.value"
        :type="activeTab === tab.value ? 'primary' : 'default'"
        @click="activeTab = tab.value"
      >
        {{ tab.label }}
      </n-button>
    </n-button-group>

    <p v-if="ai.error" class="ai-center__error">{{ ai.error }}</p>

    <template v-if="activeTab === 'search'">
      <section v-if="!ai.modelInstalled" class="ai-setup">
        <h3>安装中文 CLIP 模型</h3>
        <p>首次使用需要下载约 195 MB 的本地模型。安装后可离线用文字搜索图片。</p>
        <div class="ai-setup__actions">
          <n-button
            type="primary"
            :loading="installJobActive"
            :disabled="ai.jobActive"
            @click="install"
          >
            安装模型
          </n-button>
          <span v-if="installJobActive" class="ai-muted">
            {{ jobProgressText }}
          </span>
        </div>
        <n-progress
          v-if="installJobActive"
          type="line"
          :percentage="jobPercent"
          :height="6"
        />
      </section>

      <template v-else>
        <section v-if="!ai.canSearch" class="ai-setup">
          <h3>建立图片索引</h3>
          <p>
            当前图库有 {{ ai.total }} 张图片，已索引 {{ ai.indexed }} 张。
            首次索引只在本机计算向量。
          </p>
          <div class="ai-setup__actions">
            <n-button
              type="primary"
              :loading="indexJobActive"
              :disabled="ai.jobActive"
              @click="index(false)"
            >
              增量索引
            </n-button>
            <n-button
              size="small"
              :disabled="ai.jobActive"
              @click="rebuildIndex"
            >
              重建全部
            </n-button>
            <span v-if="indexJobActive" class="ai-muted">
              {{ jobProgressText }}
            </span>
          </div>
          <n-progress
            v-if="indexJobActive"
            type="line"
            :percentage="jobPercent"
            :height="6"
          />
        </section>

        <template v-else>
          <div class="ai-searchbar">
            <n-input
              v-model:value="query"
              size="small"
              clearable
              placeholder="用中文描述图片，例如：海边、两个人、红帽子"
              :disabled="ai.jobActive"
              @keydown.enter.prevent="runSearch"
            />
            <n-button
              type="primary"
              size="small"
              :loading="ai.searching"
              :disabled="ai.jobActive"
              @click="runSearch"
            >
              搜索
            </n-button>
            <label class="ai-min-score">
              <span>最低分</span>
              <n-input-number
                v-model:value="minScore"
                size="small"
                :min="0"
                :max="1"
                :step="0.05"
                :show-button="false"
              />
            </label>
          </div>
          <div v-if="ai.recentQueries.length" class="ai-history">
            <span class="ai-muted">最近搜索</span>
            <button
              v-for="item in ai.recentQueries"
              :key="item"
              type="button"
              class="ai-history__item"
              @click="useRecentQuery(item)"
            >
              {{ item }}
            </button>
            <button type="button" class="ai-history__clear" @click="ai.clearRecentQueries()">
              清除
            </button>
          </div>
          <p v-if="indexJobActive" class="ai-muted">索引重建中，完成后即可搜索。</p>
          <p v-else-if="ai.jobActive" class="ai-muted">AI 任务运行中，暂不能开始搜索。</p>
          <p class="ai-muted">
            已索引 {{ ai.results?.indexed ?? ai.indexed }} / {{ ai.total }} 张
            <template v-if="ai.results">
              · 匹配 {{ ai.results.matched }} 张 · 显示 {{ ai.results.returned }} 张
              <template v-if="ai.results.captionMatched">
                · 文案命中 {{ ai.results.captionMatched }} 张
              </template>
              <template v-if="ai.results.filteredLowScore">
                · 低于阈值 {{ ai.results.filteredLowScore }} 张
              </template>
              <template v-if="ai.results.feedbackAdjusted">
                · 反馈重排 {{ ai.results.feedbackAdjusted }} 张
              </template>
            </template>
          </p>
          <div v-if="ai.results?.filters.length" class="ai-filters">
            <n-tag v-for="filter in ai.results.filters" :key="filter" size="small" :bordered="false">
              {{ filter }}
            </n-tag>
          </div>

          <AIInsightPanel :insight="ai.results?.queryInsight ?? null" />

          <div v-if="ai.searching" class="ai-empty">
            <n-spin size="small" /> 正在计算相似度
          </div>
          <div v-else-if="ai.results?.items.length" class="ai-results">
            <div v-if="feedbackNotice" class="ai-feedback-notice">{{ feedbackNotice }}</div>
            <div v-for="(item, index) in ai.results.items" :key="item.id" class="ai-result-item">
              <button
                type="button"
                class="ai-result"
                :title="matchReason(ai.results.explanations[index])"
                @click="openResult(item)"
              >
                <img :src="resolveCardImageUrl(item)" :alt="item.title" loading="lazy" />
                <span class="ai-result__score">
                  {{ searchScoreLabel(ai.results.scores[index] ?? 0) }}
                </span>
                <span class="ai-result__title">{{ item.title }}</span>
                <span v-if="matchReason(ai.results.explanations[index])" class="ai-result__why">
                  {{ matchReason(ai.results.explanations[index]) }}
                </span>
              </button>
              <div class="ai-result__feedback">
                <button
                  type="button"
                  :class="{ 'is-relevant': feedbackMark(item) === 'relevant' }"
                  :aria-pressed="feedbackMark(item) === 'relevant'"
                  :title="
                    feedbackMark(item) === 'relevant'
                      ? '已标为相关，再次点击取消'
                      : '标记为相关'
                  "
                  @click.stop="sendFeedback(item, index, 'relevant')"
                >
                  相关
                </button>
                <button
                  type="button"
                  :class="{ 'is-irrelevant': feedbackMark(item) === 'irrelevant' }"
                  :aria-pressed="feedbackMark(item) === 'irrelevant'"
                  :title="
                    feedbackMark(item) === 'irrelevant'
                      ? '已标为不相关，再次点击取消'
                      : '标记为不相关'
                  "
                  @click.stop="sendFeedback(item, index, 'irrelevant')"
                >
                  不相关
                </button>
              </div>
              <p v-if="feedbackMark(item)" class="ai-result__feedback-state">
                {{
                  feedbackMark(item) === 'relevant'
                    ? '已标为相关，再次点击可取消'
                    : '已标为不相关，再次点击可取消'
                }}
              </p>
            </div>
          </div>
          <div v-else-if="ai.results && ai.results.matched === 0" class="ai-empty">
            没有符合当前特征的图片。
          </div>
          <div v-else-if="ai.results" class="ai-empty">
            没有找到相近图片，换一种说法试试。
          </div>
          <div v-else class="ai-empty">
            输入描述后开始搜索。
          </div>
        </template>
      </template>
    </template>

    <template v-else-if="activeTab === 'similar'">
      <input
        ref="fileInput"
        class="ai-file-input"
        type="file"
        accept="image/*"
        @change="onFileChange"
      />
      <section
        v-if="!similarSource && !externalPreview"
        class="ai-setup"
        @dragover.prevent
        @drop.prevent="onDrop"
      >
        <h3>以图搜图</h3>
        <p>选择本地图片，或从图片查看器 / Inspector 的「找相似」进入。也可以把图片拖到这里，或按 Ctrl/Cmd+V 粘贴。</p>
        <div class="ai-setup__actions">
          <n-button type="primary" size="small" @click="chooseFile">选择本地图片</n-button>
        </div>
      </section>

      <template v-else>
        <section
          class="ai-similar-source"
          @dragover.prevent
          @drop.prevent="onDrop"
        >
          <img
            :src="similarSource ? resolveCardImageUrl(similarSource) : externalPreview"
            :alt="similarSource?.title ?? externalName"
          />
          <div>
            <strong>{{ similarSource?.title ?? externalName }}</strong>
            <p class="ai-muted">查询图不会出现在结果中。可拖入或粘贴另一张图片。</p>
            <n-button size="tiny" quaternary @click="chooseFile">选择其他图片</n-button>
          </div>
        </section>

        <AIInsightPanel :insight="similar?.queryInsight ?? null" />

        <div class="ai-similar-modes">
          <n-button-group size="small">
            <n-button
              v-for="mode in similarModes"
              :key="mode.value"
              :type="similarMode === mode.value ? 'primary' : 'default'"
              @click="changeSimilarMode(mode.value)"
            >
              {{ mode.label }}
            </n-button>
          </n-button-group>
          <span class="ai-muted">
            已索引 {{ similar?.indexed ?? 0 }} 张
            · 返回 {{ similar?.returned ?? 0 }} 张
          </span>
        </div>

        <div v-if="similarSource" class="ai-fusionbar">
          <n-input
            v-model:value="fusionText"
            size="small"
            clearable
            placeholder="像这张图，但要有红帽子 / 室内 / 两个人"
            :disabled="ai.jobActive"
            @keydown.enter.prevent="runFusion"
          />
          <n-checkbox v-model:checked="fusionStrict" :disabled="ai.jobActive">严格匹配</n-checkbox>
          <n-button
            type="primary"
            size="small"
            :loading="fusionLoading"
            :disabled="ai.jobActive || !fusionText.trim()"
            @click="runFusion"
          >
            图文融合
          </n-button>
        </div>

        <p v-if="fusionError" class="ai-center__error">{{ fusionError }}</p>
        <p v-if="similarError && !fusion" class="ai-center__error">{{ similarError }}</p>
        <div v-if="similarLoading && !fusionLoading" class="ai-empty">
          <n-spin size="small" /> 正在计算相似度
        </div>

        <div v-if="fusionLoading" class="ai-empty">
          <n-spin size="small" /> 正在融合图片和文字
        </div>

        <section v-if="fusion" class="ai-panel">
          <div class="ai-panel__row">
            <strong>图文融合</strong>
            <n-tag size="small" :bordered="false">{{ fusionText }}</n-tag>
          </div>
          <p class="ai-muted">
            已索引 {{ fusion.indexed }} 张 · 匹配 {{ fusion.matched }} 张
            · 显示 {{ fusion.returned }} 张
          </p>
          <div v-if="fusion.filters.length" class="ai-filters">
            <n-tag v-for="filter in fusion.filters" :key="filter" size="small" :bordered="false">
              {{ filter }}
            </n-tag>
          </div>
          <div v-if="fusion.items.length" class="ai-results">
            <button
              v-for="(item, index) in fusion.items"
              :key="`fusion-${item.id}`"
              type="button"
              class="ai-result"
              @click="openFusionResult(item)"
            >
              <img :src="resolveCardImageUrl(item)" :alt="item.title" loading="lazy" />
              <span class="ai-result__score">
                {{ scoreLabel(fusion.scores[index] ?? 0) }}
              </span>
              <span class="ai-result__title">{{ item.title }}</span>
            </button>
          </div>
          <div v-else class="ai-empty">没有同时满足图片和文字条件的结果。</div>
        </section>

        <template v-else-if="similar && !fusionLoading">
          <section v-if="similar.duplicates.length" class="ai-panel">
            <div class="ai-panel__row">
              <strong>近似重复</strong>
              <n-tag size="small" :bordered="false">{{ similar.duplicates.length }} 张</n-tag>
            </div>
            <div class="ai-results">
              <button
                v-for="(item, index) in similar.duplicates"
                :key="`dup-${item.id}`"
                type="button"
                class="ai-result"
                @click="openDuplicateResult(item)"
              >
                <img :src="resolveCardImageUrl(item)" :alt="item.title" loading="lazy" />
                <span class="ai-result__score">重复 {{ ((similar.duplicateScores[index] ?? 0) * 100).toFixed(0) }}%</span>
                <span class="ai-result__title">{{ item.title }}</span>
                <span
                  v-if="matchReason(similar.duplicateExplanations[index])"
                  class="ai-result__why"
                >
                  {{ matchReason(similar.duplicateExplanations[index]) }}
                </span>
              </button>
            </div>
          </section>

          <section v-if="similar.items.length" class="ai-panel">
            <div class="ai-panel__row">
              <strong>相似图片</strong>
              <n-tag size="small" :bordered="false">{{ similar.items.length }} 张</n-tag>
            </div>
            <div class="ai-results">
              <button
                v-for="(item, index) in similar.items"
                :key="`similar-${item.id}`"
                type="button"
                class="ai-result"
                @click="openSimilarResult(item)"
              >
                <img :src="resolveCardImageUrl(item)" :alt="item.title" loading="lazy" />
                <span class="ai-result__score">
                  {{ scoreLabel(similar.scores[index] ?? 0) }}
                </span>
                <span class="ai-result__title">{{ item.title }}</span>
                <span
                  v-if="matchReason(similar.explanations[index])"
                  class="ai-result__why"
                >
                  {{ matchReason(similar.explanations[index]) }}
                </span>
              </button>
            </div>
          </section>

          <div v-if="similar.duplicates.length === 0 && similar.items.length === 0" class="ai-empty">
            没有找到相近图片。
          </div>
        </template>
      </template>
    </template>

    <section v-else-if="activeTab === 'models'" class="ai-panel">
      <div class="ai-panel__row">
        <strong>中文 CLIP</strong>
        <n-tag size="small" :bordered="false" :type="ai.modelInstalled ? 'success' : 'warning'">
          {{ ai.modelInstalled ? '已安装' : '未安装' }}
        </n-tag>
      </div>
      <p class="ai-muted">
        Chinese-CLIP ViT-B/16 + YOLOv8n 人物检测 · 512 维 · 约 195 MB · 本地 CPU 推理
      </p>
      <p class="ai-muted">
        已索引 {{ ai.status?.indexed ?? 0 }} 张 · 人数特征
        {{ ai.status?.personCountIndexed ?? 0 }} 张
      </p>
      <p class="ai-muted">
        模型会下载到本机数据目录；不会把图片或描述发到外部服务。
      </p>
      <div class="ai-panel__actions">
        <n-button
          v-if="!ai.modelInstalled"
          type="primary"
          :loading="installJobActive"
          :disabled="ai.jobActive"
          @click="install"
        >
          安装模型
        </n-button>
        <n-button
          v-else
          :loading="indexJobActive"
          :disabled="ai.jobActive"
          @click="index(false)"
        >
          增量索引
        </n-button>
        <n-button
          v-if="ai.modelInstalled"
          size="small"
          :disabled="ai.jobActive"
          @click="rebuildIndex"
        >
          重建全部
        </n-button>
      </div>
      <p class="ai-muted">建立索引只计算 CLIP/人数/hash，不会自动分析文案。</p>
      <n-progress
        v-if="installJobActive || indexJobActive"
        class="ai-panel__progress"
        type="line"
        :percentage="jobPercent"
        :height="6"
      />
      <p v-if="installJobActive || indexJobActive" class="ai-muted">{{ jobProgressText }}</p>

      <div class="ai-panel__divider" />
      <div class="ai-panel__row">
        <strong>文案 / 标签</strong>
        <n-tag size="small" :bordered="false" :type="ai.status?.captionReady ? 'success' : 'warning'">
          {{ ai.status?.captionReady ? 'VLM 可用' : '未配置 VLM' }}
        </n-tag>
      </div>
      <p class="ai-muted">
        已分析 {{ ai.status?.captionIndexed ?? 0 }} 张
        <template v-if="ai.status?.captionReady"> · {{ ai.status?.captionModel }}</template>
      </p>
      <template v-if="ai.status?.captionReady">
        <div class="ai-panel__actions">
          <n-button
            size="small"
            :loading="captionJobActive"
            :disabled="ai.jobActive"
            @click="analyzeCaptions(true)"
          >
            分析未分析图片
          </n-button>
          <n-button
            size="small"
            quaternary
            :disabled="ai.jobActive"
            @click="analyzeCaptions(false)"
          >
            重新分析全部
          </n-button>
        </div>
        <p class="ai-muted">分析文案不会重建中文 CLIP 索引；可单独重跑全部或只补未分析的图片。</p>
      </template>
      <p v-if="!ai.status?.vlmRuntimeReady" class="ai-muted">
        未检测到 Ollama。请先安装、选择本地 ollama.exe，或手动启动本地服务。
      </p>
      <template v-if="!ai.status?.vlmRuntimeReady">
        <div class="ai-panel__actions">
          <n-button size="small" :loading="detectingOllama" @click="detectOllama">
            检测 Ollama
          </n-button>
          <n-button size="small" @click="chooseOllama">选择程序</n-button>
          <n-button size="small" type="primary" @click="installOllama">
            下载安装
          </n-button>
          <n-button
            v-if="ai.vlmRuntime?.detected && !ai.vlmRuntime?.running"
            size="small"
            type="primary"
            :loading="startingOllama"
            @click="startOllama"
          >
            启动 Ollama
          </n-button>
        </div>
        <p v-if="ai.vlmRuntime?.binaryPath" class="ai-muted">
          已找到：{{ ai.vlmRuntime.binaryPath }}
        </p>
        <p v-if="ai.vlmRuntime?.error" class="ai-center__error">
          {{ ai.vlmRuntime.error }}
        </p>
      </template>
      <template v-else>
        <p class="ai-muted">
          下载视觉模型。推荐 <code>qwen2.5vl:3b</code>（中文、视觉、约 3.2GB）；
          也可输入其他 Ollama 视觉模型，例如 <code>qwen2.5vl:7b</code>、<code>llava:7b</code>。
        </p>
        <div class="ai-fusionbar">
          <n-input
            v-model:value="vlmModel"
            size="small"
            placeholder="qwen2.5vl:3b"
            :disabled="vlmPullActive"
          />
          <n-button
            type="primary"
            size="small"
            :loading="vlmPullActive"
            :disabled="!vlmModel.trim() || ai.jobActive"
            @click="pullVLM"
          >
            下载模型
          </n-button>
        </div>
      </template>
      <div v-if="ai.vlmModelDetails.length" class="ai-model-list">
        <p class="ai-muted">已下载模型</p>
        <div
          v-for="model in ai.vlmModelDetails"
          :key="model.name"
          class="ai-model-row"
        >
          <div class="ai-model-row__main">
            <strong>{{ model.name }}</strong>
            <p class="ai-muted">
              {{ formatBytes(model.sizeBytes) }} ·
              {{ model.supportsVision ? '支持视觉分析' : '不支持视觉分析' }}
            </p>
          </div>
          <n-tag v-if="model.selected" size="small" type="success" :bordered="false">
            当前
          </n-tag>
          <n-button
            v-else-if="model.supportsVision"
            size="tiny"
            :loading="selectingModel === model.name"
            :disabled="ai.jobActive"
            @click="switchVLMModel(model.name)"
          >
            切换
          </n-button>
          <n-tag v-else size="small" type="warning" :bordered="false">不可用于文案</n-tag>
        </div>
      </div>
      <p v-else-if="ai.status?.vlmRuntimeReady" class="ai-muted">尚未下载视觉模型。</p>
      <n-progress
        v-if="captionJobActive || vlmPullActive"
        class="ai-panel__progress"
        type="line"
        :percentage="jobPercent"
        :height="6"
      />
      <p v-if="captionJobActive || vlmPullActive" class="ai-muted">{{ jobProgressText }}</p>
    </section>

    <section v-else-if="activeTab === 'jobs'" class="ai-panel">
      <div class="ai-panel__row">
        <strong>{{ ai.job ? jobTitle(ai.job.kind) : 'AI 任务' }}</strong>
        <n-tag v-if="ai.job" size="small" :bordered="false" :type="jobTagType(ai.job.status)">
          {{ jobStatusText(ai.job.status) }}
        </n-tag>
      </div>
      <template v-if="ai.job">
        <n-progress
          v-if="ai.job.status === 'queued' || ai.job.status === 'running'"
          type="line"
          :percentage="jobPercent"
          :height="6"
        />
        <p class="ai-muted">{{ ai.job.message || jobProgressText }}</p>
        <p v-if="ai.job.failed" class="ai-muted">失败 {{ ai.job.failed }} 张</p>
        <p v-if="ai.job.status === 'error'" class="ai-center__error">{{ ai.job.message }}</p>
      </template>
      <p v-else class="ai-muted">安装模型、建立索引或分析文案后，任务进度会显示在这里。</p>

      <div class="ai-panel__divider" />
      <div class="ai-panel__row">
        <strong>任务历史</strong>
        <n-tag size="small" :bordered="false">{{ ai.jobHistory.length }}</n-tag>
      </div>
      <div v-if="ai.jobHistory.length" class="ai-job-list">
        <div v-for="item in ai.jobHistory" :key="item.id" class="ai-job-row">
          <div class="ai-job-row__main">
            <strong>{{ jobTitle(item.kind) }}</strong>
            <p class="ai-muted">
              {{ formatJobTime(item.createdAt) }} · {{ item.message || '无详情' }}
            </p>
          </div>
          <span v-if="item.failed" class="ai-job-row__failed">失败 {{ item.failed }}</span>
          <n-tag size="small" :bordered="false" :type="jobTagType(item.status)">
            {{ jobStatusText(item.status) }}
          </n-tag>
        </div>
      </div>
      <p v-else class="ai-muted">还没有 AI 操作历史。</p>
    </section>

    <section v-else-if="activeTab === 'suggestions'" class="ai-panel">
      <div class="ai-panel__row">
        <strong>AI 建议</strong>
        <n-tag size="small" :bordered="false">{{ ai.suggestions.length }} 张</n-tag>
        <n-button size="tiny" :loading="ai.suggestionsLoading" @click="ai.refreshSuggestions()">
          刷新
        </n-button>
      </div>
      <p class="ai-muted">
        审核后应用。标签和实体只会添加，不会覆盖已有内容；不会自动创建角色或合集。
      </p>
      <div v-if="ai.suggestionsLoading" class="ai-empty">
        <n-spin size="small" /> 正在读取建议
      </div>
      <div v-else-if="!ai.suggestions.length" class="ai-empty">
        暂无建议。先在图片任务里完成 VLM 文案分析，或补充已有角色/扮演者/合集。
      </div>
      <div v-else class="ai-suggestion-list">
        <article
          v-for="item in ai.suggestions"
          :key="item.resourceId"
          class="ai-suggestion"
        >
          <button
            type="button"
            class="ai-suggestion__cover"
            :title="`打开 ${item.title || `资源 #${item.resourceId}`}`"
            @click="openSuggestion(item)"
          >
            <img
              v-if="item.thumbnailPath"
              :src="resolveCardImageUrl({ thumbnailPath: item.thumbnailPath })"
              :alt="item.title"
              loading="lazy"
            />
            <span v-else>无图</span>
          </button>
          <div class="ai-suggestion__main">
            <div class="ai-panel__row">
              <strong>{{ item.title || `资源 #${item.resourceId}` }}</strong>
              <n-tag size="tiny" :bordered="false">#{{ item.resourceId }}</n-tag>
            </div>
            <div v-if="item.tags.length" class="ai-suggestion__group">
              <span>标签（可多选）</span>
              <button
                v-for="tag in item.tags"
                :key="`tag-${item.resourceId}-${tag}`"
                type="button"
                class="ai-suggestion__tag"
                :class="{ active: isTagSelected(item, tag) }"
                :disabled="suggestionBusy === item.resourceId"
                @click="toggleTag(item, tag)"
              >
                {{ tag }}
              </button>
              <button
                type="button"
                class="ai-suggestion__select"
                @click="selectAllTags(item)"
              >
                全选
              </button>
              <button
                v-if="selectedTagCount(item)"
                type="button"
                class="ai-suggestion__select"
                @click="clearSelectedTags(item)"
              >
                清空
              </button>
            </div>
            <div v-if="item.characters.length" class="ai-suggestion__group">
              <span>角色</span>
              <button
                v-for="entity in item.characters"
                :key="`character-${item.resourceId}-${entity.id}`"
                type="button"
                class="ai-suggestion__apply"
                :disabled="suggestionBusy === item.resourceId"
                @click="applyEntity(item, 'characters', entity)"
              >
                + {{ entity.name }}
              </button>
            </div>
            <div v-if="item.persons.length" class="ai-suggestion__group">
              <span>扮演者</span>
              <button
                v-for="entity in item.persons"
                :key="`person-${item.resourceId}-${entity.id}`"
                type="button"
                class="ai-suggestion__apply"
                :disabled="suggestionBusy === item.resourceId"
                @click="applyEntity(item, 'persons', entity)"
              >
                + {{ entity.name }}
              </button>
            </div>
            <div v-if="item.collections.length" class="ai-suggestion__group">
              <span>合集</span>
              <button
                v-for="entity in item.collections"
                :key="`collection-${item.resourceId}-${entity.id}`"
                type="button"
                class="ai-suggestion__apply"
                :disabled="suggestionBusy === item.resourceId"
                @click="applyEntity(item, 'collections', entity)"
              >
                + {{ entity.name }}
              </button>
            </div>
          </div>
          <n-button
            v-if="item.tags.length"
            size="tiny"
            :loading="suggestionBusy === item.resourceId"
            :disabled="selectedTagCount(item) === 0"
            @click="applyTags(item)"
          >
            应用选中 {{ selectedTagCount(item) }}
          </n-button>
        </article>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  NButton,
  NButtonGroup,
  NCheckbox,
  NInput,
  NInputNumber,
  NProgress,
  NSpin,
  NTag,
} from 'naive-ui'
import { useAIStore } from '@/application/stores/ai'
import { openResource } from '@/infrastructure/consume/consumeResource'
import { addCollectionItems } from '@/infrastructure/http/collections'
import { batchResources, getAISimilar, getResource, resolveCardImageUrl, searchAIFusion, searchAISimilarFile } from '@/infrastructure/http'
import type { AIEntitySuggestion, AIFusionResult, AIMatchExplanation, AISimilarResult, AISuggestionItem } from '@/infrastructure/http'
import type { Resource } from '@/domain'
import AIInsightPanel from '@/components/AIInsightPanel/index.vue'

const tabs = [
  { value: 'search', label: '搜索' },
  { value: 'similar', label: '找相似' },
  { value: 'models', label: '模型' },
  { value: 'jobs', label: '任务' },
  { value: 'suggestions', label: '建议' },
] as const

const similarModes = [
  { value: 'auto', label: '综合' },
  { value: 'semantic', label: '语义' },
  { value: 'duplicate', label: '近似重复' },
] as const

type TabValue = (typeof tabs)[number]['value']

const ai = useAIStore()
const route = useRoute()
const router = useRouter()
const activeTab = ref<TabValue>(readTab(route.query.tab))
const query = ref(String(route.query.q ?? ''))
const minScore = ref(0.2)
const feedbackMarks = ref<Record<string, 'relevant' | 'irrelevant'>>({})
const feedbackNotice = ref('')

watch(query, (value) => {
  const submitted = ai.results?.queryInsight?.raw ?? ''
  if (value.trim() !== submitted) {
    ai.clearResults()
    feedbackMarks.value = {}
    feedbackNotice.value = ''
  }
})
const similar = ref<AISimilarResult | null>(null)
const similarSource = ref<Resource | null>(null)
const similarLoading = ref(false)
const similarMode = ref<'auto' | 'semantic' | 'duplicate'>('auto')
const similarError = ref('')
const fusionText = ref('')
const fusionStrict = ref(false)
const fusion = ref<AIFusionResult | null>(null)
const fusionLoading = ref(false)
const fusionError = ref('')
const externalFile = ref<File | null>(null)
const externalPreview = ref('')
const externalName = ref('')
const fileInput = ref<HTMLInputElement | null>(null)

function readTab(value: unknown): TabValue {
  return tabs.some((tab) => tab.value === value) ? (value as TabValue) : 'search'
}

const statusLabel = computed(() => {
  if (ai.loading && !ai.status) return '检测中'
  if (ai.status?.dependencyReady === false) return '依赖缺失'
  if (!ai.modelInstalled) return 'AI 未启用'
  if (ai.indexed > 0) return 'AI 就绪'
  return '等待索引'
})

const statusTagType = computed(() => {
  if (!ai.modelInstalled || ai.status?.dependencyReady === false) return 'warning'
  if (ai.indexed > 0) return 'success'
  return 'info'
})

const jobPercent = computed(() => ai.job?.percent ?? 0)
const installJobActive = computed(() => ai.job?.kind === 'install' && ai.jobActive)
const indexJobActive = computed(() => ai.job?.kind === 'index' && ai.jobActive)
const captionJobActive = computed(() => ai.job?.kind === 'caption' && ai.jobActive)
const vlmPullActive = computed(() => ai.job?.kind === 'vlm-pull' && ai.jobActive)
const animeJobActive = computed(() => ai.job?.kind === 'anime-install' && ai.jobActive)
const vlmModel = ref('qwen2.5vl:3b')
const selectingModel = ref('')
const detectingOllama = ref(false)
const startingOllama = ref(false)
const suggestionBusy = ref(0)
const selectedSuggestionTags = ref<Record<number, string[]>>({})
const jobProgressText = computed(() => {
  const job = ai.job
  if (!job) return ''
  if (job.total > 0) return `${job.done}/${job.total}`
  return job.message || ''
})

function jobStatusText(status: string): string {
  switch (status) {
    case 'queued':
      return '排队中'
    case 'running':
      return '进行中'
    case 'done':
      return '已完成'
    case 'error':
      return '失败'
    default:
      return status
  }
}

function jobTagType(status: string): 'default' | 'info' | 'success' | 'warning' | 'error' {
  switch (status) {
    case 'running':
      return 'info'
    case 'done':
      return 'success'
    case 'error':
      return 'error'
    case 'queued':
      return 'warning'
    default:
      return 'default'
  }
}

function jobTitle(kind: string): string {
  if (kind === 'install') return '下载模型'
  if (kind === 'index') return '建立索引'
  if (kind === 'caption') return '分析图片文案'
  if (kind === 'vlm-pull') return '下载 VLM 模型'
  return 'AI 任务'
}

function formatBytes(value: number): string {
  if (!value) return '0 B'
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(0)} KB`
  return `${(value / 1024 / 1024).toFixed(1)} MB`
}

function formatJobTime(value: string): string {
  const date = new Date(value)
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString()
}

function scoreLabel(score: number): string {
  return `相似度 ${score.toFixed(2)}`
}

function searchScoreLabel(score: number): string {
  return `综合 ${score.toFixed(2)}`
}

function feedbackMark(item: Resource): 'relevant' | 'irrelevant' | undefined {
  return item.id == null ? undefined : feedbackMarks.value[item.id]
}

async function sendFeedback(
  item: Resource,
  index: number,
  action: 'relevant' | 'irrelevant',
): Promise<void> {
  const text = query.value.trim()
  if (!text || item.id == null) return
  const current = feedbackMarks.value[item.id]
  const cancel = current === action
  try {
    if (cancel) {
      await ai.removeFeedback(text, item.id)
      delete feedbackMarks.value[item.id]
      feedbackNotice.value = action === 'relevant' ? '已取消相关标记' : '已取消不相关标记'
      return
    }
    await ai.feedback(text, item.id, action, ai.results?.scores[index] ?? 0, index + 1)
    feedbackMarks.value[item.id] = action
    feedbackNotice.value =
      action === 'relevant' ? '已标为相关，再点一次可取消' : '已标为不相关，再点一次可取消'
  } catch {
    feedbackNotice.value = ''
  }
}

function matchReason(explanation?: AIMatchExplanation | null): string {
  return explanation?.reasons?.slice(0, 3).join(' · ') ?? ''
}

async function runSearch(): Promise<void> {
  if (!ai.canSearch) return
  await ai.search(query.value, 30, minScore.value)
  feedbackMarks.value = { ...(ai.results?.feedback ?? {}) }
  feedbackNotice.value = ''
}

async function loadSimilar(resourceId: number): Promise<void> {
  similarLoading.value = true
  similarError.value = ''
  fusion.value = null
  fusionText.value = ''
  fusionError.value = ''
  externalFile.value = null
  externalName.value = ''
  if (externalPreview.value) URL.revokeObjectURL(externalPreview.value)
  externalPreview.value = ''
  try {
    similarSource.value = await getResource(resourceId)
    similar.value = await getAISimilar(resourceId, similarMode.value)
  } catch (error) {
    similarError.value = error instanceof Error ? error.message : '相似搜索失败'
    similar.value = null
  } finally {
    similarLoading.value = false
  }
}

async function changeSimilarMode(mode: 'auto' | 'semantic' | 'duplicate'): Promise<void> {
  similarMode.value = mode
  fusion.value = null
  fusionText.value = ''
  fusionError.value = ''
  if (externalFile.value) {
    await loadExternal(externalFile.value)
    return
  }
  const id = Number(route.query.resourceId)
  if (Number.isFinite(id) && id > 0) await loadSimilar(id)
}

async function chooseFile(): Promise<void> {
  try {
    const api = window.electron
    if (api?.selectImageFile) {
      const picked = await api.selectImageFile()
      if (!picked) return
      const binary = atob(picked.dataBase64)
      const bytes = new Uint8Array(binary.length)
      for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i)
      await loadExternal(new File([bytes], picked.name))
      return
    }
    fileInput.value?.click()
  } catch (error) {
    similarError.value = error instanceof Error ? error.message : '??????'
  }
}

async function loadExternal(file: File): Promise<void> {
  externalFile.value = file
  externalName.value = file.name
  similarSource.value = null
  if (externalPreview.value) URL.revokeObjectURL(externalPreview.value)
  externalPreview.value = URL.createObjectURL(file)
  similarLoading.value = true
  similarError.value = ''
  fusion.value = null
  fusionError.value = ''
  try {
    similar.value = await searchAISimilarFile(file, similarMode.value)
  } catch (error) {
    similar.value = null
    similarError.value = error instanceof Error ? error.message : '相似搜索失败'
  } finally {
    similarLoading.value = false
  }
}

function onFileChange(event: Event): void {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (file) void loadExternal(file)
  ;(event.target as HTMLInputElement).value = ''
}

function onDrop(event: DragEvent): void {
  const file = event.dataTransfer?.files?.[0]
  if (file && file.type.startsWith('image/')) void loadExternal(file)
}

function onPaste(event: ClipboardEvent): void {
  if (activeTab.value !== 'similar') return
  const target = event.target
  if (target instanceof HTMLElement && target.closest('input, textarea, [contenteditable="true"]')) {
    return
  }
  const item = [...(event.clipboardData?.items ?? [])].find((entry) =>
    entry.type.startsWith('image/'),
  )
  const file = item?.getAsFile()
  if (!file) return
  event.preventDefault()
  void loadExternal(file)
}

async function runFusion(): Promise<void> {
  if (!similarSource.value?.id || !fusionText.value.trim() || ai.jobActive) return
  fusionLoading.value = true
  fusionError.value = ''
  try {
    fusion.value = await searchAIFusion(similarSource.value.id, fusionText.value, {
      strict: fusionStrict.value,
    })
  } catch (error) {
    fusion.value = null
    fusionError.value = error instanceof Error ? error.message : '融合搜索失败'
  } finally {
    fusionLoading.value = false
  }
}

function openSimilarResult(item: Resource): void {
  const ids = (similar.value?.items ?? []).flatMap((row) => (row.id == null ? [] : [row.id]))
  void openResource(item, {
    playlist: ids,
    pager: {
      hasMore: () => false,
      loadingMore: () => false,
      loadMore: async () => undefined,
      imageIds: () => ids,
    },
  })
}

function openFusionResult(item: Resource): void {
  const ids = (fusion.value?.items ?? []).flatMap((row) => (row.id == null ? [] : [row.id]))
  void openResource(item, {
    playlist: ids,
    pager: {
      hasMore: () => false,
      loadingMore: () => false,
      loadMore: async () => undefined,
      imageIds: () => ids,
    },
  })
}

function openDuplicateResult(item: Resource): void {
  const ids = (similar.value?.duplicates ?? []).flatMap((row) => (row.id == null ? [] : [row.id]))
  void openResource(item, {
    playlist: ids,
    pager: {
      hasMore: () => false,
      loadingMore: () => false,
      loadMore: async () => undefined,
      imageIds: () => ids,
    },
  })
}

function openSimilarCenter(resourceId: number): void {
  void router.push({ path: '/ai', query: { tab: 'similar', resourceId: String(resourceId) } })
}

async function install(): Promise<void> {
  if (ai.jobActive) return
  await ai.installModel()
}

async function index(full = false): Promise<void> {
  if (ai.jobActive) return
  await ai.buildIndex(full)
}

async function rebuildIndex(): Promise<void> {
  if (ai.jobActive) return
  if (!window.confirm('?????? CLIP ??????????????????')) return
  await ai.buildIndex(true)
}

async function analyzeCaptions(onlyPending = true): Promise<void> {
  if (ai.jobActive) return
  await ai.analyze(undefined, onlyPending)
}

async function switchVLMModel(model: string): Promise<void> {
  if (ai.jobActive || selectingModel.value) return
  selectingModel.value = model
  try {
    await ai.selectVLM(model)
    vlmModel.value = model
  } finally {
    selectingModel.value = ''
  }
}

async function openSuggestion(item: AISuggestionItem): Promise<void> {
  await openResource({ id: item.resourceId, type: 'image' })
}

function selectedTagsFor(item: AISuggestionItem): string[] {
  return selectedSuggestionTags.value[item.resourceId] ?? []
}

function selectedTagCount(item: AISuggestionItem): number {
  return selectedTagsFor(item).length
}

function isTagSelected(item: AISuggestionItem, tag: string): boolean {
  return selectedTagsFor(item).includes(tag)
}

function toggleTag(item: AISuggestionItem, tag: string): void {
  const current = selectedTagsFor(item)
  selectedSuggestionTags.value = {
    ...selectedSuggestionTags.value,
    [item.resourceId]: current.includes(tag)
      ? current.filter((value) => value !== tag)
      : [...current, tag],
  }
}

function selectAllTags(item: AISuggestionItem): void {
  selectedSuggestionTags.value = {
    ...selectedSuggestionTags.value,
    [item.resourceId]: [...item.tags],
  }
}

function clearSelectedTags(item: AISuggestionItem): void {
  selectedSuggestionTags.value = {
    ...selectedSuggestionTags.value,
    [item.resourceId]: [],
  }
}

async function applyTags(item: AISuggestionItem): Promise<void> {
  const tags = selectedTagsFor(item)
  if (!tags.length || item.resourceId == null) return
  suggestionBusy.value = item.resourceId
  try {
    const result = await batchResources('add_tags', [item.resourceId], tags)
    if (result.failed.length) {
      window.alert(result.failed[0]?.message || '应用标签失败')
      return
    }
    clearSelectedTags(item)
    await ai.refreshSuggestions()
  } finally {
    suggestionBusy.value = 0
  }
}

async function applyEntity(
  item: AISuggestionItem,
  kind: 'characters' | 'persons' | 'collections',
  entity: AIEntitySuggestion,
): Promise<void> {
  if (item.resourceId == null) return
  suggestionBusy.value = item.resourceId
  try {
    if (kind === 'collections') {
      await addCollectionItems(entity.id, [item.resourceId])
    } else if (kind === 'characters') {
      const result = await batchResources(
        'add_characters',
        [item.resourceId],
        undefined,
        undefined,
        [entity.id],
      )
      if (result.failed.length) window.alert(result.failed[0]?.message || '??????')
    } else {
      const result = await batchResources(
        'add_persons',
        [item.resourceId],
        undefined,
        undefined,
        undefined,
        [entity.id],
      )
      if (result.failed.length) window.alert(result.failed[0]?.message || '???????')
    }
    await ai.refreshSuggestions()
  } finally {
    suggestionBusy.value = 0
  }
}

async function useRecentQuery(value: string): Promise<void> {
  query.value = value
  await runSearch()
}

async function clearJobHistory(): Promise<void> {
  if (!window.confirm('???? AI ?????')) return
  await ai.clearJobHistory()
}

async function installAnime(): Promise<void> {
  if (ai.jobActive) return
  await ai.installAnime()
}

async function pullVLM(): Promise<void> {
  if (ai.jobActive || !vlmModel.value.trim()) return
  await ai.pullVLM(vlmModel.value.trim())
}

async function detectOllama(): Promise<void> {
  detectingOllama.value = true
  try {
    await ai.refreshVLMRuntime()
    await ai.refresh()
  } finally {
    detectingOllama.value = false
  }
}

async function chooseOllama(): Promise<void> {
  const files = await window.electron?.selectFiles([
    { name: 'Ollama', extensions: ['exe'] },
  ])
  if (files?.[0]) await ai.selectOllama(files[0])
}

async function installOllama(): Promise<void> {
  await window.electron?.openExternal('https://ollama.com/download/windows')
}

async function startOllama(): Promise<void> {
  startingOllama.value = true
  try {
    await ai.startOllama()
  } finally {
    startingOllama.value = false
  }
}

function openResult(item: Resource): void {
  const ids = (ai.results?.items ?? []).flatMap((row) => (row.id == null ? [] : [row.id]))
  void openResource(item, {
    playlist: ids,
    pager: {
      hasMore: () => false,
      loadingMore: () => false,
      loadMore: async () => undefined,
      imageIds: () => ids,
    },
  })
}

watch(
  () => route.query.tab,
  (value) => {
    activeTab.value = readTab(value)
  },
)

watch(
  () => route.query.resourceId,
  async (value) => {
    const id = Number(value)
    if (value && Number.isFinite(id) && id > 0) {
      activeTab.value = 'similar'
      await loadSimilar(id)
    }
  },
)

watch(
  () => ai.status?.captionModel,
  (value) => {
    if (value) vlmModel.value = value
  },
)

onUnmounted(() => {
  window.removeEventListener('paste', onPaste)
  if (externalPreview.value) URL.revokeObjectURL(externalPreview.value)
})

onMounted(async () => {
  window.addEventListener('paste', onPaste)
  await ai.refresh()
  await ai.refreshJobs()
  await ai.refreshSuggestions()
  await ai.refreshVLMRuntime()
  const selected = ai.vlmModelDetails.find((model) => model.selected)?.name
  if (selected) vlmModel.value = selected
  const id = Number(route.query.resourceId)
  if (route.query.tab === 'similar' && Number.isFinite(id) && id > 0) {
    await loadSimilar(id)
  } else if (query.value) {
    await runSearch()
  }
})
</script>

<style scoped lang="less">
.ai-center {
  height: 100%;
  max-width: 1200px;
  margin: 0 auto;
  overflow: auto;
  padding: 20px;
}

.ai-center__head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;

  h2 {
    margin: 0;
    font-size: 20px;
  }

  p {
    margin: 6px 0 0;
    color: var(--sm-color-text-muted);
    font-size: 12px;
  }
}

.ai-center__tabs {
  margin-top: 18px;
}

.ai-center__error {
  margin: 14px 0 0;
  padding: 8px 10px;
  border: 1px solid color-mix(in srgb, var(--sm-color-danger, #d03050) 35%, transparent);
  border-radius: 8px;
  color: var(--sm-color-danger, #d03050);
  font-size: 12px;
}

.ai-setup,
.ai-panel {
  margin-top: 14px;
  padding: 18px;
  border: 1px solid var(--sm-color-border);
  border-radius: 12px;
  background: var(--sm-color-bg-surface);
}

.ai-setup {
  h3 {
    margin: 0;
    font-size: 16px;
  }

  p {
    max-width: 620px;
    margin: 8px 0 14px;
    color: var(--sm-color-text-muted);
    font-size: 12px;
    line-height: 1.7;
  }
}

.ai-setup__actions,
.ai-panel__divider {
  height: 1px;
  margin: 16px 0;
  background: var(--sm-color-border);
}

.ai-panel__actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.ai-setup :deep(.n-progress),
.ai-panel__progress {
  margin-top: 12px;
}

.ai-panel__row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.ai-panel__actions {
  margin-top: 16px;
}

.ai-file-input {
  display: none;
}

.ai-similar-source {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-top: 14px;
  padding: 12px;
  border: 1px solid var(--sm-color-border);
  border-radius: 12px;
  background: var(--sm-color-bg-surface);

  img {
    width: 160px;
    height: 120px;
    object-fit: cover;
    border-radius: 8px;
    background: var(--sm-color-bg-muted);
  }
}

.ai-similar-modes {
  display: flex;
  align-items: center;
  gap: 14px;
  flex-wrap: wrap;
  margin-top: 14px;
}

.ai-fusionbar {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 12px;
  padding: 10px 12px;
  border: 1px solid var(--sm-color-border);
  border-radius: 10px;
  background: var(--sm-color-bg-surface);

  :deep(.n-input) {
    flex: 1;
    min-width: 0;
  }
}

.ai-searchbar {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 18px;
  padding: 12px;
  border: 1px solid var(--sm-color-border);
  border-radius: 10px;
  background: var(--sm-color-bg-surface);
}

.ai-min-score {
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--sm-color-text-muted);
  font-size: 11px;
  white-space: nowrap;

  :deep(.n-input-number) {
    width: 62px;
  }
}

.ai-runtime-hint {
  margin: 8px 0 0;
  padding: 8px 10px;
  border: 1px solid color-mix(in srgb, var(--sm-color-warning, #f0a020) 35%, transparent);
  border-radius: 8px;
  background: color-mix(in srgb, var(--sm-color-warning, #f0a020) 8%, transparent);
  color: var(--sm-color-text);
  font-size: 12px;
}

.ai-muted {
  margin: 8px 0 0;
  color: var(--sm-color-text-muted);
  font-size: 12px;
}

.ai-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;
}

.ai-history {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 8px;

  .ai-runtime-hint {
  margin: 8px 0 0;
  padding: 8px 10px;
  border: 1px solid color-mix(in srgb, var(--sm-color-warning, #f0a020) 35%, transparent);
  border-radius: 8px;
  background: color-mix(in srgb, var(--sm-color-warning, #f0a020) 8%, transparent);
  color: var(--sm-color-text);
  font-size: 12px;
}

.ai-muted {
    margin: 0 4px 0 0;
  }
}

.ai-history__item,
.ai-history__clear {
  padding: 2px 8px;
  border: 1px solid var(--sm-color-border);
  border-radius: 999px;
  background: var(--sm-color-bg-surface);
  color: var(--sm-color-text);
  font-size: 11px;
  cursor: pointer;
}

.ai-history__item:hover {
  border-color: var(--sm-color-accent);
}

.ai-history__clear {
  border-color: transparent;
  color: var(--sm-color-text-muted);
}

.ai-model-list {
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid var(--sm-color-border);
}

.ai-model-row,
.ai-job-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid var(--sm-color-border);
}

.ai-model-row:last-child,
.ai-job-row:last-child {
  border-bottom: 0;
}

.ai-model-row__main,
.ai-job-row__main {
  flex: 1;
  min-width: 0;

  strong {
    display: block;
    font-size: 12px;
    overflow-wrap: anywhere;
  }

  .ai-runtime-hint {
  margin: 8px 0 0;
  padding: 8px 10px;
  border: 1px solid color-mix(in srgb, var(--sm-color-warning, #f0a020) 35%, transparent);
  border-radius: 8px;
  background: color-mix(in srgb, var(--sm-color-warning, #f0a020) 8%, transparent);
  color: var(--sm-color-text);
  font-size: 12px;
}

.ai-muted {
    margin: 4px 0 0;
  }
}

.ai-job-list {
  margin-top: 4px;
}

.ai-suggestion-list {
  margin-top: 8px;
}

.ai-suggestion {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid var(--sm-color-border);
}

.ai-suggestion__cover {
  display: flex;
  flex: 0 0 96px;
  align-items: center;
  justify-content: center;
  width: 96px;
  height: 72px;
  overflow: hidden;
  padding: 0;
  border: 1px solid var(--sm-color-border);
  border-radius: 6px;
  background: var(--sm-color-bg-surface);
  color: var(--sm-color-text-muted);
  font-size: 11px;
  cursor: pointer;

  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
}

.ai-suggestion__tag {
  padding: 1px 6px;
  border: 1px solid var(--sm-color-border);
  border-radius: 999px;
  background: transparent;
  color: var(--sm-color-text-muted);
  font-size: 11px;
  cursor: pointer;
}

.ai-suggestion__tag.active {
  border-color: var(--sm-color-accent);
  background: color-mix(in srgb, var(--sm-color-accent) 12%, transparent);
  color: var(--sm-color-text);
}

.ai-suggestion__select {
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--sm-color-accent);
  font-size: 11px;
  cursor: pointer;
}

.ai-suggestion:last-child {
  border-bottom: 0;
}

.ai-suggestion__main {
  flex: 1;
  min-width: 0;
}

.ai-suggestion__group {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 6px;

  > span {
    color: var(--sm-color-text-muted);
    font-size: 11px;
  }
}

.ai-suggestion__apply {
  padding: 1px 6px;
  border: 1px solid var(--sm-color-border);
  border-radius: 4px;
  background: transparent;
  color: var(--sm-color-text);
  font-size: 11px;
  cursor: pointer;
}

.ai-suggestion__apply:hover {
  border-color: var(--sm-color-accent);
}

.ai-job-row__failed {
  color: var(--sm-color-danger, #d03050);
  font-size: 11px;
}

.ai-results {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  align-items: start;
  gap: 12px;
  margin-top: 14px;
}

.ai-result-item {
  display: flex;
  flex-direction: column;
  min-width: 0;
  height: 100%;
}

.ai-result {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 6px;
  width: 100%;
  min-width: 0;
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--sm-color-text);
  text-align: left;
  cursor: pointer;

  img {
    display: block;
    width: 100%;
    aspect-ratio: 4 / 3;
    object-fit: cover;
    border-radius: 8px;
    background: var(--sm-color-bg-muted);
  }

  &:hover img {
    outline: 2px solid var(--sm-color-accent);
    outline-offset: 2px;
  }
}

.ai-result__score {
  position: absolute;
  top: 6px;
  right: 6px;
  padding: 2px 6px;
  border-radius: 5px;
  background: rgb(0 0 0 / 62%);
  color: #fff;
  font-size: 10px;
}

.ai-result__title {
  overflow: hidden;
  width: 100%;
  font-size: 12px;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.ai-result__why {
  display: -webkit-box;
  overflow: hidden;
  color: var(--sm-color-text-muted);
  font-size: 10px;
  line-height: 1.45;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
}

.ai-result__feedback {
  display: flex;
  gap: 6px;
  margin-top: 2px;

  button {
    padding: 1px 6px;
    border: 1px solid var(--sm-color-border);
    border-radius: 4px;
    background: transparent;
    color: var(--sm-color-text-muted);
    font-size: 10px;
    cursor: pointer;
  }

  button:hover,
  button.active {
    border-color: var(--sm-color-accent);
    color: var(--sm-color-text);
  }

  button.active {
    background: color-mix(in srgb, var(--sm-color-accent) 12%, transparent);
  }

  button.is-relevant {
    border-color: var(--sm-color-success, #18a058);
    background: color-mix(in srgb, var(--sm-color-success, #18a058) 12%, transparent);
    color: var(--sm-color-success, #18a058);
  }

  button.is-irrelevant {
    border-color: var(--sm-color-danger, #d03050);
    background: color-mix(in srgb, var(--sm-color-danger, #d03050) 12%, transparent);
    color: var(--sm-color-danger, #d03050);
  }
}

.ai-result__feedback-state {
  margin: 0;
  color: var(--sm-color-text-muted);
  font-size: 10px;
  line-height: 1.4;
}

.ai-feedback-notice {
  grid-column: 1 / -1;
  padding: 4px 8px;
  border-radius: 4px;
  background: color-mix(in srgb, var(--sm-color-accent) 8%, transparent);
  color: var(--sm-color-text-muted);
  font-size: 11px;
}

.ai-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 220px;
  margin-top: 12px;
  border: 1px dashed var(--sm-color-border);
  border-radius: 10px;
  color: var(--sm-color-text-muted);
  font-size: 12px;
}
</style>
