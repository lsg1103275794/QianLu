<template>
  <div class="analysis-results">
    <!-- 深度分析报告 (如果存在) -->
    <div v-if="analysisReportContent" class="analysis-block deep-analysis-report-block">
      <h3 class="block-title">深度分析报告</h3>
      <div class="chart-card markdown-body" v-html="renderedMarkdown"></div>
    </div>

    <!-- 处理新的content字段 -->
    <div v-if="contentMarkdown" class="analysis-block content-markdown-block">
      <h3 class="block-title">主题与象征分析</h3>
      <div class="chart-card markdown-body" v-html="renderedContentMarkdown"></div>
    </div>

    <!-- 可视化部分 -->
    <div class="visualization-section">
      <!-- 情感分析区块 -->
      <div v-if="result.sentiment" class="analysis-block sentiment-block">
        <h3 class="block-title">情感分析</h3>
        <div class="chart-card">
          <SentimentChart :sentiment="result.sentiment" />
        </div>
      </div>

      <!-- 主观性分析区块 -->
      <div v-if="result.language_features" class="analysis-block language-block">
        <h3 class="block-title">语言特征分析</h3>
        <div class="chart-card">
          <LanguageFeatureCharts :language-features="result.language_features" />
        </div>
      </div>

      <!-- 可读性分析区块 -->
      <div v-if="result.readability" class="analysis-block readability-block">
        <h3 class="block-title">可读性分析</h3>
        <div class="chart-card">
          <ReadabilityChart :readability="result.readability" />
        </div>
      </div>

      <!-- 文本统计区块 -->
      <div v-if="result.text_stats" class="analysis-block text-stats-block">
        <h3 class="block-title">文本统计</h3>
        <div class="chart-card">
          <TextStatsChart :text_stats="result.text_stats" />
        </div>
      </div>

      <!-- 词频分析区块 -->
      <div v-if="result.word_frequency" class="analysis-block word-frequency-block">
        <h3 class="block-title">词频分析</h3>
        <div class="chart-card">
          <WordFrequencyChart :word-frequency="result.word_frequency" />
        </div>
      </div>

      <!-- 句式分析区块 -->
      <div v-if="result.sentence_pattern" class="analysis-block sentence-pattern-block">
        <h3 class="block-title">句式分析</h3>
        <div class="chart-card">
          <SentencePatternChart :sentence-pattern="result.sentence_pattern" />
        </div>
      </div>

      <!-- 关键词提取区块 -->
      <div v-if="result.keyword_extraction" class="analysis-block keyword-extraction-block">
        <h3 class="block-title">关键词提取</h3>
        <div class="chart-card">
          <KeywordExtractionChart :keyword_extraction="result.keyword_extraction" />
        </div>
      </div>
    </div>

    <!-- 原始数据部分 -->
    <div class="raw-data-section">
      <el-collapse v-model="activeCollapse">
        <!-- 语言特征数据 -->
        <el-collapse-item v-if="result.language_features" name="language-features">
          <template #title>
            <div class="collapse-header">
              <span>📊 语言特征数据</span>
            </div>
          </template>
          <div class="raw-data-content">
            <pre>{{ JSON.stringify(result.language_features, null, 2) }}</pre>
          </div>
        </el-collapse-item>

        <!-- 词频分析数据 -->
        <el-collapse-item v-if="result.word_frequency" name="word-frequency">
          <template #title>
            <div class="collapse-header">
              <span>📈 词频分析数据</span>
            </div>
          </template>
          <div class="raw-data-content">
            <pre>{{ JSON.stringify(result.word_frequency, null, 2) }}</pre>
          </div>
        </el-collapse-item>

        <!-- 句式分析数据 -->
        <el-collapse-item v-if="result.sentence_pattern" name="sentence-pattern">
          <template #title>
            <div class="collapse-header">
              <span>🔣 句式分析数据</span>
            </div>
          </template>
          <div class="raw-data-content">
            <pre>{{ JSON.stringify(result.sentence_pattern, null, 2) }}</pre>
          </div>
        </el-collapse-item>

        <!-- 情感分析数据 -->
        <el-collapse-item v-if="result.sentiment" name="sentiment">
          <template #title>
            <div class="collapse-header">
              <span>😊 情感分析数据</span>
            </div>
          </template>
          <div class="raw-data-content">
            <pre>{{ JSON.stringify(result.sentiment, null, 2) }}</pre>
          </div>
        </el-collapse-item>

        <!-- 可读性分析数据 -->
        <el-collapse-item v-if="result.readability" name="readability">
          <template #title>
            <div class="collapse-header">
              <span>📖 可读性分析数据</span>
            </div>
          </template>
          <div class="raw-data-content">
            <pre>{{ JSON.stringify(result.readability, null, 2) }}</pre>
          </div>
        </el-collapse-item>

        <!-- 文本统计数据 -->
        <el-collapse-item v-if="result.text_stats" name="text-stats">
          <template #title>
            <div class="collapse-header">
              <span>📋 文本统计数据</span>
            </div>
          </template>
          <div class="raw-data-content">
            <pre>{{ JSON.stringify(result.text_stats, null, 2) }}</pre>
          </div>
        </el-collapse-item>

        <!-- 关键词提取数据 -->
        <el-collapse-item v-if="result.keyword_extraction" name="keyword-extraction">
          <template #title>
            <div class="collapse-header">
              <span>🔑 关键词提取数据</span>
            </div>
          </template>
          <div class="raw-data-content">
            <pre>{{ JSON.stringify(result.keyword_extraction, null, 2) }}</pre>
          </div>
        </el-collapse-item>
      </el-collapse>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { marked } from 'marked' // 导入 marked 库
import LanguageFeatureCharts from './LanguageFeatureCharts.vue'
import WordFrequencyChart from './WordFrequencyChart.vue'
import SentencePatternChart from './SentencePatternChart.vue'
import SentimentChart from './SentimentChart.vue'
import ReadabilityChart from './ReadabilityChart.vue'
import TextStatsChart from './TextStatsChart.vue'
import KeywordExtractionChart from './KeywordExtractionChart.vue'

/* eslint-disable no-unused-vars */
const props = defineProps({
  result: {
    type: Object,
    required: true,
    default: () => ({})
  },
  activeSections: { // 接收来自父组件的激活部分列表
    type: Array,
    default: () => []
  }
})
/* eslint-enable no-unused-vars */

// 计算属性，获取要显示的分析报告内容
const analysisReportContent = computed(() => {
  return props.result?.analysis_report || props.result?.deep_analysis_report || null;
});

// 计算属性，获取content字段内容
const contentMarkdown = computed(() => {
  return props.result?.content || null;
});

// 计算属性，将 Markdown 渲染为 HTML
const renderedMarkdown = computed(() => {
  if (analysisReportContent.value) {
    try {
      // 注意：直接使用 v-html 有 XSS 风险，确保内容可信！
      // 可以配置 marked 或使用 DOMPurify 进行净化
      return marked.parse(analysisReportContent.value);
    } catch (e) {
      console.error("Markdown rendering error:", e);
      return '<p style="color: red;">Error rendering report.</p>';
    }
  } 
  return '';
});

// 计算属性，将content字段内容作为Markdown渲染为HTML
const renderedContentMarkdown = computed(() => {
  if (contentMarkdown.value) {
    try {
      return marked.parse(contentMarkdown.value);
    } catch (e) {
      console.error("Content markdown rendering error:", e);
      return '<p style="color: red;">Error rendering content.</p>';
    }
  }
  return '';
});

// 默认折叠全部面板
const activeCollapse = ref([])
</script>

<style lang="scss" scoped>
.analysis-results {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.visualization-section {
  display: flex;
  flex-direction: column;
  gap: 30px;
}

.analysis-block {
  width: 100%;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.block-title {
  margin: 0;
  padding: 0 0 10px 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  border-bottom: 2px solid var(--el-border-color-light);
}

.chart-card {
  background: var(--el-bg-color);
  border-radius: 8px;
  padding: 20px;
  box-shadow: var(--el-box-shadow-light);
  overflow: hidden; /* 防止内容溢出 */
}

/* 确保每个分析块内的内容展现一致 */
.sentiment-block .chart-card,
.language-block .chart-card,
.readability-block .chart-card {
  min-height: 350px;
}

.text-stats-block .chart-card {
  min-height: 450px;
}

.word-frequency-block .chart-card,
.sentence-pattern-block .chart-card,
.keyword-extraction-block .chart-card {
  min-height: 400px;
}

.raw-data-section {
  margin-top: 30px;
}

.collapse-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  color: var(--el-text-color-secondary);
  width: 100%;
  justify-content: space-between;
}

.collapse-header::after {
  content: "点击查看详细数据";
  font-size: 12px;
  color: var(--el-color-info);
  opacity: 0.7;
}

.raw-data-content {
  padding: 16px;
  background-color: var(--el-fill-color-light);
  border-radius: 4px;
  overflow-x: auto;
}

.raw-data-content pre {
  margin: 0;
  font-family: monospace;
  font-size: 12px;
  line-height: 1.5;
  color: var(--el-text-color-primary);
}

/* 深色模式适配 */
:deep(.el-collapse-item__header) {
  background-color: var(--el-bg-color);
  border-bottom-color: var(--el-border-color-light);
}

:deep(.el-collapse-item__wrap) {
  background-color: var(--el-bg-color);
  border-bottom-color: var(--el-border-color-light);
}

:deep(.el-collapse-item__content) {
  background-color: var(--el-bg-color);
  color: var(--el-text-color-primary);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .chart-card {
    min-height: auto !important;
    padding: 15px;
  }

  .block-title {
    font-size: 16px;
    padding-bottom: 8px;
  }

  .raw-data-section {
    margin-top: 20px;
  }

  .collapse-header {
    font-size: 13px;
  }

  .raw-data-content {
    padding: 12px;
  }

  .raw-data-content pre {
    font-size: 11px;
  }
}

/* 深度分析报告区块特定样式 */
.deep-analysis-report-block .chart-card {
  min-height: 200px; /* 或根据需要调整 */
  max-height: 600px; /* 添加最大高度和滚动条 */
  overflow-y: auto;
  padding: 20px;
}

/* Markdown 渲染的基本样式 (可以引入 github-markdown-css 或自定义) */
.markdown-body {
  line-height: 1.6;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji";
  color: var(--el-text-color-primary);
}

.markdown-body h1, .markdown-body h2, .markdown-body h3 {
  border-bottom: 1px solid var(--el-border-color-light);
  padding-bottom: 0.3em;
  margin-top: 24px;
  margin-bottom: 16px;
  font-weight: 600;
}

.markdown-body h1 { font-size: 2em; }
.markdown-body h2 { font-size: 1.5em; }
.markdown-body h3 { font-size: 1.25em; }

.markdown-body p {
  margin-bottom: 16px;
}

.markdown-body code {
  padding: .2em .4em;
  margin: 0;
  font-size: 85%;
  background-color: rgba(175, 184, 193, 0.2);
  border-radius: 6px;
}

.markdown-body pre {
  padding: 16px;
  overflow: auto;
  font-size: 85%;
  line-height: 1.45;
  background-color: var(--el-fill-color-lighter);
  border-radius: 6px;
}

.markdown-body pre code {
  padding: 0;
  margin: 0;
  background-color: transparent;
  border-radius: 0;
}

.markdown-body ul, .markdown-body ol {
  padding-left: 2em;
  margin-bottom: 16px;
}

.markdown-body blockquote {
  margin: 0 0 16px 0;
  padding: 0 1em;
  color: var(--el-text-color-secondary);
  border-left: .25em solid var(--el-border-color);
}
</style> 