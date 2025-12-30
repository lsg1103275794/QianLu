<template>
  <div class="text-analysis">
    <el-card class="analysis-card">
      <template #header>
        <div class="gm-card-header">
          <div class="left-section">
            <h2 class="feature-title">{{ addEmoji('文本分析', 'menu', 'text-analysis') }}</h2>
            <el-switch
              v-model="isDarkMode"
              @change="toggleDarkMode"
              inline-prompt
              :active-icon="Moon"
              :inactive-icon="Sunny"
              class="theme-switch"
            />
          </div>
        </div>
      </template>
      
      <el-form :model="form" label-width="100px" ref="analysisFormRef" :rules="formRules">
        <el-form-item label="输入文本" prop="text">
          <!-- 文本输入区 -->
          <el-input
            v-model="form.text"
            type="textarea"
            :rows="10"
            placeholder="在此输入或粘贴要分析的文本内容，或使用下方的按钮上传文件..."
            clearable
            class="gm-textarea"
            :class="{'has-content': form.text.trim().length > 0}"
            :disabled="analyzing" 
          />
          
          <!-- 文件上传区 -->
          <div class="gm-upload-container">
            <el-upload
              ref="uploadRef"
              class="gm-text-uploader"
              action="#"
              :auto-upload="true"
              :http-request="handleFileUpload"
              :before-upload="beforeUpload"
              :on-remove="handleFileRemove"
              :on-error="handleUploadError"
              :show-file-list="false"
              :limit="1"
            >
              <el-button 
                class="upload-button"
                size="default"
                :loading="loadingFileContent"
              >
                <el-icon><Upload /></el-icon>
                上传文本文件
              </el-button>
              <template #tip>
                <div class="el-upload__tip">
                  支持 TXT、PDF、DOCX、EPUB、MD 格式，最大 50MB
                </div>
              </template>
            </el-upload>
            
            <!-- 已上传文件信息展示 -->
            <div v-if="fileList.length > 0" class="gm-uploaded-file-info">
              <el-tag size="small" type="success">
                <el-icon><Document /></el-icon>
                <span>已提取: {{ fileList[0].name }}</span>
              </el-tag>
              <el-button 
                type="danger" 
                size="small" 
                circle
                @click="removeFile"
                title="移除文件"
              >
                <el-icon><Delete /></el-icon>
              </el-button>
            </div>
          </div>
          
          <!-- 加载状态覆盖层，绝对定位 -->
          <div v-if="loadingFileContent" class="gm-upload-loading-overlay">
            <div class="gm-upload-loading-content">
              <el-icon class="is-loading"><Loading /></el-icon>
              <span>正在提取文本内容...</span>
            </div>
          </div>
        </el-form-item>
        
        <el-form-item label="分析类型">
          <el-radio-group v-model="analysisType" @change="handleAnalysisTypeChange">
            <el-radio :value="'basic'">{{ addEmoji('基础分析', 'feature', 'readability') }} (本地计算)</el-radio>
            <el-radio :value="'deep'">{{ addEmoji('深度文学分析', 'feature', 'style') }} (AI大模型)</el-radio>
          </el-radio-group>
          
          <!-- Display selected template info -->
          <el-tag 
            v-if="form.template && analysisType === 'deep'" 
            type="info" 
            size="small" 
            style="margin-left: 10px; cursor: pointer;"
            @click="openTemplateDrawer" 
            title="点击更换模板">
            当前模板: {{ form.template }}
          </el-tag>
          <el-tooltip 
            v-if="!form.template && analysisType === 'deep'" 
            content="为深度分析选择一个预设的分析框架和提示词模板" 
            placement="top">
             <el-button 
               link 
               type="primary" 
               @click="openTemplateDrawer" 
               style="margin-left: 10px;" 
               :icon="QuestionFilled">
               选择分析模板
             </el-button>
          </el-tooltip>
        </el-form-item>
        
        <!-- 分析维度 -->
        <el-form-item 
          label="分析维度" 
          prop="options" 
          v-if="analysisType === 'basic'" > <!-- Only show for basic analysis -->
           <div class="gm-options-container">
              <el-checkbox-group v-model="form.options">
                <!-- Only show basic options here -->
                <el-checkbox value="sentiment">情感分析</el-checkbox>
                <el-checkbox value="readability">可读性</el-checkbox>
                <el-checkbox value="text_stats">文本统计</el-checkbox>
                <el-checkbox value="word_frequency">词频统计</el-checkbox>
                <el-checkbox value="sentence_pattern">句式分析</el-checkbox>
                <el-checkbox value="keyword_extraction">关键词提取</el-checkbox>
                <el-checkbox value="language_features">语言特征</el-checkbox>
              </el-checkbox-group>
            </div>
        </el-form-item>

        <el-form-item 
          label="分析模型" 
          required 
          v-if="analysisType === 'deep'"> <!-- Only show for deep analysis -->
          <el-row :gutter="20">
            <el-col :span="8">
              <el-form-item :label="$t('analysis.provider')" prop="provider" style="width: 100%; margin-bottom: 15px;">
                <el-select 
                  v-model="form.provider" 
                  :placeholder="$t('analysis.selectProvider')" 
                  :disabled="analyzing"
                  @change="handleProviderChange"
                  filterable
                  style="width: 100%;"
                  clearable
                >
                  <el-option
                    v-for="provider in availableProviders"
                    :key="provider.name"
                    :label="getProviderWithEmoji(provider)"
                    :value="provider.name"
                  />
                </el-select>
                <el-button 
                  type="primary" 
                  size="small" 
                  @click="refreshProvider"
                  :loading="refreshingProvider"
                  style="margin-left: 10px;"
                >
                  <el-icon><Refresh /></el-icon>
                  刷新
                </el-button>
              </el-form-item>
            </el-col>
            
            <el-col :span="11">
              <el-form-item prop="model" style="width: 100%; margin-bottom: 0;">
                <el-select 
                  v-model="form.model" 
                  :placeholder="modelSelectPlaceholder" 
                  :disabled="!form.provider || loadingModels" 
                  :loading="loadingModels"
                  filterable 
                  clearable
                  allow-create 
                  default-first-option
                  style="width: 100%;"
                >
                  <el-option
                    v-for="model in availableModels"
                    :key="model.id"
                    :label="model.name"
                    :value="model.id"
                  />
                  <template #empty>
                    <div style="padding: 10px; text-align: center; color: #999;">
                      {{ emptyModelText }}
                    </div>
                  </template>
                </el-select>
                <div v-if="showDefaultModelHint" class="el-form-item__tip" style="font-size: 12px; margin-top: 4px;">
                  {{ $t('analysis.defaultModelHint') }}
                </div>
                <el-button 
                  type="primary" 
                  size="small" 
                  @click="refreshModel"
                  :loading="refreshingModel"
                  style="margin-left: 10px;"
                >
                  <el-icon><Refresh /></el-icon>
                  刷新
                </el-button>
              </el-form-item>
            </el-col>
          </el-row>
          
          <div class="section-actions" style="margin-top: 10px">
            <el-button 
              type="info" 
              plain 
              size="small" 
              @click="testDirectAPICall" 
              :loading="testingApi"
              v-if="showTestApiButton"
            >
               <el-icon class="el-icon--left"><Connection /></el-icon>测试API连接
            </el-button>
            <div :class="[
              'api-test-status',
              apiTestStatus.type ? `api-test-status--${apiTestStatus.type}` : ''
            ]" v-if="apiTestStatus.message">
              <el-icon v-if="apiTestStatus.type === 'success'"><CircleCheck /></el-icon>
              <el-icon v-else-if="apiTestStatus.type === 'error'"><CircleClose /></el-icon>
              <el-icon v-else-if="apiTestStatus.type === 'warning'"><Warning /></el-icon>
              <el-icon v-else-if="apiTestStatus.type === 'pending'" class="is-loading"><Loading /></el-icon>
              <el-icon v-else><InfoFilled /></el-icon>
              <span>{{ apiTestStatus.message }}</span>
            </div>
          </div>
          
          <div v-if="analysisType === 'deep'" style="margin-top: 10px">
            <el-checkbox v-model="form.forceAsync">
              处理大型文本/数据集 (强制使用异步处理，结果会发送到AI Chat对话中)
            </el-checkbox>
          </div>
        </el-form-item>

        <!-- Move the action button here -->
        <div class="form-action-buttons">
          <el-button 
            type="primary" 
            @click="submitAnalysis"
            :loading="analyzing"
            :disabled="!canStartAnalysis"
            class="action-button"
          >
            <el-icon class="el-icon--left"><CaretRight /></el-icon>
            开始分析
          </el-button>
        </div>
      </el-form>
      
      <!-- 分析中状态显示 -->
      <div v-if="analyzing" class="gm-loading-container">
        <el-icon class="is-loading"><Loading /></el-icon>
        <span>{{ analyzingMessage }}</span>
      </div>
      
      <!-- 分析结果展示 -->
      <div v-if="result && Object.keys(result).length > 0" class="analysis-results-container">
        <analysis-results 
          :result="result" 
          :active-sections="activeResultSections"
        />
        <!-- Add Save Button Here -->
        <div class="form-action-buttons" style="margin-top: 20px;">
           <el-button
              @click="saveAnalysis"
              :disabled="!result"
              type="success"
              plain
            >
              <el-icon class="el-icon--left"><FolderChecked /></el-icon>
              保存分析结果
            </el-button>
        </div>
      </div>
      
      <!-- 错误展示 -->
      <el-alert
        v-if="analysisError"
        type="error"
        :title="analysisError"
        :closable="false"
        show-icon
      />
    </el-card>
    
    <!-- 分析模板抽屉 -->
    <AnalysisTemplateDrawer
      :visible="templateDrawerVisible"
      :current-template-id="form.template"
      @close="handleTemplateDrawerClose"
      @select="handleTemplateSelect"
    />
  </div>
</template>

<script setup>
import AnalysisResults from './AnalysisResults.vue'
import { ref, reactive, computed, onMounted, watch, onUnmounted, nextTick } from 'vue'
import { ElMessage, ElLoading } from 'element-plus'
import { Document, Upload, Moon, Sunny, QuestionFilled, Loading, CircleCheck, CircleClose, Warning, Connection, Delete, InfoFilled, CaretRight, FolderChecked, Refresh } from '@element-plus/icons-vue'
import api from '../../services/api'
import axios from 'axios'
import { addEmoji } from '../../assets/emojiMap.js'
import { useDark } from '@vueuse/core'
import AnalysisTemplateDrawer from '../api/AnalysisTemplateDrawer.vue'

// Refs
const analysisFormRef = ref();
const uploadRef = ref(null);

// Reactive state
const form = reactive({
  text: '',
  uploadedFilePath: '',
  options: ['writing_style', 'structure', 'tone', 'lexical'], // Default options
  provider: null,
  model: null,
  template: null, // For deep analysis templates
  forceAsync: true, // Default to async for large tasks
  _trigger: 0 // 添加一个触发器属性，用于强制重新计算
});
const fileList = ref([]);
const analyzing = ref(false);
const result = ref(null);
const analysisError = ref(null); // Initialize analysisError
const activeResultSections = ref([]);
const availableProviders = ref([]);
const availableModels = ref([]);
const loadingModels = ref(false);
const loadingFileContent = ref(false); // Add state for loading file content
const templateDrawerVisible = ref(false);
const analysisType = ref('deep'); 
const editableReportContent = ref('');

// --- Dark mode state and logic ---
const isDarkMode = useDark(); // Use VueUse for dark mode

const toggleDarkMode = () => {
  // Update local state
  const newDarkMode = isDarkMode.value;
  
  // Save preference to localStorage
  localStorage.setItem('darkMode', newDarkMode);
  
  // Apply to document
  if (newDarkMode) {
    document.documentElement.classList.add('dark');
    document.body.setAttribute('data-theme', 'dark');
  } else {
    document.documentElement.classList.remove('dark');
    document.body.setAttribute('data-theme', 'light');
  }
};

// Watch for changes in the result and update the editable content
watch(result, (newResult) => {
  if (newResult && newResult.deep_analysis_report) {
    // 处理深度分析报告，可能是对象、JSON字符串或其他格式
    let reportContent = newResult.deep_analysis_report;
    
    // 检查报告内容的类型
    if (typeof reportContent === 'object') {
      // 如果是对象（包括对象里有content字段的情况）
      if (reportContent.content) {
        // 优先使用content字段的内容
        editableReportContent.value = reportContent.content;
      } else if (reportContent.raw_text) {
        // 或者raw_text字段
        editableReportContent.value = reportContent.raw_text;
      } else {
        // 否则格式化整个对象
        editableReportContent.value = JSON.stringify(reportContent, null, 2);
      }
      console.log("成功处理深度分析报告对象");
    } else if (typeof reportContent === 'string') {
      // 如果是字符串，尝试解析JSON
      try {
        if (reportContent.startsWith('{') || reportContent.startsWith('[')) {
          // 解析JSON字符串
          const parsedReport = JSON.parse(reportContent);
          // 格式化为易读的文本
          editableReportContent.value = JSON.stringify(parsedReport, null, 2);
        } else {
          // 如果不是JSON字符串，直接使用
          editableReportContent.value = reportContent;
        }
      } catch (error) {
        console.error("解析深度分析报告失败:", error);
        // 解析失败时直接使用原始内容
        editableReportContent.value = reportContent;
      }
    } else {
      // 其他类型，转为字符串
      editableReportContent.value = String(reportContent);
    }
  } else {
    editableReportContent.value = ''; // Clear if no report
  }
}, { deep: true }); // Use deep watch if result structure might change internally

// --- Computed properties for validation rules ---
const formRules = computed(() => ({
  text: [
    // Required only if file is not uploaded
    { validator: validateTextOrFile, trigger: 'blur' }
  ],
  // Provider is required ONLY if deep analysis is selected
  provider: [
    { required: analysisType.value === 'deep', message: '进行深度分析需要选择 AI 服务商', trigger: 'change' }
  ],
  // Model is optional even for deep analysis (backend uses default)
  // options validation remains the same
  options: [
      { type: 'array', required: true, message: '请至少选择一个分析维度', trigger: 'change' }
  ]
}));

// --- Add computed properties for model select placeholder and empty text ---
const modelSelectPlaceholder = computed(() => {
  if (loadingModels.value) {
    return '正在加载模型...';
  }
  if (!form.provider) {
    return '请先选择服务商';
  }
   // 如果有可用模型，或允许手动输入，则显示标准提示
  // if (availableModels.value.length > 0) { 
    return '选择模型 (留空则使用默认)';
  // }
  // return '无可用模型 (可尝试默认)'; // 如果列表为空
});

const emptyModelText = computed(() => {
  if (loadingModels.value) {
    return '加载中...';
  }
   if (!form.provider) {
     return '请先选择服务商';
   }
  // if (availableModels.value.length === 0) { // Redundant check with #empty template
    return '无可用模型列表 (可手动输入或使用默认)';
  // }
  // return '没有匹配的模型'; // Default filterable empty text
});

// 控制提示显示的计算属性
const showDefaultModelHint = computed(() => {
  return form.provider && !loadingModels.value; // && availableModels.value.length === 0; // 无论列表是否为空都显示提示
});
// ---------------------------------------------------------------------

// Custom validator for text/file input
const validateTextOrFile = (rule, value, callback) => {
  if (!form.text.trim() && !form.uploadedFilePath) {
    callback(new Error('请输入文本或上传文件'));
  } else {
    callback();
  }
};

// --- API Fetching ---
const fetchProviders = async () => {
  try {
    const response = await api.getProviders();
    console.log("原始API提供商数据:", response);
    
    // 处理axios响应格式
    const data = response.data || response;
    
    // 正确处理复杂对象结构
    if (Array.isArray(data)) {
      availableProviders.value = data;
      console.log("成功获取API提供商列表:", availableProviders.value);
    } else {
      console.error("获取API提供商返回了意外的数据结构:", data);
      availableProviders.value = [];
      ElMessage.warning('API提供商数据格式异常');
    }
  } catch (error) {
    console.error("获取可用服务商失败:", error);
    ElMessage.error('无法加载服务商列表');
    availableProviders.value = [];
  }
};

const fetchModels = async (providerName) => {
  console.log(`获取提供商 ${providerName} 的模型列表`);
  form.model = ''; // 清空之前选择的模型
  availableModels.value = [];
  
  if (!providerName) {
    console.warn('无效的提供商名称');
    loadingModels.value = false;
    return;
  }
  
  try {
    loadingModels.value = true;
    
    // 添加请求日志
    console.log(`开始请求 ${providerName} 的模型列表...`);
    const response = await api.getModels(providerName);
    console.log(`成功获取 ${providerName} 的模型列表响应:`, response);
    
    let modelList = [];
    const responseData = response.data;
    
    // 检查是否有嵌套的models数组
    if (responseData && responseData.models && Array.isArray(responseData.models)) {
      console.log("发现嵌套的models数组:", responseData.models.length);
      modelList = responseData.models;
    } 
    // 处理直接返回数组的情况
    else if (Array.isArray(responseData)) {
      console.log("响应直接返回模型数组:", responseData.length);
      modelList = responseData;
    }
    // 处理空响应
    else {
      console.warn(`获取 ${providerName} 的模型列表返回了非预期的格式:`, responseData);
      modelList = [];
    }
    
    console.log(`为 ${providerName} 处理模型列表，数量: ${modelList.length}`);
    
    // 转换模型格式
    availableModels.value = modelList.map(model => {
      // 处理不同格式的模型对象
      if (typeof model === 'string') {
        return { id: model, name: model };
      } else if (model && model.id) {
        return { id: model.id, name: model.name || model.id };
      } else if (model && model.model) {
        return { id: model.model, name: model.name || model.model };
      } else {
        console.warn('无法识别的模型格式:', model);
        return null;
      }
    }).filter(model => model !== null); // 过滤掉无效模型
    
    console.log(`最终加载了 ${availableModels.value.length} 个有效模型`);
    
    // 如果之前有选择过模型，尝试恢复选择
    const previousModel = localStorage.getItem(`${providerName}_last_model`);
    if (previousModel && availableModels.value.some(m => m.id === previousModel)) {
      form.model = previousModel;
      console.log(`恢复之前选择的模型: ${previousModel}`);
    }
  } catch (error) {
    console.error(`获取模型列表失败: ${error.message || error}`, error);
    ElMessage.error(`无法加载 ${providerName} 的模型列表: ${error.message || '未知错误'}`);
    availableModels.value = [];
  } finally {
    loadingModels.value = false;
  }
};

// 获取分析模板列表
// const fetchTemplates = async () => { ... };

// --- Event Handlers ---
const handleProviderChange = (providerName) => {
  // 清除之前的模型选择和缓存
  form.model = '';
  availableModels.value = [];
  
  // 强制刷新模型列表，避免缓存问题
  if (providerName) {
    console.log("切换到新的模型供应商，强制刷新模型列表：", providerName);
    loadingModels.value = true;
    setTimeout(() => {
      fetchModels(providerName);
    }, 100);
  }
};

// 处理分析类型变化
const handleAnalysisTypeChange = (type) => {
  console.log('[handleAnalysisTypeChange]', type);
  analysisType.value = type;
  
  // 重置选项和结果
  form.options = ['writing_style', 'structure', 'tone', 'lexical'];
  form.provider = null;
  form.model = null;
  result.value = null;
  analysisError.value = null;
  
  // 根据分析类型设置默认选项
  if (type === 'basic') {
    form.options = ['sentiment', 'readability', 'text_stats', 'word_frequency', 'sentence_pattern', 'keyword_extraction', 'language_features'];
  }
  
  // 触发状态更新
  updateFormState();
};

// 打开模板选择抽屉
const openTemplateDrawer = () => {
  templateDrawerVisible.value = true;
  // No longer need to fetch templates here
  // if (availableTemplates.value.length === 0) {
  //   fetchTemplates();
  // }
};

// 处理模板选择完成
const handleTemplateSelect = (template) => {
  console.log('[handleTemplateSelect]', template);
  // 设置选定的模板和预填数据
  form.template = template;
  form.options = template.options || ['writing_style', 'structure', 'tone', 'lexical'];
  form.provider = template.provider || null;
  form.model = template.model || null;
  
  // 强制更新表单状态
  updateFormState();
  
  // 关闭抽屉
  templateDrawerVisible.value = false;
};

// 处理模板抽屉关闭
const handleTemplateDrawerClose = () => {
  templateDrawerVisible.value = false;
};

// 添加异步分析相关状态
const analyzingMessage = ref('正在提交分析请求，请稍候...');
const pollingInterval = ref(null);

// 清除轮询
const clearPolling = () => {
  if (pollingInterval.value) {
    clearInterval(pollingInterval.value);
    pollingInterval.value = null;
  }
};

// Ollama错误处理相关

// --- Add state for API test status ---
const apiTestStatus = ref({ message: '', type: 'info' }); // { message: string, type: 'info'|'success'|'error'|'warning'|'pending' }
const testingApi = ref(false); // Button loading state

// 添加直接测试API调用的函数
const testDirectAPICall = async () => {
  testingApi.value = true; // 控制按钮 loading 状态
  apiTestStatus.value = { message: '正在测试连接...', type: 'pending' }; // 显示"正在测试"
  try {
    // --- 获取 provider 和 model ---
    // 如果 provider 为空，可能需要提示用户选择或使用默认
    const testProvider = form.provider;
    if (!testProvider) {
      apiTestStatus.value = { message: '请先选择一个服务商', type: 'warning' };
      testingApi.value = false;
      return;
    }
    // 如果 model 为空，后端测试接口会使用该 provider 的默认模型
    const testModel = form.model || null;

    console.log(`尝试直接调用API: provider=${testProvider}, model=${testModel || '默认'}`);

    // --- 调用 API ---
    const response = await api.testModelConnection({
      provider: testProvider,
      model: testModel, // 发送 null 如果未选择，让后端决定默认值
      prompt: "Hi, please reply with just one word 'OK' to confirm you received this.", // 更简洁的英文 prompt
      stream: false // 明确指定非流式
    });

    console.log("API测试响应 data:", response.data);

    // --- 处理响应 (Updated Logic) ---
    if (response.data) {
      // 检查新的 status 字段
      if (response.data.status === 'success') {
         apiTestStatus.value = {
            message: response.data.message || '连接成功，但未收到具体消息', // 显示后端返回的成功消息
            type: 'success'
         };
      } else if (response.data.status === 'error') {
         // 后端明确返回了错误状态
         apiTestStatus.value = {
            message: `测试失败: ${response.data.message || '未知模型或API错误'}`,
            type: 'error'
         };
      } else if (response.data.error) {
         // 兼容旧的错误格式
         apiTestStatus.value = { message: `测试失败: ${response.data.error}`, type: 'error' };
      } else {
         // 其他未知或非预期格式
         // 尝试将响应数据转换为字符串显示，帮助调试
         const responseString = typeof response.data === 'string' ? response.data : JSON.stringify(response.data);
         apiTestStatus.value = {
            message: `连接成功，但响应内容非预期 (${responseString.substring(0, 50)}...)`, 
            type: 'warning'
         };
      }
    } else {
       apiTestStatus.value = { message: '测试失败: 后端返回无效响应', type: 'error' };
    }
  } catch (error) {
    // --- 处理请求错误 ---
    console.error("API测试出错:", error);
    const errorMsg = error.response?.data?.error ||
                     error.response?.data?.detail ||
                     error.message ||
                     '未知网络或服务器错误';
    apiTestStatus.value = { message: `测试失败: ${errorMsg}`, type: 'error' };
  } finally {
    testingApi.value = false; // 结束按钮 loading 状态
  }
};

// 在表单下方添加测试按钮的逻辑
// 使用计算属性控制显示测试按钮
const showTestApiButton = computed(() => {
  return form.provider && analysisType.value === 'deep';
});

// --- File Upload Handlers (similar to StyleTransfer) ---
const handleFileUpload = async (options) => {
  const { file, onSuccess, onError, onProgress } = options;
  
  // 如果没有选择文件，直接返回
  if (!file) {
    ElMessage.warning('请先选择一个文件');
    return;
  }

  // 清除状态和设置加载
  loadingFileContent.value = true;
  form.uploadedFilePath = '';
  
  try {
    const formData = new FormData();
    formData.append('file', file.raw || file);
    
    // 使用带进度回调的API调用
    const response = await api.uploadAndExtractText(formData, progressEvent => {
      if (progressEvent.total) {
        const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
        console.log(`Upload progress: ${percentCompleted}%`);
        onProgress({ percent: percentCompleted });
      }
    });
    
    // 处理响应
    if (response?.data?.extracted_text) {
      // 直接将提取的文本填充到文本框中
      form.text = response.data.extracted_text;
      form.uploadedFilePath = response.data.file_path || '';
      fileList.value = [{ 
        name: file.name || response.data.original_filename || 'uploaded-file',
        status: 'success' 
      }];
      
      // 检查提取的文本是否太短或为空
      const textContent = form.text.trim();
      if (!textContent) {
        ElMessage.warning('文件已上传，但未能提取到文本内容，可能是不支持的格式或空文件');
      } else if (textContent.length < 50) {
        ElMessage.warning('文件已上传，但提取的文本内容很少，可能提取不完整');
      } else {
        ElMessage.success('文件内容提取成功！文本已加载到编辑框');
      }
      
      onSuccess(response.data);
      
      // 确保文本框获得焦点，以便用户可以立即编辑
      nextTick(() => {
        const textArea = document.querySelector('.gm-input-container textarea');
        if (textArea) {
          textArea.focus();
        }
      });
    } else {
      const errorMsg = response?.data?.error || '文件内容提取失败';
      throw new Error(errorMsg);
    }
  } catch (error) {
    console.error("文件处理失败:", error);
    ElMessage.error(`文件处理失败: ${error.message || '未知错误'}`);
    fileList.value = [];
    form.uploadedFilePath = '';
    if (onError) onError(error);
  } finally {
    loadingFileContent.value = false;
  }
};

const handleFileRemove = () => {
  form.uploadedFilePath = null;
  form.text = ''; 
  analysisFormRef.value?.validateField('text'); 
};

const handleUploadError = () => {
   ElMessage.error('文件上传过程中发生错误');
   form.uploadedFilePath = null;
   if (uploadRef.value) uploadRef.value.clearFiles();
};

const beforeUpload = (rawFile) => {
  const supportedTypes = ['.txt', '.pdf', '.docx', '.epub', '.md'];
  const fileExtension = rawFile.name.substring(rawFile.name.lastIndexOf('.')).toLowerCase();
  if (!supportedTypes.includes(fileExtension)) {
    ElMessage.error('不支持的文件格式!');
    return false;
  }
  const maxSize = 50 * 1024 * 1024;
  if (rawFile.size > maxSize) {
    ElMessage.error('文件大小不能超过 50MB!');
    return false;
  }
   // Clear text input if a file is selected for upload
   form.text = ''; 
   analysisFormRef.value?.clearValidate('text');
  return true;
};

// --- Result Handling ---
// const copySection = (key) => { ... };

// --- Lifecycle Hooks ---
onMounted(() => {
  console.log('文本分析组件已挂载');
  
  // 清除潜在的请求缓存
  console.log('清除API缓存...');
  if (window.localStorage) {
    // 清除与模型相关的缓存项
    Object.keys(window.localStorage).forEach(key => {
      if (key.includes('_models_cache') || key.includes('api_cache_')) {
        window.localStorage.removeItem(key);
        console.log(`已清除缓存项: ${key}`);
      }
    });
  }
  
  loadSettings(); // Load settings when component mounts
  fetchProviders();
  // fetchTemplates(); // Removed call to undefined function
  
  // Apply dark mode setting on mount
  toggleDarkMode();
});

onUnmounted(() => {
  // Remove leftover ECharts disposal logic
  clearPolling(); 
});

// Watchers to disable opposite input method
watch(() => form.text, () => {
  // 当文本输入框内容变化时，如果有文件上传记录但文本内容变更，则更新状态
  if (form.text && form.uploadedFilePath) {
    // 用户编辑了上传后的文本，我们保留文件信息，但标记内容已修改
    const existingFile = fileList.value[0];
    if (existingFile && existingFile.status === 'success') {
      fileList.value = [{ 
        ...existingFile, 
        name: existingFile.name + ' (已编辑)' 
      }];
    }
  }
});

// Watch for changes in provider and model to clear API test status
watch([() => form.provider, () => form.model], () => {
  apiTestStatus.value = { message: '', type: 'info' }; // Clear status on provider/model change
});

// Method to clear the uploaded file state
const clearUploadedFile = () => {
  console.log("[clearUploadedFile] Start");
  try {
    console.log("[clearUploadedFile] Setting form.uploadedFilePath to null");
    form.uploadedFilePath = null;
    
    console.log("[clearUploadedFile] Setting fileList.value to []");
    fileList.value = [];
    
    console.log("[clearUploadedFile] Checking uploadRef.value");
    if (uploadRef.value) {
      console.log("[clearUploadedFile] Calling uploadRef.value.clearFiles()");
      try {
          uploadRef.value.clearFiles(); 
          console.log("[clearUploadedFile] uploadRef.value.clearFiles() succeeded");
      } catch (e) {
          console.error("[clearUploadedFile] Error calling uploadRef.value.clearFiles():", e);
      }
    } else {
        console.warn("[clearUploadedFile] uploadRef not available.");
    }
    
    console.log("[clearUploadedFile] Setting form.text to ''");
    form.text = '';
    
    console.log("[clearUploadedFile] Finished successfully (validation skipped).");
    
  } catch (error) {
      console.error("[clearUploadedFile] Unexpected error during execution:", error);
      ElMessage.error('清除文件时发生错误，请查看控制台。'); 
  }
};

// 删除已上传的文件
const removeFile = () => {
  clearUploadedFile();
  ElMessage.info('已清除文件');
};

// 检查是否可以开始分析
const canStartAnalysis = computed(() => {
  // 基础检查：确保有文本内容或上传了文件
  const hasContent = form.text.trim().length > 0 || form.uploadedFilePath;
  
  // 确保选择了分析选项
  const hasOptions = form.options && form.options.length > 0;
  
  // 强制更新检查 - 这行代码不影响逻辑，但确保计算属性会重新计算
  const _ = form._trigger;
  
  // 将检查结果输出到控制台，方便调试
  console.log('[canStartAnalysis]', {
    analysisType: analysisType.value,
    hasContent,
    hasOptions,
    provider: form.provider,
    analyzing: analyzing.value,
    trigger: _
  });
  
  // 深度分析需要额外检查服务商选择
  if (analysisType.value === 'deep') {
    return hasContent && hasOptions && !!form.provider && !analyzing.value;
  }
  
  // 基础分析只需检查内容和选项
  return hasContent && hasOptions && !analyzing.value;
});

// 强制更新表单状态的辅助函数
const updateFormState = () => {
  form._trigger = Date.now();
  nextTick(() => {
    console.log('[updateFormState] 已强制更新，按钮状态:', canStartAnalysis.value);
  });
};

// 提交分析请求
const submitAnalysis = async () => {
  console.log('[submitAnalysis] 开始提交，按钮状态:', !analyzing.value, '可用状态:', canStartAnalysis.value);
  console.log('[submitAnalysis] 表单数据:', {
    text: form.text ? `${form.text.substring(0, 50)}...` : null,
    hasUploadedFile: !!form.uploadedFilePath,
    options: form.options,
    provider: form.provider,
    model: form.model,
    template: form.template,
    analysisType: analysisType.value
  });
  
  // 表单验证
  try {
    await analysisFormRef.value.validate();
    console.log('[submitAnalysis] 表单验证通过');
  } catch (error) {
    console.error('[submitAnalysis] 表单验证失败', error);
    
    // 显示更详细的验证错误信息
    if (error.fields) {
      for (const field in error.fields) {
        ElMessage.error(`验证失败: ${field} - ${error.fields[field][0].message}`);
      }
    }
    return;
  }
  
  if (!form.text.trim() && !form.uploadedFilePath) {
    ElMessage.warning('请输入文本或上传文件进行分析');
    return;
  }

  // 附加检查：确保分析类型、选项和提供商都有效
  if (analysisType.value === 'deep' && !form.provider) {
    ElMessage.error('进行深度分析需要选择AI服务商');
    return;
  }
  
  if (!form.options || form.options.length === 0) {
    ElMessage.error('请至少选择一个分析维度');
    return;
  }

  // 重置结果状态
  analyzing.value = true;
  result.value = null;
  analysisError.value = null;
  
  try {
    console.log('开始分析文本，类型:', analysisType.value);
    
    // 获取文本内容
    const textContent = form.text.trim();
    
    // 根据分析类型分别处理
    if (analysisType.value === 'basic') {
      // 本地基础分析
      analyzingMessage.value = '正在进行基础文本分析...';
      
      // 导入textAnalysisService中的本地分析函数
      const { performLocalAnalysis } = await import('../../services/textAnalysisService.js');
      
      // 执行本地分析
      const localResult = performLocalAnalysis(textContent, form.options);
      
      console.log('本地分析结果:', localResult);
      // 更新结果状态
      result.value = localResult;
      activeResultSections.value = form.options;
      
      // 完成分析，重置状态
      analyzing.value = false;
      ElMessage.success('本地分析完成！');
      
    } else if (analysisType.value === 'deep') {
      // 深度文学分析 (需要API)
      analyzingMessage.value = '正在提交深度文本分析请求...';
      
      // --- Add detailed logging for input values ---
      console.log('[submitAnalysis Deep] Raw form.text:', form.text);
      console.log('[submitAnalysis Deep] form.uploadedFilePath:', form.uploadedFilePath);
      const textContent = form.text.trim();
      console.log('[submitAnalysis Deep] Trimmed textContent for analysisData:', textContent);
      // --- End of detailed logging ---

      // 准备分析请求参数
      const analysisData = {
        text: textContent,
        options: form.options,
        api_provider: form.provider,
        model: form.model || undefined,
        template: form.template || undefined,
        force_async: form.forceAsync,
        analysis_type: analysisType.value
      };
      
      // 添加文件路径（如果上传了文件）
      if (form.uploadedFilePath) {
        analysisData.file_path = form.uploadedFilePath;
        analysisData.text = ""; // <--- 确保当有文件路径时，文本内容为空，让后端优先处理文件
      }
      
      console.log('提交深度分析请求:', analysisData);
      
      // 根据是否强制异步，选择不同的API调用方式
      if (form.forceAsync) {
        // 异步处理大文本
        const asyncResponse = await api.analyzeTextAsync(analysisData);
        console.log('异步分析任务已提交:', asyncResponse);
        
        // 处理不同格式的响应
        let taskId = null;
        if (asyncResponse.data) {
          // 1. 标准格式: { task_id: "xxx" }
          if (asyncResponse.data.task_id) {
            taskId = asyncResponse.data.task_id;
          } 
          // 2. 备用格式: { id: "xxx" }
          else if (asyncResponse.data.id) {
            taskId = asyncResponse.data.id;
          }
          // 3. 备用格式: { task: { id: "xxx" } }
          else if (asyncResponse.data.task && asyncResponse.data.task.id) {
            taskId = asyncResponse.data.task.id;
          }
        }
        
        if (taskId) {
          console.log('获得异步任务ID:', taskId);
          console.log('完整响应数据:', JSON.stringify(asyncResponse.data, null, 2));
          
          // 保存API可能返回的自定义任务状态查询端点
          let taskEndpoint = null;
          if (asyncResponse.data.task_endpoint) {
            taskEndpoint = asyncResponse.data.task_endpoint;
            console.log('API返回的任务查询端点:', taskEndpoint);
          } else if (asyncResponse.data.status_url) {
            taskEndpoint = asyncResponse.data.status_url;
            console.log('API返回的状态URL:', taskEndpoint);
          }
          
          // 确认任务已提交
          ElMessage.success({
            message: '长文本分析请求已提交，任务ID: ' + taskId.substring(0, 8) + '...',
            duration: 5000
          });
          
          // 尝试立即获取一次任务状态（这有助于检测端点是否正确）
          try {
            const initialStatus = await api.getTaskStatus(taskId);
            console.log('初始任务状态:', initialStatus.data);
            // 显示任务初始状态的消息
            if (initialStatus.data && initialStatus.data.status) {
              ElMessage.info(`任务初始状态: ${initialStatus.data.status}`);
            }
          } catch (statusError) {
            console.warn('无法获取初始任务状态，可能需要等待任务处理:', statusError.message);
          }
          
          // 轮询检查任务状态
          clearPolling(); // 清除之前的轮询
          analyzingMessage.value = '分析中...结果将发送到AI Chat中';
          
          // 添加失败计数器
          let failureCount = 0;
          const MAX_FAILURES = 5; // 增加到5次允许更多的尝试
          
          pollingInterval.value = setInterval(async () => {
            try {
              // 如果API返回了自定义端点，尝试直接使用自定义请求
              let statusResponse;
              if (taskEndpoint) {
                try {
                  console.log(`使用自定义端点查询任务状态: ${taskEndpoint}`);
                  // 直接使用axios发送请求到自定义端点
                  statusResponse = await axios.get(taskEndpoint);
                } catch (endpointError) {
                  console.error(`自定义端点请求失败: ${endpointError.message}, 回退到默认API`);
                  // 如果自定义端点失败，回退到常规API
                  statusResponse = await api.getTaskStatus(taskId);
                }
              } else {
                // 使用常规API查询
                statusResponse = await api.getTaskStatus(taskId);
              }
              
              console.log(`任务${taskId}状态:`, statusResponse.data);
              
              // 重置失败计数器
              failureCount = 0;
              
              // 处理不同格式的状态响应 - 使用增强的状态处理逻辑
              // 1. 获取原始状态数据
              const statusData = statusResponse.data;
              
              // 2. 检查所有可能的状态字段格式
              const taskStatus = statusData.status || 
                           statusData.task_status || 
                           statusData.state ||
                           (statusData.task && statusData.task.status);
              
              // 3. 提取进度信息
              const progress = statusData.progress || 
                               (statusData.task && statusData.task.progress) || 
                               '进行中';
              
              // 4. 提取可能的结果数据
              const taskResult = statusData.result || 
                             (statusData.task && statusData.task.result);
              
              // 5. 提取可能的错误信息 
              const taskError = statusData.error || 
                            statusData.message || 
                            (statusData.task && statusData.task.error) || 
                            '未知错误';
              
              console.log(`处理任务状态 - 状态: ${taskStatus}, 进度: ${progress}`);
              
              // 根据状态决定操作
              if (taskStatus === 'completed' || taskStatus === 'success') {
                clearPolling();
                analyzing.value = false;
                // 如果返回了直接结果，处理并显示
                if (taskResult) {
                  console.log("任务返回了直接结果:", taskResult);
                  result.value = taskResult; // 将结果赋值给组件状态
                  activeResultSections.value = form.options; // 确保结果区域显示正确的选项
                  // 如果有深度分析报告，也加入
                  if (taskResult.deep_analysis_report || taskResult.analysis_report) {
                     activeResultSections.value.push('deep_analysis_report');
                  }
                }
                ElMessage.success('分析完成！'); // 更新提示信息
              } else if (taskStatus === 'failed' || taskStatus === 'error') {
                clearPolling();
                analyzing.value = false;
                analysisError.value = taskError;
                ElMessage.error(`分析任务失败: ${taskError}`);
              } else if (taskStatus === 'processing' || taskStatus === 'running' || taskStatus === 'pending') {
                // 更新处理中的消息
                // 将进度格式化为百分比
                const progressDisplay = typeof progress === 'number' 
                  ? `${Math.round(progress * 100)}%` 
                  : progress;
                
                analyzingMessage.value = `分析中 (${progressDisplay})...结果将发送到AI Chat中`;
              } else {
                // 未知状态
                console.warn(`任务返回了未知状态: ${taskStatus}`);
                analyzingMessage.value = `分析中 (未知状态: ${taskStatus})...`;
              }
            } catch (error) {
              console.error('检查任务状态出错:', error);
              failureCount++;
              
              // 详细记录错误信息
              if (error.response) {
                console.error(`API响应状态: ${error.response.status}`);
                console.error('响应数据:', error.response.data);
              }
              
              // 添加错误处理逻辑，如果连续失败多次，停止轮询
              if (error.response && error.response.status === 404) {
                console.error(`任务ID ${taskId} 不存在或已被删除，失败次数: ${failureCount}/${MAX_FAILURES}`);
                
                if (failureCount >= MAX_FAILURES) {
                  clearPolling();
                  analyzing.value = false;
                  analysisError.value = '任务跟踪失败: 任务ID不存在或已被删除';
                  ElMessage.error('无法跟踪分析任务状态，请检查聊天窗口是否有结果通知');
                } else {
                  // 还未达到最大失败次数，显示警告但继续尝试
                  if (failureCount > 1) { // 只有在第二次失败后才显示警告
                    ElMessage.warning(`任务状态查询失败 (${failureCount}/${MAX_FAILURES})，将继续尝试...`);
                  }
                }
              } else {
                // 其他类型错误
                if (failureCount >= MAX_FAILURES) {
                  clearPolling();
                  analyzing.value = false;
                  analysisError.value = `任务状态查询失败: ${error.message || '未知错误'}`;
                  ElMessage.error('无法跟踪分析任务状态，请检查聊天窗口是否有结果通知');
                }
              }
            }
          }, 5000); // 每5秒检查一次
          
        } else {
          throw new Error('未收到有效的任务ID');
        }
      } else {
        // 直接同步分析
        const response = await api.analyzeText(analysisData);
        console.log('分析结果:', response.data);
        
        // 处理分析结果
        if (response.data) {
          result.value = response.data;
          activeResultSections.value = form.options;
          
          // 如果有深度分析报告，添加到活跃部分
          if (response.data.deep_analysis_report) {
            activeResultSections.value.push('deep_analysis_report');
          }
        } else {
          throw new Error('服务器返回了空结果');
        }
      }
    }
  } catch (error) {
    console.error('分析过程出错:', error);
    analysisError.value = error.message || '分析失败，请查看控制台了解详情';
    ElMessage.error(`分析失败: ${analysisError.value}`);
  } finally {
    // 仅当不是异步分析时才停止加载
    if (!form.forceAsync) {
      analyzing.value = false;
    }
  }
};

// Function to save the analysis result
const saveAnalysis = async () => {
  if (!result.value || Object.keys(result.value).length === 0) {
    ElMessage.warning('没有可保存的分析结果');
    return;
  }

  const loadingInstance = ElLoading.service({ text: '正在保存结果...' });

  try {
    // Construct the payload
    const payload = {
        // Use form.text which holds the original input
        text_summary: (form.text || '').substring(0, 150) + (form.text.length > 150 ? '...' : ''),
        result: result.value, // The analysis result object
        // Include provider/model only if it was a deep analysis
        provider: analysisType.value === 'deep' ? form.provider || null : null,
        model: analysisType.value === 'deep' ? form.model || null : null,
        timestamp: new Date().toISOString(),
        analysis_type: analysisType.value === 'deep' ? 'text_deep' : 'text_basic',
        original_text: form.text // Include the full original text
        // Add template if used?
        // template: analysisType.value === 'deep' ? form.template || null : null,
    };

    // Log the payload for debugging
    console.log("Saving Text Analysis Payload:", payload);

    // Call the backend API (assuming function name in api.js is saveTextAnalysisResult)
    // Verify this function name in src/services/api.js if needed
    const response = await api.saveTextAnalysisResult(payload);

    console.log("Save response:", response.data);
    ElMessage.success(response.data?.message || '文本分析结果已保存');

  } catch (error) {
    console.error('保存文本分析结果失败:', error);
    ElMessage.error(`保存文本分析结果失败: ${error.response?.data?.detail || error.message || '请检查后端服务。'}`);
  } finally {
    loadingInstance.close();
  }
};

// --- Constants for LocalStorage ---
const SETTINGS_KEY = 'glyphmindUISettings';
const MODULE_KEY = 'textAnalysis';
// ---------------------------------

// --- LocalStorage Load Function ---
const loadSettings = () => {
  try {
    const allSettings = localStorage.getItem(SETTINGS_KEY);
    if (allSettings) {
      const parsedSettings = JSON.parse(allSettings);
      const moduleSettings = parsedSettings[MODULE_KEY];
      if (moduleSettings) {
        console.log('Loading saved text analysis settings:', moduleSettings);
        if (moduleSettings.analysisType) analysisType.value = moduleSettings.analysisType;
        if (moduleSettings.options) form.options = moduleSettings.options;
        if (moduleSettings.provider) form.provider = moduleSettings.provider;
        if (moduleSettings.model) form.model = moduleSettings.model;
        if (moduleSettings.template) form.template = moduleSettings.template;
        if (typeof moduleSettings.forceAsync === 'boolean') form.forceAsync = moduleSettings.forceAsync;
        // Update provider models if provider loaded
        if (form.provider) fetchModels(form.provider);
      }
    }
  } catch (error) {
    console.error('Failed to load UI settings from localStorage:', error);
    // Optional: Clear corrupted settings
    // localStorage.removeItem(SETTINGS_KEY);
  }
};

// --- LocalStorage Save Function ---
const saveSettings = () => {
  try {
    const allSettings = JSON.parse(localStorage.getItem(SETTINGS_KEY) || '{}');
    allSettings[MODULE_KEY] = {
      analysisType: analysisType.value,
      options: form.options,
      provider: form.provider,
      model: form.model,
      template: form.template,
      forceAsync: form.forceAsync
    };
    localStorage.setItem(SETTINGS_KEY, JSON.stringify(allSettings));
    console.log('Saved text analysis settings:', allSettings[MODULE_KEY]);
  } catch (error) {
    console.error('Failed to save UI settings to localStorage:', error);
  }
};

// --- Watchers to trigger saving ---
watch(analysisType, saveSettings);
watch(form, saveSettings, { deep: true }); // Watch the entire form object deeply

// 添加getProviderWithEmoji函数
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

// 保存模型选择到本地存储
watch(() => form.model, (newModel) => {
  if (form.provider && newModel) {
    localStorage.setItem(`${form.provider}_last_model`, newModel);
    console.log(`保存 ${form.provider} 的模型选择: ${newModel}`);
  }
});

// 1. 在 provider/model 选择框旁加刷新按钮
// 2. 选择时写入 localStorage，加载时恢复
// 3. 切换 provider 时清除 model 缓存
// 4. 拉取新 options 后校验缓存
// 5. 代码注释清晰

// 添加刷新按钮逻辑
const refreshingProvider = ref(false);
const refreshingModel = ref(false);

const refreshProvider = async () => {
  refreshingProvider.value = true;
  await fetchProviders();
  refreshingProvider.value = false;
};

const refreshModel = async () => {
  refreshingModel.value = true;
  await fetchModels(form.provider);
  refreshingModel.value = false;
};
</script>

<style lang="scss" scoped>
.text-analysis {
  margin: 0 auto;
  padding: 20px;
}

.analysis-card {
  margin-bottom: 20px;
}

.gm-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  
  .left-section {
    display: flex;
    align-items: center;
    gap: 12px;
    
    h2 {
      margin: 0;
      font-size: 18px;
      font-weight: 600;
    }
  }
}

.section-actions {
  display: flex;
  align-items: center;
}

.api-test-status {
  margin-left: 15px;
  font-size: 12px;
  display: inline-flex; 
  align-items: center; 
  padding: 3px 6px;
  border-radius: 4px;
  line-height: 1.5; 
  vertical-align: middle;
  color: var(--el-text-color-secondary);

  .el-icon {
    margin-right: 4px;
    font-size: 14px;
  }
  
  &--success {
    color: var(--el-color-success);
  }
  &--warning {
    color: var(--el-color-warning);
  }
  &--error {
    color: var(--el-color-danger);
  }
  
  &--pending {
    color: var(--el-text-color-secondary);
  }
}

/* 上传按钮样式 */
.upload-button {
  background-color: #42b983 !important;
  border-color: #42b983 !important;
  color: white !important;
  border-radius: 4px;
  font-weight: 500;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 8px 16px;
  transition: all 0.3s ease;
  
  &:hover, &:focus {
    background-color: #53d6a4 !important;
    border-color: #53d6a4 !important;
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(66, 185, 131, 0.3);
  }
  
  .el-icon {
    margin-right: 6px;
  }
}

/* 简化的输入区域样式 */
.gm-input-container {
  position: relative;
  display: flex;
  flex-direction: column;
}

.gm-upload-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-top: 12px;
}

.gm-uploaded-file-info {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 10px;
  background-color: rgba(240, 249, 235, 0.8);
  padding: 8px 12px;
  border-radius: 4px;
  border: 1px solid #e1f3d8;
  
  .el-tag {
    display: flex;
    align-items: center;
    
    .el-icon {
      margin-right: 4px;
    }
  }
}

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

/* 结果容器样式 */
.analysis-results-container {
  margin-top: 24px;
  padding: 16px;
  border-radius: 6px;
  background-color: rgba(250, 250, 250, 0.6);
  border: 1px solid #ebeef5;
  transition: all 0.3s ease;
}

/* Dark mode specific styles */
:deep(.dark) {
  .gm-upload-loading-overlay {
    background-color: rgba(0, 0, 0, 0.7);
  }
  
  .gm-upload-loading-content {
    background-color: var(--el-bg-color-overlay);
  }
  
  .gm-uploaded-file-info {
    background-color: rgba(15, 35, 15, 0.6);
    border-color: #2b3e26;
  }
  
  .analysis-results-container {
    background-color: rgba(30, 30, 30, 0.6);
    border-color: #333;
  }
}

/* 表单底部按钮样式 */
.form-action-buttons {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
  gap: 10px;
}
</style>