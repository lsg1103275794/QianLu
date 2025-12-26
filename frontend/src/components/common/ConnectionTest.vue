<template>
  <el-card class="test-card" shadow="hover">
    <template #header>
      <div class="card-header">
        <span class="header-title">{{ addEmoji('基础连接测试', 'menu', 'api-manager') }}</span>
      </div>
    </template>
    <el-form label-position="top" size="small">
      <el-row :gutter="15">
        <el-col :span="8">
          <el-form-item label="选择服务商" class="compact-form-item">
            <el-select 
              :model-value="selectedProvider" 
              @update:modelValue="handleProviderUpdate"
              placeholder="请选择API服务商" 
              style="width: 100%"
            >
              <el-option 
                v-for="provider in availableProviders" 
                :key="provider.name" 
                :label="addEmoji(provider.display_name || provider.name, 'provider', provider.name)"
                :value="provider.name" 
              />
            </el-select>
            <el-button 
              type="primary" 
              size="small" 
              plain 
              @click="refreshProvider" 
              :icon="Refresh"
            >
              {{ getEmoji('menu', 'refresh') }} 刷新
            </el-button>
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="选择模型" class="compact-form-item">
            <el-select
              :model-value="selectedModel"
              @update:modelValue="handleModelUpdate"
              placeholder="选择模型"
              :loading="loadingModels"
              :disabled="loadingModels || !selectedProvider || !availableModels.length"
              style="width: 100%"
            >
              <template #empty>
                <div class="text-muted">
                  <div v-if="loadingModels">
                    <el-icon class="is-loading"><Loading /></el-icon> 正在加载模型列表...
                  </div>
                  <div v-else-if="!selectedProvider">
                    请先选择服务商
                  </div>
                  <div v-else-if="modelLoadError">
                    {{ modelLoadError }}
                  </div>
                  <div v-else>
                    未找到可用模型
                  </div>
                </div>
              </template>
              <el-option
                v-for="model in availableModels"
                :key="typeof model === 'object' ? (model.id || model.name) : model"
                :label="typeof model === 'object' ? (model.name || model.id) : model"
                :value="typeof model === 'object' ? (model.id || model.name) : model"
              />
            </el-select>
            <div class="text-muted mt-5" v-if="modelLoadError && availableModels.length > 0">
              {{ modelLoadError }} <br> 已加载默认/缓存模型
            </div>
            <el-button 
              type="primary" 
              size="small" 
              plain 
              @click="refreshModel" 
              :icon="Refresh"
            >
              {{ getEmoji('menu', 'refresh') }} 刷新
            </el-button>
          </el-form-item>
        </el-col>
        <el-col :span="8">
          <el-form-item label="测试提示词" class="compact-form-item">
            <el-input v-model="testPrompt" placeholder="输入简短的测试提示词" />
          </el-form-item>
        </el-col>
      </el-row>
      
      <!-- Moved Button Below Model Selection -->
      <el-form-item class="test-btn-container">
        <el-button 
          :type="testing ? 'primary' : (testResult && testResult.status === 'success' && testResult.response && testResult.response.includes('收到')) ? 'success' : (testResult && testResult.status === 'error') ? 'danger' : 'primary'"
          @click="runTest" 
          :loading="testing"
          size="small"
        >
          {{ addEmoji('测试连接', 'menu', 'api-manager') }}
        </el-button>
      </el-form-item>

      <!-- Loading and Empty States -->
      <div v-if="testing" class="test-loading">
        <el-icon class="is-loading"><Loading /></el-icon>
        <span>{{ addEmoji('正在测试中...', 'menu', 'loading') }}</span>
      </div>
      <div v-else-if="!testResult && !testing" class="test-empty">
        <el-empty description="点击测试按钮开始连接测试" :image-size="36">
           <template #image>
             <span class="test-empty-icon">{{ getEmoji('provider', 'default') }}</span>
           </template>
        </el-empty>
      </div>
    </el-form>

    <!-- Test Result Display -->
    <div v-if="testResult" class="test-result">
      <el-alert
        :title="testResult.status === 'success' ? `${getEmoji('feature', 'api_configured')} 测试成功` : `${getEmoji('feature', 'api_error')} 测试失败`"
        :type="testResult.status === 'success' ? 'success' : 'error'"
        :description="testResult.message"  
        show-icon
        closable
        @close="testResult = null"
        class="result-alert"
      />
      <!-- 仅在成功时显示响应文本 -->
      <div v-if="testResult.status === 'success' && testResult.response" class="response-container" :class="{ 'dark-mode': isDarkMode }">
        <div class="response-header">
          <span>{{ addEmoji('模型响应', 'menu', 'model-test') }}</span>
          <el-button 
            type="primary" 
            size="small" 
            plain 
            @click="copyTestResponse" 
            :icon="CopyDocument"
          >
            {{ getEmoji('menu', 'copy') }} 复制
          </el-button>
        </div>
        <!-- 直接显示简洁的响应文本 -->
        <div class="response-text">
          {{ testResult.response }}
        </div>
      </div>
      <!-- 在失败时显示错误详情 -->
      <div v-else-if="testResult.status === 'error' && testResult.error" class="error-details-container">
         <div class="response-header">
           <span>{{ addEmoji('错误详情', 'menu', 'error') }}</span>
         </div>
         <pre class="error-details">{{ testResult.error }}</pre>
      </div>
    </div>
  </el-card>
</template>

<script setup>
import { ref } from 'vue';
import { ElMessage, ElSelect, ElOption, ElInput, ElButton, ElCard, ElForm, ElFormItem, ElRow, ElCol, ElAlert, ElIcon, ElEmpty } from 'element-plus';
import api from '../../services/api'; // Corrected path
import { getEmoji, addEmoji } from '../../assets/emojiMap'; // Corrected path
import { CopyDocument, Loading, Refresh } from '@element-plus/icons-vue';

const props = defineProps({
  availableProviders: { type: Array, default: () => [] },
  selectedProvider: { type: String, default: '' },
  availableModels: { type: Array, default: () => [] },
  selectedModel: { type: String, default: '' },
  loadingModels: { type: Boolean, default: false },
  modelLoadError: { type: String, default: '' },
  isDarkMode: { type: Boolean, default: false } // Receive dark mode status
});

const emit = defineEmits(['update:selectedProvider', 'update:selectedModel', 'fetch-models']);

const testPrompt = ref('你好，这是一个测试。请用一句话回复确认你收到了消息。');
const testing = ref(false);
const testResult = ref(null); // { status: 'success' | 'error', message?: string, response?: string, error?: string }

// Handle provider update event from select
const handleProviderUpdate = (value) => {
  emit('update:selectedProvider', value);
  emit('fetch-models', value); // Tell parent to fetch models
};

// Handle model update event from select
const handleModelUpdate = (value) => {
  emit('update:selectedModel', value);
};

// 运行测试 (使用专用测试接口 /provider/test-model)
const runTest = async () => {
  if (!props.selectedProvider || !props.selectedModel) {
    ElMessage.warning('请先选择服务商和模型');
    return;
  }
  testing.value = true;
  testResult.value = null; // 清除之前结果

  const payload = {
    provider: props.selectedProvider,
    model: props.selectedModel,
    // prompt 不再由前端发送，由后端决定
    // prompt: testPrompt.value || "你好，请确认你能收到消息并简单回复。",
  };

  console.log("ConnectionTest: 发送测试连接请求 (调用 /provider/test-model)");

  try {
    // 使用专用测试模型接口
    const response = await api.testModelConnection(payload);
    console.log("ConnectionTest: 测试连接响应:", response);

    // 处理测试接口响应
    if (response && response.data) {
      // 直接使用后端返回的 status 和 message
      const status = response.data.status === 'success' ? 'success' : 'error';
      const message = response.data.message || (status === 'success' ? '测试成功' : '测试失败');
      const responseText = response.data.response || ''; // 获取简洁响应
      const errorDetails = response.data.error_details || '';

      testResult.value = {
        status,
        message: message, // 使用后端提供的消息
        response: responseText, // 存储简洁响应文本
        error: errorDetails || (status === 'error' ? message : null) // 错误时显示后端消息或详情
      };
      
      // 成功或失败都显示提示
      if (status === 'success') {
           ElMessage.success(message);
      } else {
           ElMessage.error(errorDetails ? `${message}: ${errorDetails}` : message);
      }

    } else {
      throw new Error('服务器返回了无效的响应格式');
    }
  } catch (error) {
    console.error("ConnectionTest: 测试连接失败:", error);
    // 提取更详细的错误信息
    let errMsg = '测试失败，请检查网络连接和API配置';
    if (error.response && error.response.data) {
      errMsg = `测试失败: ${error.response.data.message || error.response.data.detail || JSON.stringify(error.response.data)}`;
    } else if (error.message) {
      errMsg = `测试失败: ${error.message}`;
    }
    testResult.value = {
      status: 'error',
      error: errMsg,
      response: null,
      message: '连接测试异常'
    };
     ElMessage.error(errMsg);
  } finally {
    testing.value = false;
  }
};

// 复制测试响应内容 (现在复制简洁文本)
const copyTestResponse = () => {
  // 直接从 testResult.response 复制简洁文本
  if (!testResult.value || testResult.value.status !== 'success' || !testResult.value.response) {
    ElMessage.warning('没有可复制的成功响应内容');
    return;
  }
  
  const textToCopy = testResult.value.response;

  navigator.clipboard.writeText(textToCopy)
    .then(() => {
      ElMessage.success('响应内容已复制');
    })
    .catch(err => {
      console.error('复制失败:', err);
      ElMessage.error('复制失败');
    });
};

// 刷新 provider 选项
const refreshProvider = () => {
  // Implementation of refreshProvider
};

// 刷新 model 选项
const refreshModel = () => {
  // Implementation of refreshModel
};

</script>

<style lang="scss" scoped>
.test-card {
  margin-bottom: 15px;
  border-radius: 6px;
  transition: all 0.3s;
  width: 100%;
  
  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 16px;
    font-weight: 600;
    
    .header-title {
      display: flex;
      align-items: center;
      font-size: 15px;
    }
  }
}

.compact-form-item {
  margin-bottom: 10px;
}

.test-btn-container {
  margin-bottom: 10px;
  margin-top: 0;
}

.text-muted {
  font-size: 12px;
  color: #909399;
  &.mt-5 {
    margin-top: 5px;
  }
}

.test-loading, .test-empty {
  padding: 12px;
  text-align: center;
  color: #909399;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 60px;
  
  .el-icon {
    margin-right: 5px;
  }
}

.test-empty {
  color: #C0C4CC;
  
  .test-empty-icon {
    font-size: 24px;
    display: flex;
    justify-content: center;
    margin-bottom: 8px;
  }
}

.test-result {
  margin-top: 15px;
  
  .result-alert {
    margin-bottom: 15px;
  }
  
  .response-container, .error-details-container {
    padding: 12px;
    border-radius: 4px;
    background-color: #f5f7fa;
    border: 1px solid #e4e7ed;
    font-size: 14px;
    
    &.dark-mode {
      background-color: #1e1e1e;
      border-color: #333;
    }
    
    .response-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 10px;
      padding-bottom: 5px;
      border-bottom: 1px solid #ebeef5;
      
      span {
        font-weight: 600;
        font-size: 14px;
      }
    }
    
    .response-text {
      white-space: pre-wrap;
      line-height: 1.5;
      font-size: 13px;
    }
  }
  
  .error-details-container {
    background-color: #fef0f0;
    border-color: #fab6b6;
    
    pre.error-details {
      white-space: pre-wrap;
      margin: 0;
      padding: 8px;
      background-color: rgba(255, 255, 255, 0.5);
      border-radius: 3px;
      font-family: monospace;
      font-size: 12px;
      line-height: 1.4;
      max-height: 200px;
      overflow-y: auto;
    }
    
    &.dark-mode {
      background-color: #2d2020;
      border-color: #5c3636;
      
      pre.error-details {
        background-color: rgba(0, 0, 0, 0.2);
      }
    }
  }
}
</style> 