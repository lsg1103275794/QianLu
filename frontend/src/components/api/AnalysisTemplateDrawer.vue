<template>
  <el-drawer
    :model-value="props.visible"
    title="选择分析模板"
    direction="rtl"
    size="70%" 
    @close="handleClose"
    :destroy-on-close="true"
  >
    <div class="template-drawer-content">
      <!-- Left Side: Template List -->
      <div class="template-list-container">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索模板名称或描述..."
          clearable
          prefix-icon="Search"
          style="margin-bottom: 15px;"
        />
        <el-scrollbar class="template-list-scrollbar">
          <el-radio-group v-model="selectedTemplate" v-loading="loading" class="template-radio-group">
            <div v-if="filteredTemplates.length === 0 && !loading" class="empty-state">
              <el-empty description="未找到匹配的模板" :image-size="80" />
            </div>
            <el-radio 
              v-for="template in filteredTemplates" 
              :key="template.id" 
              :label="template.id"
              border
              class="template-radio-item"
              @mouseover="loadTemplatePreview(template.id)" 
            >
              <div class="template-info">
                <strong class="template-name">{{ template.name }}</strong>
                <p class="template-description">{{ template.description }}</p>
              </div>
            </el-radio>
          </el-radio-group>
        </el-scrollbar>
      </div>

      <!-- Right Side: Preview Area -->
      <div class="template-preview-container">
        <h4 class="preview-title">模板内容预览 (Markdown)</h4>
        <el-scrollbar class="preview-scrollbar">
           <div class="markdown-preview" v-html="renderedPreview"></div>
        </el-scrollbar>
      </div>
    </div>

    <template #footer>
      <div style="flex: auto">
        <el-button @click="handleClose">取消</el-button>
        <el-button type="primary" @click="handleSelect">确定</el-button>
      </div>
    </template>
  </el-drawer>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue';
import { ElMessage } from 'element-plus';
// @ts-ignore - Still ignore JS module if needed, or remove if not using TS
import api from '@/services/api'; // Import API service
import { marked } from 'marked'; // Import marked
import DOMPurify from 'dompurify'; // Import DOMPurify

// Props and Emits
const props = defineProps({
  visible: Boolean,
  currentTemplateId: String
});
const emit = defineEmits(['close', 'select']);

// State
const templates = ref([]); // Removed <TemplateInfo[]>
const loading = ref(false);
const selectedTemplate = ref(props.currentTemplateId);
const hoveredTemplateId = ref(null); // Removed <string | null>
const previewContent = ref(null); // Removed <string | null>
const loadingPreview = ref(false);
const searchKeyword = ref('');

// Computed property for filtered templates
const filteredTemplates = computed(() => {
  if (!searchKeyword.value) {
    return templates.value;
  }
  const keyword = searchKeyword.value.toLowerCase();
  // Assuming template items have name and description
  return templates.value.filter(t => 
    t.name?.toLowerCase().includes(keyword) || // Added optional chaining just in case
    (t.description && t.description.toLowerCase().includes(keyword))
  );
});

// Fetch templates when the drawer becomes visible
watch(() => props.visible, (newVal) => {
  if (newVal && templates.value.length === 0) {
    fetchTemplates();
  }
  // Reset selection and preview when drawer closes
  if (!newVal) {
      selectedTemplate.value = props.currentTemplateId;
      hoveredTemplateId.value = null;
      previewContent.value = null;
      loadingPreview.value = false;
  }
});

// Function to fetch templates
const fetchTemplates = async () => {
  loading.value = true;
  try {
    const response = await api.getTemplates();
    templates.value = response.data || [];
  } catch (error) {
    console.error("Failed to fetch templates:", error);
    ElMessage.error('加载模板列表失败');
    templates.value = []; // Ensure it's an empty array on error
  } finally {
    loading.value = false;
  }
};

// Function to load preview on hover
const loadTemplatePreview = async (templateId) => { // Removed : string type hint
  if (!templateId || hoveredTemplateId.value === templateId) return; // Avoid redundant loads
  
  hoveredTemplateId.value = templateId;
  loadingPreview.value = true;
  previewContent.value = null; // Clear previous preview
  
  try {
    const response = await api.getTemplateDetails(templateId);
    const templateData = response.data;
    
    // Try finding the prompt content under common keys
    let foundContent = null;
    if (templateData) {
        if (typeof templateData.prompt === 'string') {
            foundContent = templateData.prompt;
        } else if (typeof templateData.full_prompt_template === 'string') {
             foundContent = templateData.full_prompt_template;
        } else if (typeof templateData.prompt_template === 'string') {
             foundContent = templateData.prompt_template;
        } else if (typeof templateData.instructions === 'string') { // Fallback to instructions if others not found
            foundContent = templateData.instructions;
        } else if (typeof templateData.instruction === 'string') { // Fallback for analysis.yaml structure
            foundContent = templateData.instruction;
        }
        // Add more fallbacks if needed based on template structures
    }

    if (foundContent !== null) {
      previewContent.value = foundContent;
    } else {
      console.warn("Template data received, but no suitable content field found:", templateData);
      previewContent.value = '未在此模板数据中找到可预览的内容字段。';
    }
  } catch (error) {
    console.error(`Failed to fetch template details for ${templateId}:`, error);
    // Provide more specific error if possible
    const errorMsg = error.response?.data?.detail || error.message || '未知错误';
    previewContent.value = `加载预览失败: ${errorMsg}`;
  } finally {
    loadingPreview.value = false;
  }
};

// Computed property for rendered Markdown preview
const renderedPreview = computed(() => {
  if (loadingPreview.value) {
    return '<div style="display: flex; align-items: center; justify-content: center; height: 100%; color: #909399;"><el-icon class="is-loading" style="margin-right: 5px;"><Loading /></el-icon>加载中...</div>';
  }
  if (!previewContent.value || typeof previewContent.value !== 'string') {
    return '<p style="color: #909399; text-align: center; padding-top: 20px;">将鼠标悬停在左侧模板上以查看预览</p>';
  }
  try {
    // Removed 'as string' cast
    const dirty = marked.parse(previewContent.value);
    const clean = DOMPurify.sanitize(dirty);
    return clean;
  } catch (e) {
    console.error("Markdown parsing error:", e);
    return '<p style="color: red;">渲染预览时出错。</p>';
  }
});

// Function to handle selection
const handleSelect = () => {
  if (selectedTemplate.value) {
    emit('select', selectedTemplate.value);
  } else {
    ElMessage.warning('请选择一个模板');
  }
};

// Function to close the drawer
const handleClose = () => {
  emit('close');
};

// Initial fetch if drawer is already visible on mount (rare case)
onMounted(() => {
  if (props.visible && templates.value.length === 0) {
    fetchTemplates();
  }
});
</script>

<style scoped>
.template-drawer-content {
  display: flex;
  height: calc(100% - 60px); /* Adjust based on actual footer height if different */
  padding: 0;
  margin: 0; /* Remove default padding/margin if any */
}

.template-list-container {
  width: 40%;
  border-right: 1px solid var(--el-border-color-light);
  padding: 15px;
  display: flex;
  flex-direction: column;
  overflow: hidden; /* Prevent double scrollbars */
}

.template-preview-container {
  width: 60%;
  padding: 15px;
  display: flex;
  flex-direction: column;
  overflow: hidden; /* Prevent double scrollbars */
}

.template-list-scrollbar {
  flex-grow: 1;
  height: 100%; /* Ensure scrollbar takes available height */
}

.preview-scrollbar {
   flex-grow: 1;
   height: 100%;
   border: 1px solid var(--el-border-color-lighter);
   border-radius: 4px;
}

.template-radio-group {
  display: flex;
  flex-direction: column;
  width: 100%;
}

.template-radio-item {
  width: 100%;
  margin-bottom: 10px;
  height: auto; /* Allow height to adjust */
  padding: 10px 15px;
  display: flex; /* Use flex for alignment */
  align-items: center; /* Vertically center radio and content */
  margin-right: 0 !important; /* Override default margin */
}

/* Adjust radio button position if needed */
.template-radio-item :deep(.el-radio__input) {
  margin-top: 0; /* Reset potential top margin */
}

.template-info {
  margin-left: 10px; /* Space between radio and text */
  flex-grow: 1; /* Allow info to take remaining space */
}

.template-name {
  display: block;
  font-size: 1.1em;
  margin-bottom: 4px;
  color: var(--el-text-color-primary);
}

.template-description {
  font-size: 0.9em;
  color: var(--el-text-color-secondary);
  line-height: 1.4;
  margin: 0;
}

.preview-title {
  margin-top: 0;
  margin-bottom: 10px;
  color: var(--el-text-color-regular);
  font-weight: 600;
}

.markdown-preview {
  padding: 15px;
  font-size: 14px;
  line-height: 1.6;
  min-height: 100px; /* Ensure it has some height */
}

/* Basic Markdown styling for preview (can reuse styles from TextAnalysis.vue) */
.markdown-preview :deep(h1), .markdown-preview :deep(h2), .markdown-preview :deep(h3) { margin-top: 1em; margin-bottom: 0.5em; font-weight: 600; }
.markdown-preview :deep(h1) { font-size: 1.6em; }
.markdown-preview :deep(h2) { font-size: 1.4em; }
.markdown-preview :deep(h3) { font-size: 1.2em; }
.markdown-preview :deep(p) { margin-bottom: 1em; }
.markdown-preview :deep(ul), .markdown-preview :deep(ol) { margin-left: 20px; margin-bottom: 1em; }
.markdown-preview :deep(li) { margin-bottom: 0.4em; }
.markdown-preview :deep(code) { background-color: var(--el-color-info-light-9); padding: 0.2em 0.4em; border-radius: 3px; font-size: 90%; }
.markdown-preview :deep(pre) { background-color: var(--el-color-info-light-9); padding: 10px; border-radius: 4px; overflow-x: auto; margin-bottom: 1em; }
.markdown-preview :deep(pre code) { background-color: transparent; padding: 0; font-size: inherit; }
.markdown-preview :deep(blockquote) { border-left: 4px solid var(--el-border-color); padding-left: 10px; margin-left: 0; margin-bottom: 1em; color: var(--el-text-color-secondary); }
.markdown-preview :deep(table) { border-collapse: collapse; margin-bottom: 1em; width: auto; }
.markdown-preview :deep(th), .markdown-preview :deep(td) { border: 1px solid var(--el-border-color); padding: 6px 13px; }
.markdown-preview :deep(hr) { border: 0; height: 1px; background-color: var(--el-border-color); margin: 1.5em 0; }

.empty-state {
    display: flex;
    justify-content: center;
    align-items: center;
    height: 200px; /* Adjust as needed */
    color: var(--el-text-color-secondary);
}
</style> 