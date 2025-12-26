<template>
  <div class="api-status-check">
    <!-- 基本状态信息 -->
    <div class="status-section">
      <h4 class="section-title">{{ addEmoji('后端服务与配置状态', 'feature', 'service_status') }}</h4>
      <div class="status-grid">
        <div class="status-item">
          <span class="status-label">服务状态: </span>
          <el-tag :type="apiStatus.service_status === '运行中' ? 'success' : 'danger'" effect="light">{{ apiStatus.service_status || '未知' }}</el-tag>
        </div>
        <div class="status-item">
          <span class="status-label">文本分析器: </span>
          <el-tag :type="apiStatus.analyzer_status === '已初始化' ? 'success' : 'warning'" effect="light">{{ apiStatus.analyzer_status || '未知' }}</el-tag>
        </div>
        <div class="status-item">
          <span class="status-label">已配置提供商: </span>
          <div class="provider-tags">
            <template v-if="apiStatus.available_providers?.length > 0">
              <el-tag v-for="provider in apiStatus.available_providers" :key="provider" type="info" effect="light" class="provider-tag">{{ provider }}</el-tag>
            </template>
            <span v-else class="no-providers">无已配置的API提供商</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 提供商状态概览 -->
    <div class="provider-overview" v-if="showProviders">
      <div class="section-header">
        <h4 class="section-title">{{ addEmoji('API 提供商状态', 'feature', 'api_configured') }}</h4>
      </div>
      <el-row :gutter="20">
        <el-col :xs="24" :sm="12" :md="8" v-for="provider in providers" :key="provider.name">
          <el-card shadow="hover" :class="['provider-status-card', providerStatusClass(provider.status)]">
            <div class="card-header">
              <h4>{{ getProviderWithEmoji(provider) }}</h4>
              <div class="status-tag">
                <span class="status-emoji">{{ getStatusEmoji(provider.status) }}</span>
                <template v-if="provider.status?.direct_check">
                  <el-tag type="warning" size="small" effect="light">正在运行但未配置</el-tag>
                </template>
                <template v-else>
                  <el-tag :type="provider.status?.is_configured ? 'success' : 'danger'" size="small" effect="light">
                    {{ provider.status?.is_configured ? '已配置' : '未配置' }}
                  </el-tag>
                </template>
              </div>
            </div>
            <div class="provider-info">
              <p v-if="provider.name === defaultProvider" class="default-provider">
                <el-icon><Star /></el-icon> {{ addEmoji('默认提供商', 'menu', 'favourite') }}
              </p>
              <p v-if="provider.status?.status_message" class="status-message">
                {{ provider.status.status_message }}
              </p>
              <template v-if="provider.status?.direct_check">
                <el-button 
                  type="primary" 
                  size="small" 
                  @click="configureRunningProvider(provider.name)"
                  class="auto-config-btn"
                >
                  自动配置
                </el-button>
              </template>
            </div>
          </el-card>
        </el-col>
        <el-col :span="24" v-if="providers.length === 0" class="empty-container">
          <el-empty description="暂无API提供商" />
        </el-col>
      </el-row>
    </div>

    <el-divider />
    
    <!-- 环境配置检查 -->
    <div class="env-validation">
      <h4 class="section-title">环境配置检查:</h4>
      <div class="validation-summary">
        <span class="status-label">整体状态:</span>
        <el-tag :type="envValidation.valid ? 'success' : 'danger'" effect="light">{{ envValidation.valid ? '通过' : '失败' }}</el-tag>
      </div>
      
      <div v-if="envValidation.errors?.length > 0" class="validation-list">
        <div class="list-title">错误:</div>
        <ul class="error-list">
          <li v-for="(error, index) in envValidation.errors" :key="'err-'+index">
            <el-tag type="danger" size="small" effect="light">{{ error }}</el-tag>
          </li>
        </ul>
      </div>
      
      <div v-if="envValidation.warnings?.length > 0" class="validation-list">
        <div class="list-title">警告:</div>
        <ul class="warning-list">
          <li v-for="(warning, index) in envValidation.warnings" :key="'warn-'+index">
            <el-tag type="warning" size="small" effect="light">{{ warning }}</el-tag>
          </li>
        </ul>
      </div>
      
      <div class="action-buttons">
        <el-button @click="refreshStatus" :loading="loadingStatus">
          <el-icon class="el-icon--left"><Refresh /></el-icon>刷新状态
        </el-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed, defineProps, defineEmits } from 'vue';
import { ElMessage } from 'element-plus';
import { Refresh, Star } from '@element-plus/icons-vue';
import api from '../services/api';
import { getEmoji, addEmoji } from '../assets/emojiMap';
import apiProviderUtils from '../utils/apiProviderUtils';

const props = defineProps({
  showProviders: {
    type: Boolean,
    default: true
  }
});

const emit = defineEmits(['refresh-complete', 'update:defaultProvider']);

const loadingStatus = ref(false);
const providers = ref([]);
const defaultProvider = ref('');
const apiStatus = reactive({
  service_status: '检查中...',
  analyzer_status: '未知',
  available_providers: [],
  environment_validation: { valid: false, errors: [], warnings: [] }
});

// 重试次数跟踪
const retryCount = ref(0);
const maxRetries = 3;

// Computed property for easier access to validation results
const envValidation = computed(() => apiStatus.environment_validation || { valid: false, errors: [], warnings: [] });

// 获取状态Emoji
const getStatusEmoji = (status) => {
  if (!status) return getEmoji('feature', 'status-pending', '⚪');
  
  // 如果是直接检测到的Ollama（正在运行但未配置）
  if (status.direct_check && status.connection_test === 'success') {
    return getEmoji('feature', 'status-warning', '🟠');
  }
  
  if (status.is_configured) {
    if (status.connection_test === 'success') {
      return getEmoji('feature', 'status-ok', '🟢');
    } else if (status.connection_test === 'warning') {
      return getEmoji('feature', 'status-warning', '🟠');
    } else if (status.connection_test === 'error') {
      return getEmoji('feature', 'status-warning', '⚠️');
    }
    return getEmoji('feature', 'status-ok', '🟢');
  }
  
  if (status.status_message && status.status_message.includes('缺少')) {
    return getEmoji('feature', 'status-warning', '⚠️');
  }
  return getEmoji('feature', 'status-error', '🔴');
};

// 使用工具库中的函数
const getProviderWithEmoji = (provider) => {
  return apiProviderUtils.getProviderWithEmoji(provider);
};

// 根据状态返回CSS类
const providerStatusClass = (status) => {
  if (!status) return 'status-unknown';
  
  // 正在运行但未配置
  if (status.direct_check && status.connection_test === 'success') {
    return 'status-warning';
  }
  
  if (status.is_configured && status.connection_test !== 'error') return 'status-success';
  if (status.is_configured && status.connection_test === 'error') return 'status-warning';
  if (!status.is_configured) return 'status-danger';
  return 'status-unknown';
};

// 配置正在运行的提供商
const configureRunningProvider = async (providerName) => {
  if (providerName === 'ollama_local') {
    loadingStatus.value = true;
    try {
      // 查询提供商设置以获取当前配置
      const settingsResponse = await api.getProviderSettings();
      
      // 默认的Ollama配置
      const defaultConfig = {
        OLLAMA_API_BASE_URL: 'http://localhost:11434',
        OLLAMA_DEFAULT_MODEL: 'llama3',
      };
      
      // 合并现有设置（如果有）
      const existingConfig = settingsResponse.data && settingsResponse.data.ollama_local || {};
      const mergedConfig = { ...defaultConfig, ...existingConfig };
      
      // 确保API基础URL被设置为默认的Ollama端点
      mergedConfig.OLLAMA_API_BASE_URL = mergedConfig.OLLAMA_API_BASE_URL || 'http://localhost:11434';
      
      // 保存设置
      const saveData = {
        global_config: { DEFAULT_PROVIDER: defaultProvider.value || 'ollama_local' },
        provider_configs: {
          ollama_local: mergedConfig
        }
      };
      
      const saveResponse = await api.saveSettings(saveData);
      
      if (saveResponse.data && saveResponse.data.success) {
        ElMessage.success('Ollama 配置已自动设置');
        // 刷新状态
        await refreshStatus();
      } else {
        throw new Error('保存配置失败');
      }
    } catch (error) {
      console.error('自动配置Ollama失败:', error);
      ElMessage.error('自动配置Ollama失败：' + (error.message || '未知错误'));
    } finally {
      loadingStatus.value = false;
    }
  }
};

const refreshStatus = async (isRetry = false) => {
  if (!isRetry) {
    retryCount.value = 0; // 重置重试计数
  }
  
  loadingStatus.value = true;
  try {
    // 获取API状态
    const statusData = await api.getStatus();
    // Update reactive object properties individually
    apiStatus.service_status = statusData.data.service_status || '未知';
    apiStatus.analyzer_status = statusData.data.analyzer_status || '未知';
    apiStatus.available_providers = statusData.data.available_providers || [];
    apiStatus.environment_validation = statusData.data.environment_validation || { valid: false, errors: [], warnings: [] };
    
    // 获取提供商信息
    if (props.showProviders) {
      const providerResponse = await api.getProviders();
      if (providerResponse && providerResponse.data) {
        providers.value = Array.isArray(providerResponse.data) 
          ? providerResponse.data.filter(p => p && p.name)
          : [];
        
        // 确保至少有默认的提供商
        if (providers.value.length === 0) {
          providers.value = [
            { name: 'ollama_local', display_name: 'Ollama 本地' },
            { name: 'google_gemini', display_name: 'Google Gemini' }
          ];
        }
        
        // 获取每个提供商的状态
        const statusPromises = providers.value.map(async (provider) => {
          try {
            const statusResponse = await api.getProviderStatus(provider.name);
            provider.status = statusResponse.data || { 
              is_configured: false, 
              status_message: '未配置或状态未知' 
            };
          } catch (error) {
            console.error(`获取提供商 ${provider.name} 状态失败:`, error);
            provider.status = { 
              is_configured: false, 
              connection_test: 'error',
              status_message: error.friendlyMessage || '状态获取失败' 
            };
          }
        });
        
        try {
          await Promise.all(statusPromises);
        } catch (error) {
          console.error('部分提供商状态获取失败:', error);
        }
      }
      
      // 获取默认提供商
      try {
        const globalSettingsResponse = await api.getGlobalSettings();
        if (globalSettingsResponse && globalSettingsResponse.data) {
          defaultProvider.value = globalSettingsResponse.data.DEFAULT_PROVIDER || '';
          emit('update:defaultProvider', defaultProvider.value);
        }
      } catch (error) {
        console.error('获取默认提供商设置失败:', error);
        // 如果无法获取默认提供商，使用Ollama作为默认
        defaultProvider.value = 'ollama_local';
        emit('update:defaultProvider', defaultProvider.value);
      }
    }
    
    // 显示成功消息，但仅在非重试时
    if (!isRetry) {
      ElMessage.success('API 状态已刷新');
    }
    
    emit('refresh-complete', { 
      status: statusData.data,
      providers: providers.value,
      defaultProvider: defaultProvider.value
    });
  } catch (error) {
    console.error("获取API状态失败:", error);
    
    // 当后端服务未启动时，增加重试逻辑
    if (retryCount.value < maxRetries && !isRetry) {
      retryCount.value++;
      // 1秒后重试，避免过快请求
      setTimeout(() => {
        refreshStatus(true);
      }, 1000);
      return;
    }
    
    // 重置状态，显示错误
    apiStatus.service_status = '连接失败';
    apiStatus.analyzer_status = '未知';
    apiStatus.available_providers = [];
    apiStatus.environment_validation = { 
      valid: false, 
      errors: [error.friendlyMessage || '无法连接到服务器，请检查后端服务是否运行'], 
      warnings:[] 
    };
    
    // 保证页面有基本的提供商显示
    if (providers.value.length === 0) {
      providers.value = [
        { 
          name: 'ollama_local', 
          display_name: 'Ollama 本地',
          status: { 
            is_configured: false,
            connection_test: 'error',
            status_message: '后端服务连接失败' 
          }
        }
      ];
    }
    
    emit('refresh-complete', { error: true, message: error.message });
    
    if (!isRetry) {
      ElMessage.warning('无法连接到后端服务，显示离线状态');
    }
  } finally {
    loadingStatus.value = false;
  }
};

// 获取提供商数据
const getProviders = () => {
  return {
    providers: providers.value,
    defaultProvider: defaultProvider.value
  };
};

onMounted(() => {
  refreshStatus(); // Fetch status when component mounts
});

// 定义要暴露的方法
defineExpose({
  refreshStatus,
  getProviders
});
</script>

<style lang="scss">
.api-status-check {
  font-size: 0.95em;
  line-height: 1.8;
  color: var(--light-text-primary);
  
  .section-title {
    color: var(--light-text-primary);
    font-weight: 600;
    margin-bottom: 16px;
    position: relative;
    padding-bottom: 8px;
    
    &:after {
      content: '';
      position: absolute;
      bottom: 0;
      left: 0;
      width: 40px;
      height: 3px;
      background: var(--light-accent-primary);
      border-radius: 2px;
    }
  }
  
  .status-section {
    margin-bottom: 24px;
    
    .status-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
      gap: 16px;
      
      .status-item {
        display: flex;
        align-items: center;
        
        .status-label {
          font-weight: 500;
          min-width: 100px;
          margin-right: 8px;
        }
        
        .provider-tags {
          display: flex;
          flex-wrap: wrap;
          gap: 6px;
          
          .provider-tag {
            transition: all 0.2s ease;
            
            &:hover {
              transform: translateY(-2px);
              box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
            }
          }
          
          .no-providers {
            color: var(--light-text-secondary);
            font-style: italic;
          }
        }
      }
    }
  }
  
  .provider-overview {
    margin-bottom: 28px;
    
    .section-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
    }
    
    .provider-status-card {
      margin-bottom: 16px;
      transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
      
      &:hover {
        transform: translateY(-5px);
      }
      
      &.status-success {
        border-left: 4px solid var(--light-accent-primary);
        
        .card-header {
          background: linear-gradient(to right, rgba(240, 249, 235, 0.4), transparent);
        }
      }
      
      &.status-warning {
        border-left: 4px solid #e6a23c;
        
        .card-header {
          background: linear-gradient(to right, rgba(253, 246, 236, 0.4), transparent);
        }
      }
      
      &.status-danger {
        border-left: 4px solid #f56c6c;
        
        .card-header {
          background: linear-gradient(to right, rgba(254, 240, 240, 0.4), transparent);
        }
      }
      
      &.status-unknown {
        border-left: 4px solid #909399;
        
        .card-header {
          background: linear-gradient(to right, rgba(244, 244, 245, 0.4), transparent);
        }
      }
      
      .card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding-bottom: 8px;
        margin-bottom: 10px;
        border-bottom: 1px dashed rgba(0, 0, 0, 0.05);
        
        h4 {
          margin: 0;
          font-weight: 500;
        }
        
        .status-tag {
          display: flex;
          align-items: center;
          gap: 6px;
          
          .status-emoji {
            font-size: 1.1em;
          }
        }
      }
      
      .provider-info {
        font-size: 0.9em;
        color: var(--light-text-secondary);
        
        .default-provider {
          display: flex;
          align-items: center;
          color: #e6a23c;
          font-weight: 500;
          
          .el-icon {
            margin-right: 5px;
          }
        }
        
        .status-message {
          margin: 8px 0;
          line-height: 1.4;
        }
        
        .auto-config-btn {
          margin-top: 8px;
          transition: all 0.3s ease;
          
          &:hover {
            transform: scale(1.05);
          }
        }
      }
    }
    
    .empty-container {
      padding: 20px;
      background-color: rgba(0, 0, 0, 0.02);
      border-radius: 8px;
    }
  }
  
  .env-validation {
    padding: 16px;
    background-color: rgba(255, 255, 255, 0.5);
    backdrop-filter: blur(5px);
    border-radius: 12px;
    box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
    
    .validation-summary {
      display: flex;
      align-items: center;
      margin-bottom: 16px;
      
      .status-label {
        font-weight: 500;
        margin-right: 8px;
      }
    }
    
    .validation-list {
      margin-bottom: 16px;
      
      .list-title {
        font-weight: 500;
        margin-bottom: 8px;
      }
      
      ul {
        list-style-type: none;
        padding-left: 0;
        margin-bottom: 16px;
        
        li {
          margin-bottom: 8px;
          
          .el-tag {
            padding: 6px 10px;
            font-size: 0.9em;
          }
        }
      }
      
      .error-list li .el-tag {
        background-color: rgba(245, 108, 108, 0.1);
      }
      
      .warning-list li .el-tag {
        background-color: rgba(230, 162, 60, 0.1);
      }
    }
    
    .action-buttons {
      display: flex;
      justify-content: flex-end;
      margin-top: 16px;
    }
  }
  
  // 深色模式支持
  html.dark & {
    color: var(--dark-text-primary);
    
    .section-title {
      color: var(--dark-text-primary);
      
      &:after {
        background: var(--dark-accent-primary);
      }
    }
    
    .status-section {
      .status-item {
        .status-label {
          color: var(--dark-text-primary);
        }
        
        .provider-tags {
          .no-providers {
            color: var(--dark-text-secondary);
          }
        }
      }
    }
    
    .provider-status-card {
      &.status-success {
        border-left-color: var(--dark-accent-primary);
        
        .card-header {
          background: linear-gradient(to right, rgba(66, 185, 131, 0.1), transparent);
        }
      }
      
      &.status-warning {
        .card-header {
          background: linear-gradient(to right, rgba(230, 162, 60, 0.1), transparent);
        }
      }
      
      &.status-danger {
        .card-header {
          background: linear-gradient(to right, rgba(245, 108, 108, 0.1), transparent);
        }
      }
      
      .card-header {
        border-bottom-color: rgba(255, 255, 255, 0.05);
      }
      
      .provider-info {
        color: var(--dark-text-secondary);
      }
    }
    
    .empty-container {
      background-color: rgba(255, 255, 255, 0.02);
    }
    
    .env-validation {
      background-color: rgba(10, 10, 10, 0.5);
      box-shadow: 0 2px 12px rgba(0, 0, 0, 0.15);
      
      .validation-list {
        .error-list li .el-tag {
          background-color: rgba(245, 108, 108, 0.1);
        }
        
        .warning-list li .el-tag {
          background-color: rgba(230, 162, 60, 0.1);
        }
      }
    }
  }
}
</style> 