<template>
  <el-card class="report-generator-view">
    <template #header>
      <div class="card-header">
        <span>智能研报生成器</span>
      </div>
    </template>

    <ReportForm 
      v-model:topic="topic"
      v-model:apiType="apiType"
      v-model:selectedOllamaModel="selectedOllamaModel"
      v-model:selectedCloudProvider="selectedCloudProvider"
      v-model:selectedCloudModel="selectedCloudModel"
      :ollamaModels="ollamaModels"
      :loadingOllamaModels="loadingOllamaModels"
      :cloudProviders="cloudProviders"
      :loadingCloudProviders="loadingCloudProviders"
      :cloudModels="cloudModels"
      :loadingCloudModels="loadingCloudModels"
      :isLoading="isLoading"
      @generate-report="handleGenerateReport"
      @cloud-provider-changed="fetchCloudModels"
    />

    <el-divider v-if="reportContent || errorText || isLoading" />

    <ReportLoading :isLoading="isLoading" />
    <ReportError :errorText="errorText" />
    <ReportDisplay :reportContent="reportContent" />

  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue';
import { ElMessage, ElDivider } from 'element-plus';
// Import new components
import ReportForm from '@/components/report-generator/ReportForm.vue';
import ReportLoading from '@/components/report-generator/ReportLoading.vue';
import ReportError from '@/components/report-generator/ReportError.vue';
import ReportDisplay from '@/components/report-generator/ReportDisplay.vue';
// Import services
import { generateReportAPI, generateCloudReportAPI } from '@/services/reportService'; // Assuming generateCloudReportAPI exists/will be created
import { getProviders, getModels } from '@/services/providerService';

// --- State managed by the parent view ---
const topic = ref('');
const apiType = ref('ollama'); // 'ollama' or 'cloud'

// Ollama related state
const selectedOllamaModel = ref(null);
const ollamaModels = ref([]);
const loadingOllamaModels = ref(false);

// Cloud API related state
const cloudProviders = ref([]);
const loadingCloudProviders = ref(false);
const selectedCloudProvider = ref(null);
const cloudModels = ref([]);
const loadingCloudModels = ref(false);
const selectedCloudModel = ref(null);

// Report generation process state
const isLoading = ref(false);
const reportContent = ref('');
const errorText = ref('');

// --- Data Fetching (kept in parent) ---
const fetchOllamaModels = async () => {
  loadingOllamaModels.value = true;
  ollamaModels.value = [];
  // selectedOllamaModel.value = null; // Keep selection if models reload
  console.log("[ReportGeneratorView] Fetching Ollama models...");
  try {
    const response = await getModels('ollama_report_handler');
    const data = response.data || response;
    let modelList = [];
    if (Array.isArray(data)) modelList = data;
    else if (data?.models && Array.isArray(data.models)) modelList = data.models;
    else if (data && Array.isArray(data.data)) modelList = data.data;
    else throw new Error('Unexpected models data structure');

    ollamaModels.value = modelList.map(model => {
      if (typeof model === 'string') return { value: model, label: model };
      if (typeof model === 'object' && model !== null) {
        const id = model.id || model.name || model.model;
        const label = model.name || id;
        if (id) return { value: id, label: label };
      }
      return null;
    }).filter(Boolean);

    console.log(`[ReportGeneratorView] Loaded ${ollamaModels.value.length} Ollama models.`);
    if (ollamaModels.value.length === 0) ElMessage.info('未从Ollama服务获取到可用模型列表。');

  } catch (error) {
    console.error("[ReportGeneratorView] Error fetching Ollama models:", error);
    ElMessage.error(`无法加载Ollama模型列表: ${error.message}`);
    ollamaModels.value = [];
  } finally {
    loadingOllamaModels.value = false;
  }
};

const fetchCloudProviders = async () => {
  loadingCloudProviders.value = true;
  cloudProviders.value = [];
  // selectedCloudProvider.value = null; // Keep selection if providers reload
  // selectedCloudModel.value = null;
  // cloudModels.value = [];
  console.log("[ReportGeneratorView] Fetching Cloud Providers...");
  try {
    const response = await getProviders();
    const data = response.data || response;
    if (!Array.isArray(data)) throw new Error('Unexpected providers data structure');

    cloudProviders.value = data
      .filter(p => p.name !== 'ollama_report_handler') 
      .map(provider => ({ 
        value: provider.name,
        label: provider.display_name || provider.name // Prefer display_name if available
      }));
      
    console.log(`[ReportGeneratorView] Loaded ${cloudProviders.value.length} cloud providers.`);
    if (cloudProviders.value.length === 0) ElMessage.info('未找到可用的云服务商配置。');

  } catch (error) {
    console.error("[ReportGeneratorView] Error fetching cloud providers:", error);
    ElMessage.error(`无法加载云服务商列表: ${error.message}`);
    cloudProviders.value = [];
  } finally {
    loadingCloudProviders.value = false;
  }
};

const fetchCloudModels = async (providerName) => {
  // Triggered by @cloud-provider-changed event from ReportForm
  if (!providerName) {
    cloudModels.value = [];
    selectedCloudModel.value = null;
    return;
  }
  loadingCloudModels.value = true;
  cloudModels.value = [];
  selectedCloudModel.value = null; // Reset model when provider changes
  console.log(`[ReportGeneratorView] Fetching Cloud models for: ${providerName}...`);
  try {
    const response = await getModels(providerName);
    const data = response.data || response;
    let modelList = [];
    if (Array.isArray(data)) modelList = data;
    else if (data?.models && Array.isArray(data.models)) modelList = data.models;
    else if (data && Array.isArray(data.data)) modelList = data.data;
    else throw new Error('Unexpected models data structure');

    cloudModels.value = modelList.map(model => {
       if (typeof model === 'string') return { value: model, label: model };
      if (typeof model === 'object' && model !== null) {
        const id = model.id || model.name || model.model;
        const label = model.name || id;
        if (id) return { value: id, label: label };
      }
      return null;
    }).filter(Boolean);

    console.log(`[ReportGeneratorView] Loaded ${cloudModels.value.length} models for ${providerName}.`);
    if (cloudModels.value.length === 0) ElMessage.info(`未找到服务商 ${providerName} 的可用模型列表。`);

  } catch (error) {
    console.error(`[ReportGeneratorView] Error fetching models for ${providerName}:`, error);
    ElMessage.error(`无法加载 ${providerName} 的模型列表: ${error.message}`);
    cloudModels.value = [];
  } finally {
    loadingCloudModels.value = false;
  }
};

// --- Report Generation Logic (kept in parent) ---
const handleGenerateReport = async () => {
  // Triggered by @generate-report event from ReportForm
  if (!topic.value.trim()) {
    ElMessage.warning('请输入研报主题！');
    return;
  }
  if (apiType.value === 'cloud' && !selectedCloudProvider.value) {
     ElMessage.warning('请选择云服务商！');
     return;
  }

  isLoading.value = true;
  reportContent.value = '';
  errorText.value = '';

  try {
    let response;
    if (apiType.value === 'ollama') {
      const payload = { topic: topic.value };
      if (selectedOllamaModel.value) {
        payload.model = selectedOllamaModel.value;
      }
      console.log("[ReportGeneratorView] Generating report (Ollama):", payload);
      response = await generateReportAPI(payload);
      reportContent.value = response.report_content;

    } else { // apiType === 'cloud'
      const payload = {
        topic: topic.value,
        provider: selectedCloudProvider.value, // Provider is now required
        model: selectedCloudModel.value || undefined // Pass model if selected, otherwise undefined (backend handles default)
      };
       console.log("[ReportGeneratorView] Generating report (Cloud):", payload);

      // 调用云端 API 函数
      response = await generateCloudReportAPI(payload);
      // 假设云端点也返回 { report_content: ... }
      reportContent.value = response.report_content;

    }

  } catch (err) {
    errorText.value = err.detail || err.message || '生成研报时发生未知错误。';
    console.error("[ReportGeneratorView] 研报生成失败:", err);
    reportContent.value = ''; // Clear content on error
  } finally {
    isLoading.value = false;
  }
};

// --- Lifecycle Hook ---
onMounted(() => {
  fetchOllamaModels();
  fetchCloudProviders();
});

</script>

<style scoped>
.report-generator-view {
  max-width: 800px;
  margin: 20px auto;
  padding: 20px;
}
/* Styles specific to the view layout can remain here */
</style> 