<template>
  <div class="style-transfer">
    <el-card class="feature-card">
      <template #header>
        <div class="gm-card-header">
          <div class="left-section">
            <h2 class="feature-title">{{ addEmoji('风格迁移', 'menu', 'style-transfer') }}</h2>
            <el-switch
              v-model="isDarkMode"
              @change="toggleDarkMode"
              inline-prompt
              :active-icon="Sunny"
              :inactive-icon="Moon"
              class="theme-switch"
            />
          </div>
        </div>
      </template>
      
      <el-form :model="form" label-width="120px" ref="transferFormRef" :rules="formRules">
        <el-form-item label="输入方式">
          <el-radio-group v-model="form.inputType">
            <template v-for="option in inputTypeOptions" :key="option.value">
              <el-radio :value="option.value">
                <span v-if="option.value === 'text'">{{ addEmoji('直接输入', 'feature', 'ui-input') }}</span>
                <span v-else-if="option.value === 'file'">{{ addEmoji('上传文件', 'menu', 'upload') }}</span>
                <span v-else-if="option.value === 'analysis'">{{ addEmoji('使用分析报告', 'feature', 'function-analyze') }}</span>
              </el-radio>
            </template>
          </el-radio-group>
        </el-form-item>
        
        <el-form-item v-if="form.inputType === 'text'" label="原文" prop="sourceText">
          <el-input
            v-model="form.sourceText"
            type="textarea"
            :rows="10"
            placeholder="请输入要模仿风格的原文..."
            clearable
            :disabled="transferring" 
            class="gm-textarea"
            :class="{'has-content': form.sourceText.trim().length > 0}"
          />
        </el-form-item>
        
        <el-form-item v-if="form.inputType === 'file'" label="上传文件" prop="fileList">
          <!-- 文件上传区域 -->
          <div v-if="!form.sourceText && !isUploadingExtracting"> 
            <el-upload
              ref="uploadRef"
              class="gm-text-uploader"
              action="" 
              :http-request="handleFileUpload" 
              :on-remove="handleFileRemove" 
              :on-error="handleUploadError"
              :before-upload="beforeUpload"
              :file-list="fileList" 
              :limit="1" 
              :auto-upload="true"
              :disabled="transferring" 
            >
              <el-button 
                class="upload-button"
                :loading="isUploadingExtracting"
                size="default"
                type="primary" 
                plain 
              >
                <el-icon><UploadFilled /></el-icon>
                {{ addEmoji('点击上传文件', 'menu', 'import') }}
              </el-button>
              <template #tip>
                <div class="el-upload__tip">
                  支持 .txt, .pdf, .docx, .epub, .md 格式文件，仅限单个文件。
                </div>
              </template>
            </el-upload>
          </div>

          <!-- 上传/提取中文本 -->
          <div v-if="isUploadingExtracting" class="gm-uploading-status">
            <el-icon class="is-loading"><Loading /></el-icon>
            <span>正在上传并提取文件内容，请稍候...</span>
          </div>

          <!-- 文件内容预览/编辑区 -->
          <div v-if="form.sourceText && !isUploadingExtracting" class="gm-uploaded-file-content">
             <div class="gm-file-header">
                <el-tag type="success" size="small" class="gm-file-tag">
                  <el-icon><Document /></el-icon>
                  <span>{{ loadedFile?.name || '已加载内容' }}</span>
                </el-tag>
                <div class="gm-file-actions">
                  <el-button type="primary" size="small" @click="toggleSourceTextEditable" plain>
                    <el-icon><Edit v-if="!sourceTextEditable" /><Check v-else /></el-icon>
                    {{ sourceTextEditable ? addEmoji('完成编辑', 'menu', 'confirm') : addEmoji('编辑内容', 'menu', 'edit') }}
                  </el-button>
                  <el-button type="danger" size="small" @click="clearLoadedFile" plain>
                    <el-icon><Delete /></el-icon>
                    {{ addEmoji('清除文件', 'menu', 'clear') }}
                  </el-button>
                </div>
              </div>
              
              <!-- 文本区域 -->
              <el-input
                v-model="form.sourceText"
                type="textarea"
                :rows="10"
                :placeholder="loadedFile ? '文件内容已加载' : '请输入原文...'" 
                :readonly="!sourceTextEditable" 
                :disabled="transferring"
                class="gm-textarea content-textarea"
                :class="{'has-content': form.sourceText.trim().length > 0, 'is-editable': sourceTextEditable}"
              />
          </div>
        </el-form-item>
        
        <el-form-item v-if="form.inputType === 'analysis'" label="选择分析报告" prop="selectedAnalysis">
          <div class="select-with-button">
            <el-select 
              v-model="form.selectedAnalysis" 
              placeholder="请选择分析报告" 
              clearable 
              filterable
              @change="handleAnalysisReportChange"
            >
              <el-option-group v-bind:label="addEmoji('文本分析报告', 'feature', 'text_stats')">
                <el-option
                  v-for="report in textAnalysisReports"
                  :key="report.id"
                  :label="report.name"
                  :value="report.id" 
                />
              </el-option-group>
              <el-option-group v-bind:label="addEmoji('文学分析报告', 'feature', 'creative-writing')">
                <el-option
                  v-for="report in literatureAnalysisReports"
                  :key="report.id"
                  :label="report.name"
                  :value="report.id" 
                />
              </el-option-group>
            </el-select>
            <el-button type="primary" text @click="fetchAllAnalysisReports" class="refresh-button">
              <el-icon><RefreshRight /></el-icon>
              {{ addEmoji('刷新', 'menu', 'refresh') }}
            </el-button>
          </div>
          
          <div v-if="form.selectedAnalysis && analysisReportContent" class="gm-analysis-report-preview">
            <div class="gm-report-header">
              <h4>{{ addEmoji('报告内容预览', 'menu', 'preview') }}</h4>
              <el-button type="primary" size="small" @click="openReportPreviewDialog" plain>
                <el-icon><ViewIcon /></el-icon>
                {{ addEmoji('查看完整报告', 'menu', 'view') }}
              </el-button>
            </div>
            <div class="gm-report-content-preview">
              {{ shortReportContent }}
            </div>
          </div>
        </el-form-item>
        
        <el-form-item label="新主题" prop="newTheme">
          <el-input
            v-model="form.newTheme"
            type="textarea"
            :rows="6"
            :placeholder="addEmoji('请输入新的主题或观点...', 'feature', 'theme-change')"
            clearable
            class="gm-textarea"
            :class="{'has-content': form.newTheme.trim().length > 0}"
          />
        </el-form-item>
        
        <el-form-item :label="addEmoji('AI 模型', 'feature', 'function-generate')" required>
          <el-row :gutter="10" style="width: 100%">
            <el-col :span="11">
              <el-form-item prop="provider" style="width: 100%; margin-bottom: 0;">
                <el-select 
                  v-model="form.provider" 
                  placeholder="选择 API 服务商" 
                  @change="handleProviderChange"
                  filterable
                  clearable
                  style="width: 100%;"
                >
                  <el-option
                    v-for="provider in availableProviders"
                    :key="provider.name"
                    :label="provider.display_name"
                    :value="provider.name"
                  >
                    <div class="provider-option">
                      <span class="provider-emoji">{{ getEmoji('provider', provider.name, '⚡') }}</span>
                      <span class="provider-name">{{ provider.display_name }}</span>
                    </div>
                  </el-option>
                </el-select>
              </el-form-item>
            </el-col>
            <el-col :span="2" class="divider-col">
              <el-icon><Right /></el-icon>
            </el-col>
            <el-col :span="11">
              <el-form-item prop="model" style="width: 100%; margin-bottom: 0;">
                <el-select 
                  v-model="form.model" 
                  placeholder="选择模型 (必选)" 
                  :disabled="!form.provider || loadingModels"
                  :loading="loadingModels"
                  filterable
                  clearable
                  style="width: 100%;"
                >
                  <el-option
                    v-for="modelName in availableModels"
                    :key="modelName"
                    :label="modelName"
                    :value="modelName"
                  >
                    <div class="model-option">
                      <span class="model-name">{{ modelName }}</span>
                    </div>
                  </el-option>
                  <template #empty>
                    <div style="padding: 10px; text-align: center; color: #999;">
                      {{ loadingModels ? addEmoji('正在加载模型列表...', 'feature', 'loading') : '暂无可用模型' }}
                    </div>
                  </template>
                </el-select>
                
                <!-- 添加模型加载状态提示 -->
                <div v-if="loadingModels" class="loading-models-hint">
                  <el-icon class="is-loading"><Loading /></el-icon>
                  <span>{{ addEmoji('正在加载模型列表...', 'feature', 'loading') }}</span>
                </div>
                <div v-else-if="form.provider && availableModels.length === 0" class="no-models-hint">
                  <el-icon><Warning /></el-icon>
                  <span>{{ addEmoji('未加载到任何模型，请检查API连接', 'feature', 'api_error') }}</span>
                  <el-button 
                    type="primary" 
                    link 
                    size="small" 
                    @click="reloadModels" 
                    class="refresh-btn"
                  >
                    <el-icon><RefreshRight /></el-icon>
                    {{ addEmoji('刷新模型', 'menu', 'refresh') }}
                  </el-button>
                </div>
              </el-form-item>
            </el-col>
          </el-row>
        </el-form-item>
      </el-form>
      
      <!-- Add action button here -->
      <div class="form-action-buttons">
        <el-button 
          type="primary" 
          @click="startTransfer" 
          :loading="transferring" 
          :disabled="!canStartTransfer"
          class="action-button"
        >
          <el-icon class="el-icon--left"><MagicStick /></el-icon>
          {{ addEmoji('开始生成', 'feature', 'function-generate') }}
        </el-button>
      </div>
      
      <div v-if="transferring" class="gm-loading-container">
        <el-icon class="is-loading" size="20"><Loading /></el-icon>
        <span>{{ addEmoji('正在提交生成请求，请稍候...', 'feature', 'waiting') }}</span>
      </div>
      
      <div v-if="result" class="gm-result-container">
        <h3 class="gm-result-title">{{ addEmoji('生成结果', 'feature', 'function-generate') }}</h3>
        <el-input
          v-model="result"
          type="textarea"
          :rows="15" 
          :autosize="{ minRows: 10, maxRows: 30 }"
          readonly
          class="gm-result-textarea"
        />
        <div class="form-action-buttons" style="justify-content: flex-start; margin-top: 15px;">
          <el-button type="primary" @click="copyResult">
            <el-icon class="el-icon--left"><CopyDocument /></el-icon>{{ addEmoji('复制结果', 'menu', 'copy') }}
          </el-button>
          <el-button 
            type="success" 
            plain
            @click="saveTransferResult" 
            :loading="isSaving"
            :disabled="isSaving"
           >
            <el-icon class="el-icon--left"><FolderChecked /></el-icon>
             {{ addEmoji('保存结果', 'menu', 'save') }}
          </el-button>
        </div>
      </div>
      <el-empty v-else-if="!transferring && transferAttempted" description="生成失败或未返回有效结果"></el-empty>
    </el-card>
  </div>

  <!-- 添加文本预览对话框 -->
  <el-dialog
    v-model="textPreviewDialogVisible"
    :title="textPreviewDialogTitle"
    width="80%"
    destroy-on-close
    top="5vh"
  >
    <el-input
      v-model="previewText"
      type="textarea"
      :rows="20"
      :readonly="!previewEditable"
      class="gm-preview-textarea"
    />
    <template #footer>
      <span class="dialog-footer">
        <el-button type="primary" @click="savePreviewText" v-if="previewEditable">
          {{ addEmoji('保存修改', 'menu', 'save') }}
        </el-button>
        <el-button @click="togglePreviewEditable" v-if="!previewEditable">
          <el-icon class="el-icon--left"><Edit /></el-icon>
          {{ addEmoji('编辑内容', 'menu', 'edit') }}
        </el-button>
        <el-button @click="togglePreviewEditable" v-else>
          {{ addEmoji('取消编辑', 'menu', 'cancel') }}
        </el-button>
        <el-button @click="textPreviewDialogVisible = false">
          {{ addEmoji('关闭', 'menu', 'cancel') }}
        </el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script>
import { ref, reactive, computed, onMounted, watch, onUnmounted } from 'vue'
import { UploadFilled, RefreshRight, CopyDocument, Right, Loading, MagicStick, Moon, Sunny, Delete, Document, View as ViewIcon, Edit, Check, FolderChecked, Warning } from '@element-plus/icons-vue'
import { ElMessage, ElButton, ElIcon, ElRadioGroup, ElRadio, ElForm, ElFormItem, ElInput, ElRow, ElCol, ElSelect, ElOption, ElOptionGroup, ElUpload, ElTag, ElDialog, ElEmpty } from 'element-plus'
import api from '../../services/api'
import { addEmoji, getEmoji } from '../../assets/emojiMap.js'

export default {
  name: 'StyleTransfer',
  components: {
      ElButton, ElIcon, ElRadioGroup, ElRadio, ElForm, ElFormItem, ElInput, ElRow, ElCol, 
      ElSelect, ElOption, ElOptionGroup, ElUpload, ElTag, ElDialog, ElEmpty,
      UploadFilled, RefreshRight, CopyDocument, Right, Loading, MagicStick, 
      Delete, Document, ViewIcon, Edit, Check, FolderChecked, Warning
  },
  setup() {
    // ----------------------------------
    // Refs and Reactive Objects
    // ----------------------------------
    const transferFormRef = ref(null);
    const uploadRef = ref(null);
    const fileList = ref([]);
    const loadedFile = ref(null);
    const sourceTextEditable = ref(false);
    const isUploadingExtracting = ref(false);
    const textAnalysisReports = ref([]);
    const literatureAnalysisReports = ref([]);
    const analysisReportContent = ref('');
    const availableProviders = ref([]);
    const availableModels = ref([]);
    const loadingModels = ref(false);
    const transferring = ref(false);
    const result = ref('');
    const isDarkMode = ref(localStorage.getItem('darkMode') === 'true');
    const shortReportContent = ref('');
    const textPreviewDialogTitle = ref('');
    const previewText = ref('');
    const previewEditable = ref(false);
    const transferAttempted = ref(false);
    const isSaving = ref(false);
    const isSavingPreview = ref(false);
    const textPreviewDialogVisible = ref(false);
    const loadingAnalysisReports = ref(false);
    const allResults = ref([]);

    const form = reactive({
      inputType: 'text',
      sourceText: '',
      fileList: [],
      uploadedFilePath: null,
      selectedAnalysis: null,
      newTheme: '',
      provider: null,
      model: null,
    });

    // ----------------------------------
    // Computed Properties
    // ----------------------------------
    const formRules = computed(() => ({
      sourceText: [
        { validator: validateSourceInput, trigger: 'blur' }
      ],
      selectedAnalysis: [
        { required: form.inputType === 'analysis', message: '请选择分析报告', trigger: 'change' }
      ],
      newTheme: [
        { required: true, message: '请输入新主题', trigger: 'blur' }
      ],
      provider: [
        { required: true, message: '请选择 API 服务商', trigger: 'change' }
      ],
      model: [
        { required: true, message: '请选择模型', trigger: 'change' }
      ]
    }));

    const canStartTransfer = computed(() => {
      const hasInput = (form.inputType === 'text' && form.sourceText.trim()) || 
                       (form.inputType === 'file' && form.uploadedFilePath) ||
                       (form.inputType === 'analysis' && form.selectedAnalysis);
      return hasInput && form.newTheme.trim() && form.provider && form.model && !transferring.value;
    });

    const inputTypeOptions = computed(() => [
      { value: 'text' },
      { value: 'file' },
      { value: 'analysis' }
    ]);

    // ----------------------------------
    // Validation Functions
    // ----------------------------------
    const validateSourceInput = (rule, value, callback) => {
      if (form.inputType === 'text' && !form.sourceText.trim()) {
        callback(new Error('请输入原文'));
      } else if (form.inputType === 'file' && !form.sourceText.trim() && !loadedFile.value) {
        callback(new Error('请上传文件或输入原文'));
      } else {
        callback();
      }
    };

    // ----------------------------------
    // API Fetching Functions
    // ----------------------------------
    const fetchProviders = async () => {
      try {
        const timestamp = Date.now();
        const response = await api.getProviders(`?_t=${timestamp}`);
        console.log("原始API提供商数据:", response);
        const data = response.data || response;
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
      if (!providerName) {
        availableModels.value = [];
        return;
      }
      loadingModels.value = true;
      availableModels.value = []; 
      form.model = '';
      console.log(`[fetchModels] 正在获取 ${providerName} 的模型列表...`);
      try {
        const timestamp = Date.now();
        const response = await api.getModels(`${providerName}?_t=${timestamp}`);
        console.log(`获取到 ${providerName} 的模型列表:`, response);
        const data = response.data || response;
        let modelList = [];
        if (Array.isArray(data)) {
          modelList = data;
        } else if (data && data.models && Array.isArray(data.models)) {
          modelList = data.models;
        } else {
          console.error(`获取 ${providerName} 的模型列表返回了意外的数据结构:`, data);
          availableModels.value = [];
          ElMessage.warning(`获取 ${providerName} 的模型列表格式异常`);
          loadingModels.value = false;
          return;
        }
        availableModels.value = modelList.map(model => {
          if (typeof model === 'string') return model;
          if (typeof model === 'object' && model !== null) {
            if (model.id) return model.id;
            if (model.name) return model.name;
            if (model.model) return model.model;
          }
          return String(model);
        });
        console.log(`成功加载 ${availableModels.value.length} 个模型:`, availableModels.value);
        if (availableModels.value.length > 0) {
          setTimeout(() => {
            form.model = availableModels.value[0];
            console.log(`自动选择第一个模型: ${form.model}`);
          }, 200);
        }
      } catch (error) {
        console.error(`获取 ${providerName} 的模型列表失败:`, error);
        ElMessage.error(`无法加载 ${providerName} 的模型列表: ${error.message || '未知错误'}`);
        availableModels.value = [];
        form.model = '';
      } finally {
        loadingModels.value = false;
      }
    };

    const fetchAllAnalysisReports = async () => {
      loadingAnalysisReports.value = true;
      textAnalysisReports.value = [];
      literatureAnalysisReports.value = [];
      allResults.value = [];
      try {
        console.log("[fetchAllAnalysisReports] 开始获取分析报告列表...");
        const response = await api.getResults();
        console.log("[fetchAllAnalysisReports] API响应:", response);
        
        if (!response || !response.data) {
          console.error("[fetchAllAnalysisReports] API返回了无效的数据结构:", response);
          ElMessage.warning("获取分析报告列表失败: 返回了无效的数据结构");
          return;
        }
        
        allResults.value = response.data || [];
        if (allResults.value.length === 0) {
          console.warn("[fetchAllAnalysisReports] API返回了空数组，没有找到任何分析报告");
          ElMessage.info("未找到任何分析报告");
          return;
        }
        
        console.log("[fetchAllAnalysisReports] 获取到的所有报告:", allResults.value);
        
        // 处理文本分析报告
        const textReports = allResults.value.filter(r => 
          r.type === 'text' || r.type === 'text_basic' || r.type === 'text_deep'
        );
        console.log("[fetchAllAnalysisReports] 过滤出的文本分析报告:", textReports);
        
        textAnalysisReports.value = textReports.map(report => ({
          id: report.result_id,
          name: report.name || `文本分析 - ${new Date(report.timestamp).toLocaleString()}`,
          type: 'text'
        }));
        
        // 处理文学分析报告
        const literatureReports = allResults.value.filter(r => 
          r.type === 'literature' || r.type === 'literature_v2'
        );
        console.log("[fetchAllAnalysisReports] 过滤出的文学分析报告:", literatureReports);
        
        literatureAnalysisReports.value = literatureReports.map(report => ({
          id: report.result_id,
          name: report.name || `文学分析 - ${new Date(report.timestamp).toLocaleString()}`,
          type: 'literature'
        }));
        
        console.log(`[fetchAllAnalysisReports] 成功获取 ${textAnalysisReports.value.length} 个文本报告和 ${literatureAnalysisReports.value.length} 个文学报告`);
        
        // 如果URL中有resultId参数，自动选择该报告
        const urlParams = new URLSearchParams(window.location.search);
        const preselectedId = urlParams.get('resultId');
        if (preselectedId) {
          const isTextReport = textAnalysisReports.value.some(r => r.id === preselectedId);
          const isLiteratureReport = literatureAnalysisReports.value.some(r => r.id === preselectedId);
          
          if (isTextReport || isLiteratureReport) {
            console.log(`[fetchAllAnalysisReports] 从URL参数中检测到预选报告ID: ${preselectedId}`);
            form.inputType = 'analysis';
            form.selectedAnalysis = preselectedId;
            
            // 加载该报告内容
            setTimeout(() => {
              handleAnalysisReportChange(preselectedId);
            }, 100);
          }
        }
      } catch (error) {
        console.error("[fetchAllAnalysisReports] 获取分析报告列表失败:", error);
        if (error.response) {
          console.error("[fetchAllAnalysisReports] HTTP状态码:", error.response.status);
          console.error("[fetchAllAnalysisReports] 响应数据:", error.response.data);
        }
        if (!error.isSilent) {
          ElMessage.error(`无法加载分析报告列表: ${error.message || '未知错误'}`);
        }
      } finally {
        loadingAnalysisReports.value = false;
      }
    };

    // ----------------------------------
    // Event Handlers
    // ----------------------------------
    const handleProviderChange = async (providerName) => {
      form.model = '';
      availableModels.value = [];
      if (providerName) {
        console.log(`切换到新的模型供应商，强制刷新模型列表：${providerName}`);
        loadingModels.value = true;
        setTimeout(() => { fetchModels(providerName); }, 100);
      } else {
        console.log("Provider为空，不加载模型");
      }
      saveCurrentUiState();
    };

    const handleFileUpload = async (options) => {
      const { file, onSuccess, onError, onProgress } = options;
      loadedFile.value = null;
      form.sourceText = '';
      form.uploadedFilePath = null;
      isUploadingExtracting.value = true;
      sourceTextEditable.value = false;
      ElMessage.info(`正在上传并提取文件 "${file.name}"...`);
      try {
        const response = await api.uploadAndExtractText(file, (progressEvent) => {
          if (progressEvent.lengthComputable) {
            const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            onProgress({ percent: percentCompleted });
          }
        });
        console.log("文件上传提取响应:", response);
        const responseData = response.data || response;
        if (responseData && responseData.extracted_text) {
          loadedFile.value = { name: responseData.original_filename || file.name };
          form.sourceText = responseData.extracted_text;
          form.uploadedFilePath = responseData.file_path || null;
          console.log(`文件 "${loadedFile.value.name}" 内容提取成功 (${form.sourceText.length} 字符)`);
          console.log("loadedFile.value:", loadedFile.value);
          ElMessage.success(`文件 "${file.name}" 内容提取成功！`);
          onSuccess(responseData);
          transferFormRef.value?.clearValidate('sourceText');
        } else {
          console.error("无效的响应格式:", responseData);
          ElMessage.error('从服务器获取提取文本失败：响应格式无效');
          clearLoadedFile();
          onError(new Error('从服务器获取提取文本失败：响应格式无效'));
        }
      } catch (error) {
        console.error("文件上传和提取过程中出错:", error);
        ElMessage.error(`上传或提取文件 "${file.name}" 失败: ${error.response?.data?.detail || error.message || '请检查后端服务和文件格式。'}`);
        clearLoadedFile();
        onError(error);
      } finally {
        isUploadingExtracting.value = false;
      }
    };

    const handleFileRemove = () => {
      form.uploadedFilePath = null;
      form.sourceText = '';
      loadedFile.value = null;
    };

    const handleUploadError = (err) => {
      console.error("El-upload 错误:", err);
      ElMessage.error('文件上传失败');
      fileList.value = [];
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
      form.sourceText = '';
      transferFormRef.value?.clearValidate('sourceText');
      return true;
    };

    const clearLoadedFile = () => {
      loadedFile.value = null;
      form.sourceText = '';
      form.uploadedFilePath = null;
      fileList.value = [];
      sourceTextEditable.value = false;
      if (uploadRef.value) {
        uploadRef.value.clearFiles();
      }
      ElMessage.info('已清除文件内容');
    };
    
    // *** Function for Issue 1 ***
    const toggleSourceTextEditable = () => {
      sourceTextEditable.value = !sourceTextEditable.value;
      console.log('Toggled sourceTextEditable to:', sourceTextEditable.value);
    };

    // *** Functions for Preview Dialog Editing ***
    const togglePreviewEditable = () => {
      previewEditable.value = !previewEditable.value;
      console.log('Toggled previewEditable to:', previewEditable.value);
    };

    const savePreviewText = async () => {
      if (!form.selectedAnalysis || !previewText.value) {
        ElMessage.warning('没有可保存的内容或原始报告ID');
        return;
      }
      isSavingPreview.value = true;
      console.log(`[savePreviewText] Attempting to save EDITED content from report ID: ${form.selectedAnalysis} as a NEW result.`);
      
      // Construct the payload for creating a NEW result
      // Match the backend SaveAnalysisPayload model
      const payload = {
          // Generate a summary for the new entry
          text_summary: previewText.value.substring(0, 150) + (previewText.value.length > 150 ? '...' : ''), 
          result: previewText.value, // The edited content is the main result
          provider: form.provider, // Carry over provider/model if relevant, or set defaults
          model: form.model,
          timestamp: new Date().toISOString(),
          // Determine analysis_type based on the original report if possible, else default
          analysis_type: 'text_edited', // Or derive from original: e.g., allResults.value.find(r => r.result_id === form.selectedAnalysis)?.type + '_edited'
          original_text: previewText.value // The edited text becomes the 'original_text' for this new entry
          // original_result_id: form.selectedAnalysis // Consider adding this field to backend/payload if useful for tracking edits
      };

      try {
        // Call the NEW function to save as a new result
        const response = await api.saveNewAnalysisResult(payload); 
        
        console.log("[savePreviewText] Save New Result Response:", response);

        // Expecting backend to return the ID of the newly created result
        if (response && response.data && response.data.id) {
            const newResultId = response.data.id;
            ElMessage.success(`编辑后的内容已保存为新报告 (ID: ${newResultId})！`);
            previewEditable.value = false; // Close edit mode
            
            // Update component state to reflect the NEWLY saved report
            analysisReportContent.value = previewText.value; 
            shortReportContent.value = analysisReportContent.value.substring(0, 200) + 
                                       (analysisReportContent.value.length > 200 ? '...' : '');
            
            // Refresh the report list to include the new one
            await fetchAllAnalysisReports(); 
            
            // Optionally, select the newly created report
            form.selectedAnalysis = newResultId; 
            textPreviewDialogTitle.value = `新分析报告内容预览: ${payload.text_summary.substring(0,30)}...`; // Update dialog title

        } else {
             console.error("[savePreviewText] Save response did not contain a new result ID:", response);
             ElMessage.error('保存成功，但未能获取新报告ID。');
             previewEditable.value = false; // Still close edit mode, but indicate potential issue
        }

      } catch (error) {
        console.error("[savePreviewText] Failed to save edited content as new result:", error);
        ElMessage.error(`保存新报告失败: ${error.response?.data?.detail || error.message || '请检查后端服务或API实现。'}`);
        // Keep editable state on error so user doesn't lose changes
      } finally {
        isSavingPreview.value = false;
      }
    };
    // ******************************************

    const handleAnalysisReportChange = async (reportId) => {
      form.selectedAnalysis = reportId;
      await fetchAnalysisReportContent(reportId);
    };

    const fetchAnalysisReportContent = async (reportId) => {
      if (!reportId) {
        console.warn("[fetchAnalysisReportContent] 未提供reportId，无法获取报告内容");
        return;
      }
      
      console.log(`[fetchAnalysisReportContent] 开始获取报告内容，ID: ${reportId}`);
      
      try {
        // 确定报告类型
        const isTextReport = textAnalysisReports.value.some(r => r.id === reportId);
        const isLiteratureReport = literatureAnalysisReports.value.some(r => r.id === reportId);
        let response;
        
        console.log(`[fetchAnalysisReportContent] 报告类型检测: isTextReport=${isTextReport}, isLiteratureReport=${isLiteratureReport}`);
        
        if (isTextReport) {
          console.log(`[fetchAnalysisReportContent] 获取文本分析报告内容, ID: ${reportId}`);
          response = await api.getTextAnalysisResult(reportId);
        } else if (isLiteratureReport) {
          console.log(`[fetchAnalysisReportContent] 获取文学分析报告内容, ID: ${reportId}`);
          response = await api.getLiteratureAnalysisResult(reportId);
        } else {
          console.error(`[fetchAnalysisReportContent] 未知的报告类型, ID: ${reportId}`);
          throw new Error('未知的报告类型，无法确定获取API');
        }
        
        console.log(`[fetchAnalysisReportContent] API响应:`, response);
        
        if (!response || !response.data) {
          console.error(`[fetchAnalysisReportContent] API返回无效数据:`, response);
          throw new Error('API返回了无效的数据结构');
        }
        
        let reportText = '';
        const responseData = response.data;
        
        // 提取报告内容的多级检查
        if (responseData.result) {
          console.log('[fetchAnalysisReportContent] 检测到result字段，尝试提取内容');
          
          // 深度分析报告
          if (responseData.result.deep_analysis_report && typeof responseData.result.deep_analysis_report === 'string') {
            reportText = responseData.result.deep_analysis_report;
            console.log('[fetchAnalysisReportContent] 从deep_analysis_report提取内容成功');
          } 
          // 基础分析报告
          else if (responseData.result.analysis_report && typeof responseData.result.analysis_report === 'string') {
            reportText = responseData.result.analysis_report.replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, '');
            console.log('[fetchAnalysisReportContent] 从analysis_report提取内容成功');
          }
          // 结果本身是字符串
          else if (typeof responseData.result === 'string') {
            reportText = responseData.result;
            console.log('[fetchAnalysisReportContent] 将result字符串直接作为报告内容');
          }
          // 结果是对象，尝试序列化
          else if (typeof responseData.result === 'object') {
            try {
              if (responseData.result.content && typeof responseData.result.content === 'string') {
                reportText = responseData.result.content;
                console.log('[fetchAnalysisReportContent] 从result.content提取到内容');
              } else {
                reportText = JSON.stringify(responseData.result, null, 2);
                console.log('[fetchAnalysisReportContent] 将result对象序列化为JSON字符串');
              }
            } catch (e) {
              console.error('[fetchAnalysisReportContent] 序列化result对象失败:', e);
              reportText = "[无法显示的复杂分析结果]";
            }
          }
        } 
        // 直接在响应根级别的分析报告
        else if (responseData.analysis_report && typeof responseData.analysis_report === 'string') {
          reportText = responseData.analysis_report.replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, '');
          console.log('[fetchAnalysisReportContent] 从根级analysis_report提取内容成功');
        }
        // 原始文本
        else if (responseData.original_text) {
          reportText = responseData.original_text;
          console.warn('[fetchAnalysisReportContent] 未找到分析报告内容，使用原始文本');
          ElMessage.warning('未找到分析报告内容，将使用原始文本进行迁移。');
        }
        // 其他可能的内容字段
        else if (responseData.text) {
          reportText = responseData.text;
          console.log('[fetchAnalysisReportContent] 使用text字段作为报告内容');
        }
        // 最后尝试使用整个响应数据
        else {
          console.error('[fetchAnalysisReportContent] 无法从响应中提取有效内容:', responseData);
          throw new Error('报告数据中缺少可用的分析结果或原始文本内容');
        }
        
        // 处理<think>标签
        if (reportText) {
          console.log(`[fetchAnalysisReportContent] 原始报告内容长度: ${reportText.length}`);
          
          // 移除<think>标签内容
          const thinkRegex = /<think>([\s\S]*?)<\/think>/g;
          reportText = reportText.replace(thinkRegex, '');
          reportText = reportText.replace(/<\/?think>/g, '');
          
          // 尝试解析JSON格式的内容
          try {
            const jsonObj = JSON.parse(reportText);
            if (jsonObj && jsonObj.content) {
              reportText = jsonObj.content;
              console.log('[fetchAnalysisReportContent] 从JSON格式中提取content字段成功');
            }
          } catch (e) {
            // 不是JSON格式，继续使用原内容
          }
          
          console.log(`[fetchAnalysisReportContent] 处理后的报告内容长度: ${reportText.length}`);
        } else {
          console.warn('[fetchAnalysisReportContent] 提取的报告内容为空');
          ElMessage.warning('从选定的报告中提取到的内容为空');
        }
        
        // 更新组件状态
        analysisReportContent.value = reportText;
        form.sourceText = reportText;
        shortReportContent.value = analysisReportContent.value.substring(0, 200) + (analysisReportContent.value.length > 200 ? '...' : '');
        
        // 设置对话框标题
        const reportName = responseData.name || (responseData._ && responseData._.name) || `分析报告 ${reportId}`;
        textPreviewDialogTitle.value = `分析报告内容预览: ${reportName}`;
        
        console.log(`[fetchAnalysisReportContent] 成功获取并处理报告内容，ID: ${reportId}`);
      } catch (error) {
        console.error("[fetchAnalysisReportContent] 获取或处理报告内容时出错:", error);
        if (error.response) {
          console.error("[fetchAnalysisReportContent] HTTP状态码:", error.response.status);
          console.error("[fetchAnalysisReportContent] 响应数据:", error.response.data);
        }
        ElMessage.error(`无法加载分析报告内容: ${error.message || '未知错误'}`);
        analysisReportContent.value = '';
        shortReportContent.value = '';
        // 返回到选择报告界面
        form.selectedAnalysis = '';
      }
    };

    const openReportPreviewDialog = () => {
      if (!analysisReportContent.value) {
        ElMessage.warning('没有可预览的报告内容');
        return;
      }
      previewText.value = analysisReportContent.value;
      previewEditable.value = false;
      textPreviewDialogVisible.value = true;
    };

    // ----------------------------------
    // Utility Functions
    // ----------------------------------
    const copyResult = () => {
      if (!result.value) return;
      navigator.clipboard.writeText(result.value)
        .then(() => ElMessage.success('已复制到剪贴板'))
        .catch(err => { console.error('复制失败:', err); ElMessage.error('复制失败'); });
    };

    const toggleDarkMode = () => {
      const htmlEl = document.documentElement;
      if (isDarkMode.value) {
        htmlEl.classList.add('dark');
      } else {
        htmlEl.classList.remove('dark');
      }
      localStorage.setItem('darkMode', isDarkMode.value);
    };

    const saveTransferResult = async () => {
      if (!result.value) {
        ElMessage.warning('没有可保存的迁移结果');
        return;
      }
      isSaving.value = true;
      try {
        const payload = {
          result: result.value,
          analysis_type: 'style',
          timestamp: new Date().toISOString(),
          provider: form.provider,
          model: form.model,
          source_info: form.inputType === 'text' 
            ? (form.sourceText || '').substring(0, 150) + (form.sourceText.length > 150 ? '...' : '')
            : `Report: ${form.selectedAnalysis || 'N/A'}`, 
          original_text: form.inputType === 'text' ? form.sourceText : null,
          new_theme: form.newTheme
        };
        console.log("Saving Style Transfer Payload:", payload);
        const response = await api.saveStyleTransferResult(payload);
        ElMessage.success(response.data?.message || '风格迁移结果已保存');
      } catch (error) {
        console.error('保存风格迁移结果失败:', error);
        ElMessage.error(`保存失败: ${error.response?.data?.detail || error.message || '请检查后端服务。'}`);
      } finally {
        isSaving.value = false;
      }
    };

    const reloadModels = async () => {
      if (!form.provider) {
        ElMessage.warning('请先选择API提供商');
        return;
      }
      ElMessage.info('正在强制刷新模型列表...');
      loadingModels.value = true;
      availableModels.value = [];
      form.model = '';
      if (window.caches) {
        try {
          const cacheKeys = await window.caches.keys();
          await Promise.all(cacheKeys.map(key => window.caches.delete(key)));
          console.log('已清理浏览器Cache API缓存');
        } catch (e) { console.error('清理Cache API失败:', e); }
      }
      try {
        await fetchModels(form.provider);
        if (availableModels.value.length > 0) {
          ElMessage.success(`成功加载 ${availableModels.value.length} 个模型`);
        } else {
          ElMessage.warning('未找到模型，请检查API连接和提供商设置');
        }
      } catch (error) {
        console.error('刷新模型列表失败:', error);
        ElMessage.error(`刷新模型列表失败: ${error.message || '未知错误'}`);
      } finally {
        loadingModels.value = false;
      }
    };

    // ----------------------------------
    // *** START TRANSFER FUNCTION (for Issue 2) ***
    // ----------------------------------
    const startTransfer = async () => {
      console.log('[startTransfer] Clicked!');
      if (!transferFormRef.value) {
        console.error('[startTransfer] transferFormRef is not available');
        return;
      }
      console.log('[startTransfer] Attempting form validation...');
      try {
        await transferFormRef.value.validate();
        console.log('[startTransfer] Form validation successful.');
      } catch (error) {
        console.error('[startTransfer] Form validation failed:', error);
        if (error && typeof error === 'object') {
          const errorFields = Object.keys(error).join(', ');
          ElMessage.warning(`表单验证失败，请检查字段: ${errorFields}`);
        } else {
          ElMessage.warning('请检查表单输入是否完整有效');
        }
        return;
      }
      transferring.value = true;
      result.value = '';
      transferAttempted.value = true;
      console.log('[startTransfer] Set transferring=true, cleared result.');
      try {
        let payloadSourceText = null;
        let payloadAnalysisReportId = null;
        if (form.inputType === 'text' || form.inputType === 'file') {
          payloadSourceText = form.sourceText;
          console.log('[startTransfer] Input type text/file, using sourceText.');
        } else if (form.inputType === 'analysis') {
          payloadAnalysisReportId = form.selectedAnalysis;
          payloadSourceText = analysisReportContent.value; 
          console.log('[startTransfer] Input type analysis, using selectedAnalysis ID and fetched report content as sourceText.');
        } else {
           console.error('[startTransfer] Unknown input type:', form.inputType);
           ElMessage.error('未知的输入类型');
           transferring.value = false;
           return;
        }
        const payload = {
          input_type: form.inputType,
          source_text: payloadSourceText,
          analysis_report_id: payloadAnalysisReportId,
          file_path: form.uploadedFilePath,
          new_theme: form.newTheme,
          provider: form.provider,
          model: form.model,
        };
        console.log('[startTransfer] Prepared Payload (source_text snippet):', { ...payload, source_text: payload.source_text ? payload.source_text.substring(0, 100) + '...' : null });
        console.log('[startTransfer] Calling api.performStyleTransfer...');
        const response = await api.performStyleTransfer(
          payload.input_type,
          payload.new_theme,
          payload.provider,
          payload.model,
          payload.source_text,
          payload.analysis_report_id
        );
        console.log('[startTransfer] API Response:', response);
        if (response && response.data && response.data.result) {
          // 处理结果中的<think>标签
          let resultText = response.data.result;
          
          // 移除<think>标签内容
          const thinkRegex = /<think>([\s\S]*?)<\/think>/g;
          resultText = resultText.replace(thinkRegex, '');
          resultText = resultText.replace(/<\/?think>/g, '');
          
          // 尝试解析JSON格式的内容
          try {
            const jsonObj = JSON.parse(resultText);
            if (jsonObj && jsonObj.content) {
              resultText = jsonObj.content;
              console.log('[startTransfer] 从JSON格式中提取content字段成功');
            }
          } catch (e) {
            // 不是JSON格式，继续使用原内容
          }
          
          result.value = resultText;
          ElMessage.success('风格迁移成功！');
        } else {
          console.error('[startTransfer] Unexpected API response structure:', response);
          ElMessage.error('风格迁移失败：API 返回无效数据');
          result.value = '';
        }
      } catch (error) {
        console.error('[startTransfer] API call failed:', error);
        const errorMsg = error.response?.data?.detail || error.message || '请检查后端服务和网络连接。';
        ElMessage.error(`风格迁移失败: ${errorMsg}`);
        result.value = '';
      } finally {
        console.log('[startTransfer] Setting transferring=false in finally block.');
        transferring.value = false;
      }
    };

    // ----------------------------------
    // UI State Persistence
    // ----------------------------------
    const UI_STATE_KEY = 'style-transfer';

    const saveCurrentUiState = async () => {
      try {
        const state = { provider: form.provider, model: form.model, input_type: form.inputType, selected_analysis: form.selectedAnalysis };
        await api.saveUiState(UI_STATE_KEY, state);
        console.log('StyleTransfer UI state saved');
      } catch (error) { console.error('Failed to save UI state:', error); }
    };

    const loadUiState = async () => {
      try {
        const response = await api.getUiState(UI_STATE_KEY);
        if (response?.data) {
          const state = response.data;
          console.log('Loaded UI state:', state);
          if (state.provider) form.provider = state.provider;
          if (state.model) form.model = state.model;
          if (state.input_type) form.inputType = state.input_type;
          if (state.selected_analysis) form.selectedAnalysis = state.selected_analysis;
          if (form.provider) { await fetchModels(form.provider); }
        }
      } catch (error) { console.error('Failed to load UI state:', error); }
    };

    // ----------------------------------
    // Lifecycle Hooks
    // ----------------------------------
    onMounted(async () => {
      console.log('风格迁移组件挂载，清除API缓存...');
      if (window.localStorage) {
        Object.keys(window.localStorage).forEach(key => {
          if (key.includes('_models_cache') || key.includes('api_cache_') || 
              key.includes('style_transfer_models_') || key.includes('_model_list')) {
            window.localStorage.removeItem(key);
            console.log(`已清除缓存项: ${key}`);
          }
        });
      }
      if (window.fetch) {
        console.log('注册全局防缓存拦截器');
        const originalFetch = window.fetch;
        window.fetch = function(url, options) {
          if (typeof url === 'string' && (url.includes('/models/') || url.includes('/providers'))) {
            const separator = url.includes('?') ? '&' : '?';
            url = `${url}${separator}_t=${Date.now()}`;
            console.log('防缓存URL:', url);
            options = options || {};
            options.headers = options.headers || {};
            options.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate';
            options.headers['Pragma'] = 'no-cache';
            options.headers['Expires'] = '0';
          }
          return originalFetch(url, options);
        };
      }
      await fetchProviders();
      await fetchAllAnalysisReports();
      await loadUiState();
    });

    onUnmounted(() => { saveCurrentUiState(); });

    // ----------------------------------
    // Watchers
    // ----------------------------------
    watch(() => form.inputType, (newType) => {
      if (newType !== 'text') form.sourceText = '';
      if (newType !== 'file') clearLoadedFile();
      if (newType !== 'analysis') form.selectedAnalysis = '';
      if (transferFormRef.value) transferFormRef.value.clearValidate(); 
    });

    watch(() => form.sourceText, (newText, oldText) => {
      if (newText && newText.trim() && !oldText && loadedFile.value && form.inputType === 'file') {
        console.log("用户开始在空文本区域输入内容，清除文件关联但保留输入内容");
        loadedFile.value = null;
        form.uploadedFilePath = null;
        fileList.value = [];
        if (uploadRef.value) uploadRef.value.clearFiles();
      }
    });

    watch(() => form.provider, (newProvider, oldProvider) => {
      if (newProvider) {
        localStorage.setItem('style_transfer_last_provider', newProvider);
        // 切换 provider 时清除 model 缓存
        localStorage.removeItem(`style_transfer_last_model_${oldProvider}`);
        form.model = '';
        availableModels.value = [];
        fetchModels(newProvider);
      }
    });

    watch(() => form.model, (newModel) => {
      if (form.provider && newModel) {
        localStorage.setItem(`style_transfer_last_model_${form.provider}`, newModel);
      }
    });

    // ----------------------------------
    // Return values exposed to template
    // ----------------------------------
    return {
      transferFormRef,
      uploadRef,
      fileList,
      loadedFile,
      sourceTextEditable,
      isUploadingExtracting,
      textAnalysisReports,
      literatureAnalysisReports,
      analysisReportContent,
      availableProviders,
      availableModels,
      loadingModels,
      transferring,
      result,
      isDarkMode,
      shortReportContent,
      textPreviewDialogTitle,
      previewText,
      previewEditable,
      transferAttempted,
      isSaving,
      isSavingPreview,
      textPreviewDialogVisible,
      allResults,
      form,
      formRules,
      canStartTransfer,
      inputTypeOptions,
      validateSourceInput,
      fetchProviders,
      fetchModels,
      fetchAllAnalysisReports,
      handleProviderChange,
      handleFileUpload,
      handleFileRemove,
      handleUploadError,
      beforeUpload,
      clearLoadedFile,
      toggleSourceTextEditable,
      handleAnalysisReportChange,
      fetchAnalysisReportContent,
      openReportPreviewDialog,
      copyResult,
      toggleDarkMode,
      saveTransferResult,
      reloadModels,
      startTransfer,
      addEmoji,
      getEmoji,
      Moon,
      Sunny,
      ViewIcon,
      togglePreviewEditable,
      savePreviewText
    };
  }
}
</script>

<style lang="scss" scoped>
.style-transfer {
  margin: 0 auto;
  padding: 20px;
}

.feature-card {
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

// Align the form label width with TextAnalysis
.el-form {
  --el-form-label-width: 100px !important; // Added to align label width
}

.select-with-button {
  display: flex;
  gap: 10px;
  align-items: center;

  .el-select {
    flex-grow: 1;
  }

  .refresh-button {
    flex-shrink: 0;
  }
}

.divider-col {
  display: flex;
  justify-content: center;
  align-items: center;
  color: var(--el-text-color-secondary);
}

.content-textarea {
  width: 100%;
  margin-top: 10px;
}

.gm-upload-container {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
  
.gm-uploaded-file-info {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 10px;
  
  .el-tag {
    display: flex;
    align-items: center;
    
    .el-icon {
      margin-right: 4px;
    }
  }
}
  
.gm-uploaded-file-content {
  width: 100%;
  margin-bottom: 15px;
  
  .gm-file-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 10px;
    padding: 8px 12px;
    background-color: var(--el-color-success-lighter);
    border-radius: 4px;
    border: 1px solid var(--el-color-success-light-8);
    
    .gm-file-actions {
      display: flex;
      gap: 8px;
    }
  }
}
  
.gm-result-container {
  margin-top: 24px;
  padding: 16px;
  border-radius: 6px;
  background-color: transparent;
  border: 1px solid var(--el-border-color-light);
  transition: all 0.3s ease;
  max-height: 900px;
  overflow-y: auto;
  
  .gm-result-title {
    font-size: 16px;
    margin-top: 0;
    margin-bottom: 16px;
    color: var(--el-text-color-primary);
  }
  
  // 添加内容溢出处理
  max-height: 900px;
  overflow-y: auto;
}
  
.gm-loading-container {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  margin: 15px 0;
  background-color: var(--el-color-primary-light-9);
  border-radius: 4px;
  border: 1px solid var(--el-color-primary-light-7);
  color: var(--el-color-primary);
  
  .el-icon {
    margin-right: 10px;
    font-size: 20px;
  }
  
  span {
    font-size: 14px;
  }
}

/* 添加模型加载状态提示样式 */
.loading-models-hint, .no-models-hint {
  margin-top: 8px;
  padding: 8px 12px;
  border-radius: 4px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.loading-models-hint {
  background-color: var(--el-color-success-lighter);
  border: 1px solid var(--el-color-success-light-8);
  color: var(--el-color-success);
  
  .el-icon {
    color: var(--el-color-success);
  }
}

.no-models-hint {
  background-color: var(--el-color-warning-lighter);
  border: 1px solid var(--el-color-warning-light-8);
  color: var(--el-color-warning);
  
  .el-icon {
    color: var(--el-color-warning);
  }
  
  .refresh-btn {
    margin-left: auto;
    color: var(--el-color-warning);
    
    &:hover {
      color: var(--el-color-warning-dark-2);
    }
  }
}

.gm-analysis-report-preview {
  margin-top: 10px;
  padding: 10px;
  background-color: transparent;
  border-radius: 4px;
  border: 1px solid var(--el-border-color-darker);

  .gm-report-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 10px;

    h4 {
      margin: 0;
      font-size: 16px;
      font-weight: 600;
    }
  }

  .gm-report-content-preview {
    margin-top: 10px;
    font-size: 14px;
    color: var(--el-text-color-secondary);
  }
}

.gm-preview-textarea {
  width: 100%;
  font-family: 'Consolas', 'Monaco', 'Courier New', monospace;
  
  :deep(.el-textarea__inner) {
    font-family: inherit;
    padding: 12px;
    line-height: 1.6;
    max-height: 70vh;
    overflow-y: auto;
    white-space: pre-wrap;
    word-break: break-word;
  }
}

.provider-option {
  display: flex;
  align-items: center;
  gap: 8px;
  
  .provider-emoji {
    font-size: 18px;
  }
  
  .provider-name {
    flex: 1;
  }
}

.model-option {
  display: flex;
  align-items: center;
  
  .model-name {
    flex: 1;
  }
}

.gm-result-textarea {
  :deep(.el-textarea__inner) {
    background-color: transparent;
    color: var(--el-text-color-primary);
    border-color: var(--el-border-color);
    font-family: var(--el-font-family);
    line-height: 1.6;
    padding: 12px;
    max-height: 800px;
    overflow-y: auto;
    white-space: pre-wrap;
    word-break: break-word;
  }
}

/* 深色模式适配 */
:deep(.dark) {
  .gm-analysis-report-preview {
    background-color: transparent;
    border-color: var(--el-border-color-darker);
    
    .gm-report-header h4 {
        color: var(--el-text-color-regular);
    }
    
    .gm-report-content-preview {
      color: var(--el-text-color-secondary);
    }
    
    .el-button--primary.is-plain {
        color: var(--el-color-primary-light-3);
        background: transparent;
        border-color: var(--el-color-primary-light-5);
    }
  }
  
  .gm-file-header {
    background-color: rgba(60, 60, 60, 0.3);
    border-color: var(--el-border-color-darker);
    
    .gm-file-tag span,
    .gm-file-tag .el-icon {
        color: #b0f2a3;
    }
    
    .el-button--primary.is-plain {
        color: var(--el-color-primary-light-3);
        background: transparent;
        border-color: var(--el-color-primary-light-5);
    }
    .el-button--danger.is-plain {
         color: var(--el-color-danger-light-3);
         background: transparent;
         border-color: var(--el-color-danger-light-5);
    }
  }
  
  .gm-result-container {
    background-color: transparent;
    border-color: var(--el-border-color-darker);
  }
  
  .gm-loading-container {
    background-color: rgba(18, 64, 110, 0.2);
    border-color: var(--el-color-primary-light-8);
  }
  
  /* 添加模型加载状态提示样式 */
  .loading-models-hint, .no-models-hint {
    margin-top: 8px;
    padding: 8px 12px;
    border-radius: 4px;
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 13px;
  }
  
  .loading-models-hint {
    background-color: var(--el-color-success-lighter);
    border: 1px solid var(--el-color-success-light-8);
    color: var(--el-color-success-light-3);
    
    .el-icon {
      color: var(--el-color-success-light-3);
    }
  }
  
  .no-models-hint {
    background-color: var(--el-color-warning-lighter);
    border: 1px solid var(--el-color-warning-light-8);
    color: var(--el-color-warning-light-3);
    
    .el-icon {
      color: var(--el-color-warning-light-3);
    }
    
    .refresh-btn {
      margin-left: auto;
      color: var(--el-color-warning-light-3);
      
      &:hover {
        color: var(--el-color-warning);
      }
    }
  }
}
</style>