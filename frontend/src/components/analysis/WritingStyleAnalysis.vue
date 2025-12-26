image.png<template>
  <div class="writing-style-analysis">
    <el-card 
      class="analysis-card">
      <template #header>
        <div class="gm-card-header">
          <div class="left-section">
            <h2 class="feature-title">{{ addEmoji('文学作品多维分析', 'menu', 'writing-style-analysis') }}</h2>
          </div>
        </div>
      </template>

      <el-form :model="form" label-width="120px">
        <!-- API 提供商和模型选择 -->
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="API 提供商">
              <el-select 
                v-model="form.provider" 
                placeholder="请选择 API 提供商" 
                style="width: 100%;" 
                :disabled="isAnalyzing"
                @change="handleProviderChange" 
              >
                <el-option
                  v-for="provider in providers"
                  :key="provider.name"
                  :label="getProviderWithEmoji(provider)"
                  :value="provider.name"
                />
              </el-select>
              <el-button 
                type="primary" 
                link 
                size="small" 
                @click="reloadModels" 
                class="refresh-btn"
              >
                <el-icon><Refresh /></el-icon>
                刷新
              </el-button>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item :label="$t('analysis.model')" prop="model">
              <el-select
                v-model="form.model"
                :placeholder="$t('common.selectModel')"
                :loading="loadingModels.value"
                :disabled="!form.provider || loadingModels.value"
                @change="saveCurrentUiState"
              >
                <el-option
                  v-for="model in models"
                  :key="model.id"
                  :label="model.name"
                  :value="model.id"
                />
              </el-select>
              <!-- 添加模型加载状态提示 -->
              <div v-if="loadingModels.value" class="loading-models-hint">
                <el-icon class="is-loading"><Loading /></el-icon>
                <span>正在加载模型列表...</span>
              </div>
              <div v-else-if="form.provider && models.length === 0" class="no-models-hint">
                <el-icon><Warning /></el-icon>
                <span>未加载到任何模型，请检查API连接</span>
                <el-button 
                  type="primary" 
                  link 
                  size="small" 
                  @click="reloadModels" 
                  class="refresh-btn"
                >
                  <el-icon><Refresh /></el-icon>
                  刷新
                </el-button>
              </div>
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 文件上传和文本输入 -->
        <el-form-item label="输入文本">
          <!-- File Indicator -->
          <div v-if="loadedFile" class="gm-file-indicator">
            <el-icon><Document /></el-icon>
            <span>已加载文件: {{ loadedFile.name }}</span>
            <el-button 
              type="danger" 
              :icon="Delete" 
              size="small" 
              circle 
              plain 
              @click="clearLoadedFile"
              title="清除文件内容"
              style="margin-left: 10px;"
            />
          </div>

          <!-- Textarea -->
          <el-input
            v-model="form.text"
            type="textarea"
            :rows="10"
            placeholder="在此处粘贴文本，或从下方上传文件"
            :disabled="isAnalyzing"
            class="gm-textarea"
            :class="{'has-content': form.text.trim().length > 0 || loadedFile}" 
          />

          <!-- Upload Component -->
          <div class="gm-upload-container">
            <el-upload
              ref="uploadRef"
              class="gm-text-uploader"
              action="" 
              :auto-upload="false"
              :show-file-list="false"  
              :limit="1"
              :on-change="handleFileChange" 
              :on-exceed="handleFileExceed"
              accept=".txt,.md,.pdf,.docx,.epub,.yaml,.json" 
              :disabled="isAnalyzing"
            >
              <el-button 
                class="upload-button"
                size="default"
              >
                <el-icon><UploadFilled /></el-icon>
                选择文件
              </el-button>
              <template #tip>
                <div class="el-upload__tip">
                  支持 .txt, .md, .pdf, .docx, .epub, .yaml, .json 文件，仅限上传 1 个文件。上传后将覆盖上方文本框内容。
                </div>
              </template>
            </el-upload>
            
            <!-- 显示已选文件 -->
            <div v-if="loadedFile" class="gm-uploaded-file-info">
              <el-tag size="small" type="success">
                <el-icon><Document /></el-icon>
                <span>{{ loadedFile.name }}</span>
              </el-tag>
            </div>
            
            <!-- 上传中的状态 -->
            <div v-if="isUploadingExtracting" class="gm-upload-loading-overlay">
              <div class="gm-upload-loading-content">
                <el-icon class="is-loading"><Loading /></el-icon>
                <span>正在提取文本内容...</span>
              </div>
            </div>
          </div>
        </el-form-item>


        <!-- 分析维度选择 (Tree View) -->
        <el-form-item label="分析维度">
           <div class="gm-template-tree-container">
            <el-tree
              ref="treeRef"
              :data="literatureTemplateTreeData"
              show-checkbox
              node-key="id"
              :props="treeProps"
              @check-change="handleTreeCheckChange"
              :disabled="isAnalyzing"
            >
              <template #default="{ node, data }">
                <span class="custom-tree-node" :title="data.tooltip">
                  <el-icon v-if="!data.isLeaf"><Folder /></el-icon>
                  <el-icon v-else><Document /></el-icon>
                  <span style="margin-left: 4px;">{{ node.label }}</span>
                </span>
              </template>
            </el-tree>
          </div>
        </el-form-item>

        <!-- Add action buttons here -->
        <div class="form-action-buttons">
          <el-button 
            type="primary" 
            @click="startAnalysis" 
            :loading="isAnalyzing" 
            :disabled="!canStartAnalysis || isAnalyzing"
            class="action-button"
          >
            <el-icon class="el-icon--left"><Search /></el-icon>
            {{ isAnalyzing ? '分析中...' : '开始分析' }}
          </el-button>
          <el-button 
            @click="downloadResult" 
            :disabled="!analysisResult" 
            v-if="analysisResult"
            class="action-button"
          >
            <el-icon class="el-icon--left"><Download /></el-icon>
            下载结果
          </el-button>
          <el-button 
            @click="saveAnalysis" 
            :disabled="!analysisResult" 
            v-if="analysisResult"
            class="action-button"
          >
            <el-icon class="el-icon--left"><FolderChecked /></el-icon>
            保存分析
          </el-button>
        </div>
      </el-form>

      <!-- 进度显示区域，替代原来的覆盖层 -->
      <div v-if="isAnalyzing" class="gm-analysis-progress">
        <div class="progress-container">
          <el-progress :percentage="progressPercentage" />
          <div class="progress-text">
            <el-icon class="is-loading"><Loading /></el-icon>
            <span>分析中...结果将显示在下方</span>
          </div>
        </div>
      </div>

      <!-- 分析结果展示 -->
      <div v-if="analysisResult" class="gm-analysis-result">
        <h3 class="block-title">分析结果</h3>
        <div class="chart-card markdown-body" v-html="renderedMarkdown"></div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, onUnmounted, nextTick } from 'vue';
import { ElMessage, ElUpload, ElTree, ElButton, ElIcon, ElLoading } from 'element-plus';
import { Delete, UploadFilled, Loading, Search, Download, Document, FolderChecked, Folder, Warning, Refresh } from '@element-plus/icons-vue';
import { marked } from 'marked';
import api from '../../services/api';
import { addEmoji } from '../../assets/emojiMap';

const form = ref({
  provider: '',
  model: '',
  text: ''
});

const providers = ref([]);
const models = ref([]);
const literatureTemplate = ref(null);
const isAnalyzing = ref(false);
const analysisResult = ref('');
const uploadRef = ref();
const treeRef = ref(); // 用于访问 Tree 组件实例
const loadedFile = ref(null);
const isUploadingExtracting = ref(false);
const selectedTreeNodes = ref([]); // 这个可能不再直接使用，改为通过 treeRef 获取
const loadingModels = ref(false);
const isLoadingProviders = ref(false); // 新增：定义 isLoadingProviders
const progressPercentage = ref(0); // 新增：进度百分比
let progressInterval = null; // 新增：进度条更新间隔

const treeProps = {
  children: 'children',
  label: 'name'
};

const literatureTemplateTreeData = computed(() => {
  if (!literatureTemplate.value || !literatureTemplate.value.categories) {
    return [];
  }

  function transformNode(node, parentId = '') {
      const nodeId = parentId ? `${parentId}.${node.id}` : node.id;
      const tooltipContent = node.instruction || node.description || node.name;
      const treeNode = {
          id: nodeId,
          name: node.name,
          tooltip: tooltipContent,
          raw: node,
          children: [],
          isLeaf: false
      };

      if (node.subcategories && node.subcategories.length > 0) {
          treeNode.children = node.subcategories.map(sub => transformNode(sub, nodeId));
          treeNode.isLeaf = false;
      } else if (node.parameters && node.parameters.length > 0) {
           treeNode.children = node.parameters.map(param => ({
              id: `${nodeId}.${param.id}`,
              name: param.name,
              tooltip: param.instruction || param.description || param.name,
              isLeaf: true,
              raw: param
          }));
          treeNode.isLeaf = false;
      } else {
           treeNode.isLeaf = !!parentId; 
      }

      return treeNode;
  }

  return literatureTemplate.value.categories.map(cat => transformNode(cat));
});

// --- Lifecycle Hooks ---
onMounted(async () => {
  // 添加调试信息
  console.log('文笔分析组件挂载，准备初始化...');
  
  // 清除潜在的缓存
  console.log('清除API缓存...');
  if (window.localStorage) {
    // 清除与模型相关的缓存项
    Object.keys(window.localStorage).forEach(key => {
      if (key.includes('_models_cache') || key.includes('api_cache_') || 
          key.includes('writing_style_models_') || key.includes('_model_list')) {
        window.localStorage.removeItem(key);
        console.log(`已清除缓存项: ${key}`);
      }
    });
  }
  
  // 添加额外的防缓存措施
  if (window.fetch) {
    console.log('注册全局防缓存拦截器');
    const originalFetch = window.fetch;
    window.fetch = function(url, options) {
      if (typeof url === 'string' && (url.includes('/models/') || url.includes('/providers'))) {
        // 添加时间戳到URL
        const separator = url.includes('?') ? '&' : '?';
        url = `${url}${separator}_t=${Date.now()}`;
        console.log('防缓存URL:', url);
        
        // 添加防缓存头
        options = options || {};
        options.headers = options.headers || {};
        options.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate';
        options.headers['Pragma'] = 'no-cache';
        options.headers['Expires'] = '0';
      }
      return originalFetch(url, options);
    };
  }
  
  // 移除旧的 localStorage 加载逻辑
  // loadSettings(); 
  
  isLoadingProviders.value = true; // 使用定义的 isLoadingProviders
  await fetchProviders();
  isLoadingProviders.value = false; // 使用定义的 isLoadingProviders
  
  await fetchLiteratureTemplate();
  
  // 加载保存的 UI 状态
  await loadUiState();

  // 检查并设置所有节点为选中状态（如果需要默认全选）
  // ensureAllNodesChecked(); 
});

onUnmounted(() => {
  // 页面离开时保存当前状态
  // saveCurrentUiState();
});

// --- API Fetching Functions ---
const fetchProviders = async () => {
  try {
    const response = await api.getProviders();
    providers.value = response.data || [];
    let providerToSet = null;
    
    // Determine the provider to set initially
    if (form.value.provider && providers.value.some(p => p.name === form.value.provider)) {
        providerToSet = form.value.provider;
    } else if (providers.value.length > 0) {
      // Default to the first provider if initialProvider is invalid or not provided
      providerToSet = providers.value[0].name;
      console.log(`Initial provider '${form.value.provider}' not valid or not found, defaulting to '${providerToSet}'`);
    } else {
      console.warn("No providers available.")
    }
    
    // Set the provider value. The watcher will handle fetching models.
    if (providerToSet && providerToSet !== form.value.provider) {
        console.log(`[fetchProviders] Setting initial provider to: ${providerToSet}`);
        form.value.provider = providerToSet; 
    } else if (providerToSet && providerToSet === form.value.provider) {
        // If provider is already set correctly, ensure models are fetched if list is empty
        // This case might happen if localStorage matches the default provider
        if (models.value.length === 0) {
             console.log(`[fetchProviders] Provider '${providerToSet}' already set, models empty. Triggering fetchModels.`);
             await fetchModels(providerToSet); // Manually trigger fetch if needed
        }
    } else if (!providerToSet) {
       // Handle case where no providers are available
       form.value.provider = '';
       form.value.model = '';
       models.value = [];
    }

  } catch (error) {
    ElMessage.error('获取 API 提供商列表失败');
    console.error(error);
    form.value.provider = '';
    models.value = [];
    form.value.model = '';
  }
};

const fetchLiteratureTemplate = async () => {
  try {
    console.log("Fetching detailed literature template structure (V2)...");
    const response = await api.getDetailedLiteratureTemplateStructure();
    if (response.data) {
      literatureTemplate.value = response.data;
      console.log("Successfully loaded detailed literature template structure (V2):", literatureTemplate.value);
    } else {
       throw new Error('API did not return data for the V2 template structure.');
    }
  } catch (error) {
    console.error('加载详细文学分析模板结构 (V2) 失败:', error);
    let errorMsg = '加载详细文学分析模板结构失败。请确保后端服务正常且模板文件存在。';
    if (error.response && error.response.status === 404) {
       errorMsg = `加载模板失败: 后端未找到 V2 模板结构接口或模板文件。`;
    } else if (error.message) {
       errorMsg += ` 原因: ${error.message}`;
    }
    ElMessage.error(errorMsg);
    literatureTemplate.value = null;
  }
};

// --- Event Handlers ---
const handleTreeCheckChange = () => {
  if (treeRef.value) {
      selectedTreeNodes.value = treeRef.value.getCheckedKeys(true);
  }
  // Remove call to non-existent function
  // saveCurrentUiState();
};

// 新增：Provider 变更处理器
const handleProviderChange = async (newProvider) => {
    console.log(`Provider changed to: ${newProvider}`);
    form.value.model = ''; // Clear model when provider changes
    models.value = []; // Clear model list immediately
    
    // 强制刷新模型列表，避免缓存问题
    if (newProvider) {
        console.log(`切换到新的模型供应商，强制刷新模型列表：${newProvider}`);
        loadingModels.value = true;
        
        // 添加小延迟确保UI更新
        setTimeout(() => {
            fetchModels(newProvider);
        }, 100);
    } else {
        console.log("Provider为空，不加载模型");
    }
    
    // Fetch models 之后再保存状态，确保 model 列表已更新，但此时 model 尚未选择
    saveCurrentUiState(); 
};

// --- File Handling ---
const handleFileChange = (uploadFile, uploadFiles) => {
  // ElUpload's change hook provides UploadFile object directly
  // Check if uploadFile exists and has a raw property (which is the File object)
  const file = uploadFile?.raw; 
  
  if (file instanceof File) {
    loadedFile.value = file; // Store the actual File object
    form.value.text = ''; 
    console.log("Selected file:", file.name);
    // No need to manually set input value here, ElUpload handles it

    // Trigger extraction immediately after selection
    // Note: This changes behavior slightly, extraction starts on select, not button click
    // If you want to keep the button click, remove the call below
    uploadSelectedFile(); 

  } else if (!uploadFile && uploadFiles.length === 0) {
    // This handles the case where the file is removed via ElUpload's UI
    loadedFile.value = null;
    form.value.text = ''; 
    console.log("File removed.");
  } else {
    // Log unexpected cases
    console.warn("handleFileChange called with unexpected arguments:", uploadFile, uploadFiles);
    loadedFile.value = null;
  }
  saveCurrentUiState(); // Save settings after file change
};

const uploadSelectedFile = async () => {
  if (!loadedFile.value) {
    ElMessage.warning('请先选择一个文件');
    return;
  }

  isUploadingExtracting.value = true;
  const formData = new FormData();
  formData.append('file', loadedFile.value);

  try {
    const response = await api.uploadAndExtractText(formData);
    if (response?.data?.extracted_text) {
      form.value.text = response.data.extracted_text;
      ElMessage.success('文件内容提取成功！');
    } else {
      throw new Error(response?.data?.error || '文件内容提取失败');
    }
  } catch (error) {
    ElMessage.error(`文件处理失败: ${error.message || '未知错误'}`);
    console.error("文件上传或提取失败:", error);
    form.value.text = '';
  } finally {
    isUploadingExtracting.value = false;
  }
};

const handleFileExceed = (files) => {
  uploadRef.value?.clearFiles();
  const file = files[0];
  handleFileChange({ raw: file, name: file.name }); 
  ElMessage.warning('只能上传一个文件，已替换为新文件');
};

// --- Analysis Logic ---
const canStartAnalysis = computed(() => {
  return form.value.text.trim() !== '' &&
         form.value.provider !== '' &&
         form.value.model !== '' &&
         selectedTreeNodes.value.length > 0 &&
         !isAnalyzing.value &&
         !isUploadingExtracting.value;
});

// 新增：启动进度条模拟
const startProgressSimulation = () => {
  // 重置进度
  progressPercentage.value = 0;
  
  // 清除可能存在的旧计时器
  if (progressInterval) {
    clearInterval(progressInterval);
  }
  
  // 创建新的进度模拟计时器
  progressInterval = setInterval(() => {
    // 进度增长逻辑：开始快，接近90%后变慢
    if (progressPercentage.value < 30) {
      progressPercentage.value += 5;
    } else if (progressPercentage.value < 60) {
      progressPercentage.value += 3;
    } else if (progressPercentage.value < 85) {
      progressPercentage.value += 1;
    } else if (progressPercentage.value < 90) {
      progressPercentage.value += 0.5;
    }
    
    // 确保不超过95%
    if (progressPercentage.value >= 95) {
      progressPercentage.value = 95;
      clearInterval(progressInterval);
    }
  }, 300);
};

// 新增：结束进度条模拟
const stopProgressSimulation = () => {
  if (progressInterval) {
    clearInterval(progressInterval);
    progressInterval = null;
  }
  progressPercentage.value = 100;
};

// 新增：处理<think>标签内容的函数
const removeThinkContent = (text) => {
  if (!text) return '';
  
  // 过滤<think>标签内容
  let result = text;
  const thinkRegex = /<think>([\s\S]*?)<\/think>/g;
  result = result.replace(thinkRegex, '');
  
  // 移除可能残留的单个标签
  result = result.replace(/<\/?think>/g, '');
  
  return result.trim();
};

const startAnalysis = async () => {
  if (!canStartAnalysis.value) return;

  isAnalyzing.value = true;
  analysisResult.value = '';
  startProgressSimulation(); // 启动进度条模拟

  try {
    const selectedDimensions = treeRef.value ? treeRef.value.getCheckedKeys(true) : selectedTreeNodes.value;
    
    if (selectedDimensions.length === 0) {
        ElMessage.warning('请至少选择一个分析维度');
        isAnalyzing.value = false;
        stopProgressSimulation(); // 停止进度条模拟
        return;
    }

    const payload = {
      text: form.value.text,
      provider: form.value.provider,
      model: form.value.model,
      selected_dimensions: selectedDimensions
    };
    
    console.log("Submitting analysis request:", payload);
    const response = await api.analyzeLiterature(payload);
    let result = response.data.result || '分析完成，但未返回有效结果。';
    
    // 清理<think>标签内容
    result = removeThinkContent(result);
    
    // 检查是否是JSON格式，如果是，解析它并获取content字段
    try {
      const jsonResult = JSON.parse(result);
      if (jsonResult && jsonResult.content) {
        result = jsonResult.content;
      }
    } catch (e) {
      // 不是JSON格式，使用原始结果
    }
    
    analysisResult.value = result;
    ElMessage.success('分析完成！');
    
  } catch (error) {
    ElMessage.error(`分析失败: ${error.response?.data?.detail || error.message || '未知错误'}`);
    console.error("分析请求失败:", error);
    analysisResult.value = `分析失败：${error.response?.data?.detail || error.message}`;
  } finally {
    stopProgressSimulation(); // 完成时进度条到100%
    isAnalyzing.value = false;
  }
};

// --- Result Handling ---
const downloadResult = () => {
  if (!analysisResult.value) return;
  const blob = new Blob([analysisResult.value], { type: 'text/plain;charset=utf-8' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = `writing_style_analysis_result_${Date.now()}.txt`;
  link.click();
  URL.revokeObjectURL(link.href);
};

const saveAnalysis = async () => {
  if (!analysisResult.value) {
    ElMessage.warning('没有可保存的分析结果');
    return;
  }
  const loadingInstance = ElLoading.service({ text: '正在保存结果...' });
  try {
    const payload = {
      text_summary: (form.value.text || '').substring(0, 150) + (form.value.text.length > 150 ? '...' : ''),
      result: analysisResult.value,
      provider: form.value.provider,
      model: form.value.model,
      timestamp: new Date().toISOString(),
      analysis_type: 'literature_v2',
      original_text: form.value.text,
      selected_dimensions: treeRef.value ? treeRef.value.getCheckedKeys(true) : selectedTreeNodes.value
    };
    const response = await api.saveLiteratureAnalysisResult(payload);
    ElMessage.success(response.data?.message || '写作风格分析结果已保存');
  } catch (error) {
    console.error('保存写作风格分析结果失败:', error);
    ElMessage.error(`保存失败: ${error.response?.data?.detail || error.message || '请检查后端服务。'}`);
  } finally {
    loadingInstance.close();
  }
};

const getProviderWithEmoji = (provider) => {
  const emojis = {
    'ollama_local': '🦙',
    'google_gemini': '🌌',
    'openai': '💡',
    'zhipu_ai': '🧠',
    'deepseek_ai': '🔍',
    'volc_engine': '🌋',
    'silicon_flow': '🔄'
  };
  
  const emoji = emojis[provider.name] || '🤖';
  return `${emoji} ${provider.display_name || provider.name}`;
};

const clearLoadedFile = () => {
    form.value.text = '';
    loadedFile.value = null;
    uploadRef.value?.clearFiles(); 
};

// Modify fetchModels to handle restoration
const fetchModels = async (providerName) => {
  console.log(`[fetchModels] 尝试获取 ${providerName} 的模型列表`);
  
  if (!providerName) {
    console.warn('无效的provider名称');
    models.value = [];
    form.value.model = '';
    return; 
  }
  
  loadingModels.value = true;
  models.value = []; // Clear previous models
  form.value.model = ''; // 清空当前选中的模型，避免错误选择

  console.log(`[fetchModels] 正在获取 ${providerName} 的模型列表...`);
  
  try {
    // 直接在URL中添加时间戳
    const response = await api.getModels(`${providerName}?_t=${Date.now()}`);
    console.log(`[fetchModels] 获取模型响应:`, response);
    
    let modelList = [];
    
    if (response?.data) {
      console.log(`[fetchModels] 成功获取 ${providerName} 的模型响应:`, response.data);
      
      // 处理不同格式的响应
      if (Array.isArray(response.data)) {
        modelList = response.data;
        console.log(`[fetchModels] 响应为数组格式，包含 ${modelList.length} 个模型`);
      } else if (response.data.models && Array.isArray(response.data.models)) {
        modelList = response.data.models;
        console.log(`[fetchModels] 响应包含嵌套models数组，包含 ${modelList.length} 个模型`);
      } else {
        console.warn(`[fetchModels] 响应格式不符合预期:`, response.data);
        modelList = [];
      }
      
      // 处理并标准化模型数据
      models.value = modelList.map(model => {
        if (typeof model === 'string') {
          return { id: model, name: model };
        } else if (model && typeof model === 'object') {
          return { 
            id: model.id || model.model || model.name || String(model),
            name: model.name || model.id || model.model || String(model)
          };
        } else {
          console.warn('[fetchModels] 无法处理的模型格式:', model);
          return null;
        }
      }).filter(model => model !== null);
      
      console.log(`[fetchModels] 处理后得到 ${models.value.length} 个有效模型:`, models.value);
      
      // 如果有保存的模型选择，尝试恢复
      setTimeout(() => {
        if (models.value.length > 0) {
          // 默认选择第一个模型
          form.value.model = models.value[0].id;
          console.log(`[fetchModels] 默认选择第一个模型: ${form.value.model}`);
        }
      }, 200);
    } else {
      console.warn(`[fetchModels] 获取 ${providerName} 的模型列表失败: 响应无数据`);
      models.value = [];
    }
  } catch (error) {
    console.error(`[fetchModels] 获取 ${providerName} 模型列表出错:`, error);
    ElMessage.error(`无法加载 ${providerName} 的模型列表: ${error.message || '未知错误'}`);
    models.value = [];
  } finally {
    loadingModels.value = false;
  }
};

// --- UI State Persistence ---
const UI_STATE_KEY = 'writing-style-analysis';

const saveCurrentUiState = async () => {
  try {
    const state = {
      provider: form.value.provider,
      model: form.value.model,
      selectedDimensions: selectedTreeNodes.value,
      text: form.value.text ? form.value.text.substring(0, 100) : '', // 仅保存部分文本内容作为标识
    };
    
    await api.saveUiState(UI_STATE_KEY, state);
    console.log('WritingStyleAnalysis UI state saved');
  } catch (error) {
    console.error('Failed to save UI state:', error);
    // 静默失败，不影响用户体验
  }
};

const loadUiState = async () => {
  try {
    const response = await api.getUiState(UI_STATE_KEY);
    if (response?.data) {
      const state = response.data;
      console.log('Loaded UI state:', state);
      
      // 应用保存的状态
      if (state.provider) form.value.provider = state.provider;
      if (state.model) form.value.model = state.model;
      if (state.selectedDimensions?.length > 0) {
        selectedTreeNodes.value = state.selectedDimensions;
        // 加载后需要更新树组件选中状态
        nextTick(() => {
          if (treeRef.value) {
            treeRef.value.setCheckedKeys(selectedTreeNodes.value);
          }
        });
      }
    }
  } catch (error) {
    console.error('Failed to load UI state:', error);
    // 静默失败，使用默认设置
  }
};

const reloadModels = async () => {
  ElMessage.info('正在强制刷新模型列表...');
  loadingModels.value = true;
  models.value = [];
  
  // 清除浏览器缓存
  if (window.caches) {
    try {
      const cacheKeys = await window.caches.keys();
      await Promise.all(
        cacheKeys.map(key => window.caches.delete(key))
      );
      console.log('已清理浏览器Cache API缓存');
    } catch (e) {
      console.error('清理Cache API失败:', e);
    }
  }
  
  // 强制请求新数据
  try {
    if (form.value.provider) {
      await fetchModels(form.value.provider);
      
      if (models.value.length > 0) {
        ElMessage.success(`成功加载 ${models.value.length} 个模型`);
      } else {
        ElMessage.warning('未找到模型，请检查API连接和提供商设置');
      }
    } else {
      await fetchProviders();
      if (form.value.provider) {
        await fetchModels(form.value.provider);
      } else {
        ElMessage.error('未找到有效的API提供商');
      }
    }
  } catch (error) {
    console.error('刷新模型列表失败:', error);
    ElMessage.error(`刷新模型列表失败: ${error.message || '未知错误'}`);
  } finally {
    loadingModels.value = false;
  }
};

// 添加计算属性，将分析结果作为Markdown渲染
const renderedMarkdown = computed(() => {
  if (analysisResult.value) {
    try {
      // 先清理<think>标签内容
      const cleanedResult = removeThinkContent(analysisResult.value);
      return marked.parse(cleanedResult);
    } catch (e) {
      console.error("Markdown渲染错误:", e);
      return '<p style="color: red;">无法渲染结果。</p>';
    }
  }
  return '';
});

// 清理未使用的计时器
onUnmounted(() => {
  if (progressInterval) {
    clearInterval(progressInterval);
  }
});
</script>

<style lang="scss" scoped>
.writing-style-analysis {
  margin: 0 auto;
  padding: 20px;
}

.analysis-card {
  margin-bottom: 20px;
}

.el-form-item {
  margin-bottom: 22px;
}

.el-form-item:has(.gm-template-tree-container) {
  margin-top: 30px;
}

/* 带有文件时的文本框样式 */
.textarea-with-file {
  border-color: var(--el-color-success);
  box-shadow: 0 0 0 1px var(--el-color-success-light-5);
}

/* 文件操作区域样式 */
.gm-uploaded-file-info {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 10px;
}

/* 上传状态样式增强 */
.gm-uploading-status {
  margin-top: 12px;
  border-radius: 4px;
}

/* 上传按钮容器布局 */
.gm-upload-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* 加载状态容器 */
.gm-loading-container {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: rgba(255, 255, 255, 0.8);
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  z-index: 1000;
  backdrop-filter: blur(5px);
  
  .is-loading {
    font-size: 40px;
    color: var(--el-color-primary);
    animation: spin 1.5s linear infinite;
    margin-bottom: 16px;
  }
  
  span {
    font-size: 16px;
    font-weight: 500;
    color: var(--el-text-color-primary);
  }
}

@keyframes spin {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

/* 分析结果容器样式优化 */
.gm-analysis-result {
  margin-top: 24px;
  padding: 16px;
  border-radius: 8px;
  background-color: var(--el-bg-color);
  border: 1px solid var(--el-border-color-light);
  transition: all 0.3s ease;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
  
  .block-title {
    margin: 0;
    padding: 0 0 10px 0;
    font-size: 18px;
    font-weight: 600;
    color: var(--el-text-color-primary);
    border-bottom: 2px solid var(--el-border-color-light);
    margin-bottom: 16px;
  }
}

/* 文件标签样式统一 */
.gm-file-indicator {
  display: flex;
  align-items: center;
  margin-bottom: 10px;
  padding: 8px 12px;
  background-color: rgba(240, 249, 235, 0.8);
  border-radius: 4px;
  border: 1px solid #e1f3d8;
  
  .el-icon {
    margin-right: 8px;
    color: #67c23a;
  }
  
  span {
    color: #67c23a;
    font-size: 14px;
  }
}

/* 深色模式适配 */
:deep(.dark) {
  .analysis-card {
    background-color: var(--el-bg-color);
    border-color: var(--el-border-color-darker);
  }

  .gm-analysis-result {
    background-color: var(--el-bg-color-overlay);
    border-color: var(--el-border-color-darker);
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.2);
    
    .block-title {
      color: var(--el-text-color-primary);
    }
  }
  
  .gm-file-indicator {
    background-color: rgba(15, 35, 15, 0.6);
    border-color: #2b3e26;
    
    span {
      color: #85ce61;
    }
  }

  .gm-loading-container {
    background-color: rgba(0, 0, 0, 0.7);
    backdrop-filter: blur(5px);
  }
}

/* 按钮容器样式 */
.form-action-buttons {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
  gap: 10px;
}

/* 文本框样式 */
.gm-textarea {
  width: 100%;
}

/* 为树节点添加一些样式 */
.gm-template-tree-container {
  width: 100%;
  max-height: 400px;
  overflow-y: auto;
  border: 1px solid var(--el-border-color-light);
  border-radius: 4px;
  padding: 10px;
}

.custom-tree-node {
  display: flex;
  align-items: center;
  font-size: 14px;
}

/* 添加模型加载状态提示 */
.loading-models-hint {
  margin-top: 12px;
  border-radius: 4px;
  padding: 8px 12px;
  background-color: rgba(240, 249, 235, 0.8);
  border: 1px solid #e1f3d8;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;

  .el-icon {
    margin-right: 8px;
    color: #67c23a;
  }

  span {
    color: #67c23a;
    font-size: 14px;
  }
}

/* 添加未加载到模型时的提示 */
.no-models-hint {
  margin-top: 12px;
  border-radius: 4px;
  padding: 8px 12px;
  background-color: rgba(240, 249, 235, 0.8);
  border: 1px solid #e1f3d8;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;

  .el-icon {
    margin-right: 8px;
    color: #67c23a;
  }

  span {
    color: #67c23a;
    font-size: 14px;
  }

  .refresh-btn {
    padding: 0;
    margin: 0;
    background: none;
    border: none;
    color: #67c23a;
    font: inherit;
    cursor: pointer;
    outline: inherit;
  }
}

/* 添加新的加载状态样式 */
.gm-upload-loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(255, 255, 255, 0.8);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
}

.gm-upload-loading-content {
  background-color: var(--el-fill-color-light);
  padding: 15px 20px;
  border-radius: 4px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  display: flex;
  align-items: center;
  
  .el-icon {
    margin-right: 8px;
    color: var(--el-color-primary);
    font-size: 18px;
  }
}

/* 添加Markdown样式 */
.markdown-body {
  line-height: 1.6;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif, "Apple Color Emoji", "Segoe UI Emoji";
  color: var(--el-text-color-primary);
  padding: 10px;
  max-height: 600px;
  overflow-y: auto;
}

.markdown-body h1, .markdown-body h2, .markdown-body h3, .markdown-body h4 {
  border-bottom: 1px solid var(--el-border-color-light);
  padding-bottom: 0.3em;
  margin-top: 24px;
  margin-bottom: 16px;
  font-weight: 600;
}

.markdown-body h1 { font-size: 2em; }
.markdown-body h2 { font-size: 1.5em; }
.markdown-body h3 { font-size: 1.25em; }
.markdown-body h4 { font-size: 1.1em; }

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

/* 移除原来的覆盖层样式 */
.gm-analysis-loading-overlay {
  display: none; /* 隐藏原来的全屏覆盖 */
}

/* 新增进度条区域样式 */
.gm-analysis-progress {
  margin: 20px 0;
  padding: 15px;
  border-radius: 8px;
  background-color: rgba(0, 0, 0, 0.03);
  border: 1px solid var(--el-border-color-light);
}

.progress-container {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.progress-text {
  display: flex;
  align-items: center;
  color: var(--el-color-primary);
  font-size: 14px;
  
  .el-icon {
    margin-right: 8px;
  }
}

/* 深色模式适配 */
:deep(.dark) {
  .gm-analysis-progress {
    background-color: rgba(255, 255, 255, 0.05);
    border-color: var(--el-border-color-darker);
  }
  
  .progress-text {
    color: var(--el-color-primary-light-3);
  }
}
</style> 