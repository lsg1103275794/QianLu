<template>
  <div class="model-test">
    <el-row :gutter="15">
      <el-col :span="24">
        <h2 class="page-title">模型连通性与聊天测试</h2>
      </el-col>
    </el-row>

    <el-row :gutter="15">
      <el-col :span="24">
        <ConnectionTest 
          v-model:selectedProvider="selectedProvider" 
          v-model:selectedModel="selectedModel"
          :available-providers="availableProviders"
          :available-models="availableModels"
          :loading-models="loadingModels"
          :model-load-error="modelLoadError"
          :is-dark-mode="isDarkMode"
          @fetch-models="handleProviderChange" 
          @update:selectedModel="handleModelChange"
        />
      </el-col>
    </el-row>

    <el-row :gutter="15" class="mt-15">
      <el-col :span="24">
        <ChatTest 
          ref="chatTestRef"
          :selected-provider="selectedProvider" 
          :selected-model="selectedModel"
          :is-dark-mode="isDarkMode"
          @update-chat-context="handleChatContextUpdate"
          @chat-ready="handleChatReady"
          @chat-state-change="handleChatStateChange"
        />
      </el-col>
    </el-row>
    
    <div class="global-actions">
      <el-tooltip content="切换深色/浅色模式" placement="top">
        <el-switch 
          v-model="isDarkMode"
          active-text="深色"
          inactive-text="浅色" 
          @change="toggleDarkMode" 
        />
      </el-tooltip>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue';
import { ElMessage, ElRow, ElCol, ElSwitch, ElTooltip } from 'element-plus';
// Corrected Import Paths
import ConnectionTest from '../components/common/ConnectionTest.vue'; // Updated path
import ChatTest from '../components/chat/ChatTest.vue'; // Updated path
import api from '../services/api'; // Assuming api.js is in services
import axios from 'axios';

const availableProviders = ref([]);
const selectedProvider = ref('');
const availableModels = ref([]);
const selectedModel = ref('');
const loadingModels = ref(false);
const modelLoadError = ref('');
const isDarkMode = ref(localStorage.getItem('darkMode') === 'true');

// Fallback client setup... (rest of the script content from ModelTest.vue)
const fallbackClient = axios.create({
  baseURL: 'http://127.0.0.1:8001/api',
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' }
});

const fetchProviders = async () => {
  console.log("ModelTestView: fetchProviders started..."); // Updated log prefix
  try {
    let response;
    try {
      response = await api.getProviders();
      console.log("ModelTestView: api.getProviders response:", response);
    } catch (primaryError) {
      console.error("ModelTestView: Primary provider fetch failed, trying fallback:", primaryError);
      try {
        response = await fallbackClient.get('/provider-status');
        console.log("ModelTestView: Fallback provider fetch response:", response);
        if (response && response.data && typeof response.data === 'object' && !Array.isArray(response.data)) {
           const providers = Object.keys(response.data).map(key => ({ name: key, display_name: key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase()) }));
            response.data = providers;
        }
      } catch (fallbackError) {
         console.error("ModelTestView: Fallback provider fetch also failed:", fallbackError);
         throw fallbackError;
      }
    }
    
    const providersData = Array.isArray(response?.data) ? response.data : [];
    availableProviders.value = providersData.slice();
    console.log("ModelTestView: Updated availableProviders:", availableProviders.value);
    
    if (availableProviders.value.length === 0) {
      console.warn("ModelTestView: No providers fetched, using defaults.");
      setDefaultProviders();
    }
    
    if (availableProviders.value.length > 0 && !selectedProvider.value) {
        selectedProvider.value = availableProviders.value[0].name;
        handleProviderChange(selectedProvider.value);
    }

  } catch (error) {
    console.error("ModelTestView: Failed to fetch providers:", error);
    setDefaultProviders();
    ElMessage.error({ message: '获取服务商列表失败，已使用默认列表', duration: 5000 });
  }
};

const setDefaultProviders = () => {
    availableProviders.value = [
      { name: 'ollama_local', display_name: 'Ollama 本地' },
      { name: 'google_gemini', display_name: 'Google Gemini' },
    ];
     if (!selectedProvider.value && availableProviders.value.length > 0) {
         selectedProvider.value = availableProviders.value[0].name;
         handleProviderChange(selectedProvider.value);
     }
};

const chatTestRef = ref(null);

const handleChatReady = () => {
  console.log("ModelTestView: ChatTest组件已就绪");
};

const handleChatStateChange = (state) => {
  console.log("ModelTestView: ChatTest状态变化:", state);
};

const handleProviderChange = async (providerName, savedModel = null) => {
  if (!providerName) return;
  console.log(`ModelTestView: Provider changed to: ${providerName}, fetching models...`);
  loadingModels.value = true;
  availableModels.value = [];
  modelLoadError.value = '';
  selectedModel.value = '';
  
  if (chatTestRef.value) {
    chatTestRef.value.resetChatInterface();
  }
  
  try {
    const response = await api.getModels(providerName);
    console.log(`ModelTestView: Models API response for ${providerName}:`, response);
    
    let modelsList = [];
    if (response.data && Array.isArray(response.data)) {
      // 直接是数组，检查元素类型
      if (response.data.length > 0 && typeof response.data[0] === 'object') {
        // 数组元素是对象，提取name字段
        modelsList = response.data.map(model => model.name || model.id || model).sort();
        console.log(`ModelTestView: 将模型对象数组转换为名称数组:`, modelsList);
      } else {
        // 数组元素是字符串或其他基本类型
        modelsList = response.data.sort();
      }
    } else if (response.data && typeof response.data === 'object') {
      if (response.data.status === 'error' && response.data.error) {
        modelLoadError.value = `API配置错误: ${response.data.error}`;
      } else if (response.data.models && Array.isArray(response.data.models)) {
        // 检查models数组中元素的类型
        if (response.data.models.length > 0 && typeof response.data.models[0] === 'object') {
          // 元素是对象，提取name字段
          modelsList = response.data.models.map(model => model.name || model.id || model).sort();
          console.log(`ModelTestView: 将models字段中的对象数组转换为名称数组:`, modelsList);
        } else {
          // 元素是字符串或其他基本类型
          modelsList = response.data.models.sort();
        }
      } else {
        const possibleModels = extractModelsFromObject(response.data);
        if (possibleModels.length > 0) {
          // 检查提取出的模型是否是对象
          if (typeof possibleModels[0] === 'object') {
            modelsList = possibleModels.map(model => model.name || model.id || model).sort();
            console.log(`ModelTestView: 将提取的模型对象转换为名称数组:`, modelsList);
          } else {
            modelsList = possibleModels.sort();
          }
        }
      }
    }
    
    availableModels.value = modelsList;

    if (availableModels.value.length > 0) {
      if (savedModel && availableModels.value.includes(savedModel)) {
          selectedModel.value = savedModel;
          console.log(`ModelTestView: Restored selected model from saved state: ${selectedModel.value}`);
      } else if (!selectedModel.value) {
          selectedModel.value = availableModels.value[0];
          console.log(`ModelTestView: Set default selected model: ${selectedModel.value}`);
      }
    } else {
       console.warn(`ModelTestView: ${providerName} returned no models.`);
       setDefaultModelsForProvider(providerName);
    }

  } catch (error) {
    console.error(`ModelTestView: Error loading models for ${providerName}:`, error);
    let errorMsg = `无法加载模型列表 - ${error.message}`;
    if (error.response) {
      const status = error.response.status;
        const detail = error.response.data?.detail || error.response.data?.error || error.message;
        errorMsg = status === 404 ? `提供商未配置` : `服务器错误: ${detail}`;
     } 
    modelLoadError.value = errorMsg;
    setDefaultModelsForProvider(providerName);
    ElMessage.warning({ message: `模型列表加载失败 (${errorMsg})，已使用默认模型`, duration: 5000 });
  } finally {
    loadingModels.value = false;
  }
};

const handleModelChange = (modelName) => {
  if (modelName) {
    selectedModel.value = modelName;
    console.log(`ModelTestView: Selected model changed: ${modelName}`);
    
    if (chatTestRef.value) {
      chatTestRef.value.resetChatInterface();
    }
  }
};

const setDefaultModelsForProvider = (providerName) => {
  if (providerName === 'ollama_local') {
        availableModels.value = ['llama2', 'gemma:2b'];
  } else {
    availableModels.value = ['default-model'];
    }
    if (availableModels.value.length > 0 && !selectedModel.value) {
        selectedModel.value = availableModels.value[0];
    }
    console.warn(`ModelTestView: Set default models for ${providerName}:`, availableModels.value);
};

const extractModelsFromObject = (data) => {
   const possibleFieldNames = ['models', 'model_list'];
   // 尝试从known字段获取模型列表
   for (const field of possibleFieldNames) {
     if (data[field] && Array.isArray(data[field])) {
       console.log(`ModelTestView: Found models in field '${field}'`, data[field]);
       return data[field]; 
     }
   }
   
   // 尝试寻找任何看起来像模型列表的数组
   for (const key in data) {
     if (Array.isArray(data[key])) {
       // 如果数组的第一个元素是字符串，或者是有id/name属性的对象
       if (data[key].length > 0) {
         if (typeof data[key][0] === 'string') {
           console.log(`ModelTestView: Found string array in field '${key}'`, data[key]);
           return data[key];
         } else if (typeof data[key][0] === 'object' && 
                  (data[key][0].id !== undefined || data[key][0].name !== undefined)) {
           console.log(`ModelTestView: Found model objects in field '${key}'`, data[key]);
           return data[key];
         }
       }
     }
   }
   return [];
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

const handleChatContextUpdate = (context) => {
  console.log("ModelTestView: Received chat context update:", context);
  if (context.provider && availableProviders.value.some(p => p.name === context.provider)) {
      selectedProvider.value = context.provider;
      handleProviderChange(context.provider).then(() => {
          if (context.model && availableModels.value.includes(context.model)) {
              selectedModel.value = context.model;
          }
      });
  } else if (context.provider) {
      console.warn(`ModelTestView: Provider '${context.provider}' from chat history not found in available providers.`);
  }
};

onMounted(async () => {
  console.log("ModelTestView component mounted");
  await fetchProviders();
  console.log("Initial model loading (if any) complete.");
});

watch(selectedModel, (newModel, oldModel) => {
    if (newModel !== oldModel) {
        console.log(`ModelTestView: selectedModel changed via watch: ${newModel}`);
    }
});

watch(selectedProvider, (newProvider, oldProvider) => {
    if (newProvider !== oldProvider) {
        console.log(`ModelTestView: selectedProvider changed via watch: ${newProvider}`);
    }
});

</script>

<style lang="scss" scoped>
.model-test {
  padding: 10px;
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
  
  .page-title {
    font-size: 20px;
    margin-top: 0;
    margin-bottom: 15px;
    font-weight: 600;
  }
  
  .mt-15 {
    margin-top: 15px;
  }
  
  .global-actions {
    position: fixed;
    bottom: 20px;
    right: 20px;
    background: rgba(255, 255, 255, 0.8);
    padding: 8px;
    border-radius: 4px;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
    z-index: 100;
  }
  
  :deep(.el-card) {
    margin-bottom: 15px;
    width: 100%;
  }
  
  :deep(.el-form-item) {
    margin-bottom: 15px;
  }
}

html.dark .model-test {
  .global-actions {
    background: rgba(0, 0, 0, 0.6);
  }
}
</style> 