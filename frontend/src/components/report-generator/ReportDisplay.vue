<template>
  <div v-if="reportContent" class="report-display">
    <h3>{{ addEmoji('研报结果：', 'menu', 'result') }}</h3>
    <!-- Note: Ensure markdown-body class is defined globally or imported -->
    <div class="markdown-body" v-html="renderedReportContent"></div>
  </div>
</template>

<script setup>
import { computed } from 'vue';
import { marked } from 'marked';
import DOMPurify from 'dompurify';
import { addEmoji } from '@/assets/emojiMap';

const props = defineProps({
  reportContent: { type: String, default: '' }
});

const renderedReportContent = computed(() => {
  if (props.reportContent) {
    const rawHtml = marked(props.reportContent);
    // Ensure proper configuration for DOMPurify if needed (e.g., allowing certain tags/attributes)
    return DOMPurify.sanitize(rawHtml);
  }
  return '';
});
</script>

<style scoped>
.report-display {
  margin-top: 20px;
  padding: 15px;
  border-radius: 4px;
}

.report-display h3 {
  margin-bottom: 10px;
}

/* 
  Consider moving markdown-body styles to a global scope 
  (e.g., assets/styles/markdown.scss) if used elsewhere.
  Or scope them here using :deep() if they should only apply within this component.
*/
.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3),
.markdown-body :deep(h4),
.markdown-body :deep(h5),
.markdown-body :deep(h6) {
  margin-top: 1em;
  margin-bottom: 0.5em;
  font-weight: 600;
}
.markdown-body :deep(p) {
  margin-bottom: 0.8em;
  line-height: 1.6;
}
.markdown-body :deep(ul),
.markdown-body :deep(ol) {
  margin-bottom: 0.8em;
  padding-left: 1.5em;
}
.markdown-body :deep(code) {
  background-color: var(--el-fill-color-light); /* Use Element Plus variable */
  padding: 0.2em 0.4em;
  border-radius: 3px;
  font-family: monospace;
  font-size: 0.9em;
}
.markdown-body :deep(pre) {
  background-color: var(--el-fill-color-lighter); /* Use Element Plus variable */
  padding: 1em;
  border-radius: 4px;
  overflow-x: auto;
  margin-bottom: 0.8em;
}
.markdown-body :deep(pre code) {
  padding: 0;
  background-color: transparent;
  font-size: inherit; /* Inherit font size from pre */
}
.markdown-body :deep(blockquote) {
  border-left: 4px solid var(--el-border-color-light); /* Use Element Plus variable */
  padding-left: 1em;
  color: var(--el-text-color-secondary); /* Use Element Plus variable */
  margin-left: 0;
  margin-right: 0;
  margin-bottom: 0.8em;
}
.markdown-body :deep(table) {
  border-collapse: collapse;
  width: 100%;
  margin-bottom: 1em;
}
.markdown-body :deep(th, td) {
  border: 1px solid var(--el-border-color); /* Use Element Plus variable */
  padding: 0.5em;
  text-align: left;
}
.markdown-body :deep(th) {
  background-color: var(--el-fill-color-light); /* Use Element Plus variable */
}

</style> 