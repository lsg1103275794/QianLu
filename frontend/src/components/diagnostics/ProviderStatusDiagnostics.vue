<template>
  <div class="provider-status-diagnostics">
    <div class="header">
      <h2>API提供商状态诊断</h2>
      <el-button 
        type="primary" 
        circle 
        @click="refreshAllProviders"
        :loading="refreshing"
      >
        <el-icon><Refresh /></el-icon>
      </el-button>
    </div>

    <el-table
      :data="providerStatusList"
      style="width: 100%"
      :empty-text="emptyText"
      v-loading="loading"
    >
      <el-table-column prop="name" label="提供商">
        <template #default="scope">
          <div class="provider-name">
            <span v-html="getProviderNameWithEmoji(scope.row.name)"></span>
          </div>
        </template>
      </el-table-column>

      <el-table-column prop="status" label="状态" width="120">
        <template #default="scope">
          <el-tag :type="getStatusType(scope.row.status)" size="small">
            {{ getStatusText(scope.row.status) }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column prop="default_model" label="默认模型">
        <template #default="scope">
          {{ scope.row.default_model || '未设置' }}
        </template>
      </el-table-column>

      <el-table-column prop="response_time" label="响应时间" width="120">
        <template #default="scope">
          <span v-if="scope.row.response_time !== undefined && scope.row.status === 'connected'">
            {{ scope.row.response_time }}ms
          </span>
          <span v-else>-</span>
        </template>
      </el-table-column>

      <el-table-column prop="last_tested" label="最后测试时间" width="180">
        <template #default="scope">
          <span v-if="scope.row.last_tested">
            {{ formatDate(scope.row.last_tested) }}
          </span>
          <span v-else>未测试</span>
        </template>
      </el-table-column>

      <el-table-column label="操作" width="200">
        <template #default="scope">
          <el-button
            type="primary"
            size="small"
            @click="testConnection(scope.row.name)"
            :loading="testingProvider === scope.row.name"
          >
            测试连接
          </el-button>
          <el-button
            type="info"
            size="small"
            @click="showDetails(scope.row)"
          >
            详情
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 提供商详情对话框 -->
    <el-dialog
      v-model="detailsVisible"
      title="API提供商详情"
      width="60%"
      destroy-on-close
    >
      <div class="provider-details" v-if="selectedProvider">
        <el-descriptions :column="1" border>
          <el-descriptions-item label="提供商名称">
            <span v-html="getProviderNameWithEmoji(selectedProvider.name)"></span>
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusType(selectedProvider.status)">
              {{ getStatusText(selectedProvider.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="默认模型">
            {{ selectedProvider.default_model || '未设置' }}
          </el-descriptions-item>
          <el-descriptions-item label="最后测试时间">
            {{ selectedProvider.last_tested ? formatDate(selectedProvider.last_tested) : '未测试' }}
          </el-descriptions-item>
          <el-descriptions-item label="响应时间">
            {{ selectedProvider.response_time !== undefined && selectedProvider.status === 'connected' ? `${selectedProvider.response_time}ms` : '-' }}
          </el-descriptions-item>
          
          <el-descriptions-item label="可用模型">
            <div v-if="selectedProvider.available_models && selectedProvider.available_models.length">
              <el-tag 
                v-for="model in selectedProvider.available_models" 
                :key="model" 
                size="small"
                style="margin-right: 4px; margin-bottom: 4px;"
              >
                {{ model }}
              </el-tag>
            </div>
            <div v-else>未获取到可用模型</div>
          </el-descriptions-item>
          
          <el-descriptions-item label="配置信息">
            <div v-if="selectedProvider.config">
              <div v-for="(value, key) in filterSensitiveConfigInfo(selectedProvider.config)" :key="key" class="config-item">
                <strong>{{ key }}:</strong> 
                <span v-if="isSensitiveKey(key)">********</span>
                <span v-else>{{ value }}</span>
              </div>
            </div>
            <div v-else>无配置信息</div>
          </el-descriptions-item>
          
          <el-descriptions-item v-if="selectedProvider.error" label="错误信息">
            <div class="error-message">{{ selectedProvider.error }}</div>
          </el-descriptions-item>
        </el-descriptions>
        
        <div class="actions">
          <el-button
            type="primary"
            @click="testConnection(selectedProvider.name)"
            :loading="testingProvider === selectedProvider.name"
          >
            测试连接
          </el-button>
          <el-button
            type="success"
            @click="setDefaultProvider(selectedProvider.name)"
            :disabled="selectedProvider.status !== 'connected'"
          >
            设为默认
          </el-button>
          <el-button
            type="warning"
            @click="showTroubleshootingDialog = true"
            v-if="selectedProvider.status !== 'connected'"
          >
            故障排除
          </el-button>
        </div>
      </div>
    </el-dialog>

    <!-- 故障排除对话框 -->
    <el-dialog
      v-model="showTroubleshootingDialog"
      title="API提供商故障排除"
      width="70%"
      destroy-on-close
    >
      <div class="troubleshooting-guide" v-if="selectedProvider">
        <h3>{{ selectedProvider.name }} 连接故障排除指南</h3>
        
        <el-divider />
        
        <el-collapse accordion>
          <el-collapse-item title="1. 检查API密钥配置" name="1">
            <div class="troubleshooting-item">
              <p>确保API密钥和配置信息正确：</p>
              <ul>
                <li>API密钥是否正确输入，没有多余的空格</li>
                <li>API密钥是否有效且未过期</li>
                <li>账户额度是否充足</li>
              </ul>
              <p>您可以在API提供商的网站上检查密钥的有效性：</p>
              <div class="troubleshooting-links" v-if="getLinkForProvider(selectedProvider.name)">
                <a :href="getLinkForProvider(selectedProvider.name)" target="_blank">访问 {{ selectedProvider.name }} 官方网站</a>
              </div>
            </div>
          </el-collapse-item>
          
          <el-collapse-item title="2. 检查网络连接" name="2">
            <div class="troubleshooting-item">
              <p>确保您的网络可以连接到该API提供商的服务器：</p>
              <ul>
                <li>检查网络连接是否稳定</li>
                <li>如果使用代理或VPN，请确保配置正确</li>
                <li>检查防火墙是否阻止了API调用</li>
              </ul>
            </div>
          </el-collapse-item>
          
          <el-collapse-item title="3. 检查API地址配置" name="3">
            <div class="troubleshooting-item">
              <p>对于自定义API端点，请确保服务器地址配置正确：</p>
              <ul>
                <li>确保API基础URL正确，包括协议(http/https)和端口号</li>
                <li>对于本地服务如Ollama，请确保服务已经启动并监听在配置的端口上</li>
              </ul>
            </div>
          </el-collapse-item>
          
          <el-collapse-item title="4. 检查API提供商服务状态" name="4">
            <div class="troubleshooting-item">
              <p>确认API提供商的服务当前是否可用：</p>
              <ul>
                <li>访问提供商的状态页面，查看是否有已知的服务中断</li>
                <li>检查社交媒体或开发论坛，了解是否有其他用户报告类似问题</li>
              </ul>
              <div class="troubleshooting-links" v-if="getStatusPageForProvider(selectedProvider.name)">
                <a :href="getStatusPageForProvider(selectedProvider.name)" target="_blank">
                  查看 {{ selectedProvider.name }} 服务状态页面
                </a>
              </div>
            </div>
          </el-collapse-item>
          
          <el-collapse-item title="5. 高级诊断" name="5">
            <div class="troubleshooting-item">
              <p>如果以上方法未能解决问题，请尝试以下高级诊断步骤：</p>
              
              <div v-if="selectedProvider.name === 'openai'">
                <h4>OpenAI 专用诊断</h4>
                <ul>
                  <li>检查API密钥是否限制了特定模型的使用</li>
                  <li>确认您的账户是否有足够的配额使用所选模型</li>
                  <li>查看是否对您所在地区的API访问有限制</li>
                </ul>
              </div>
              
              <div v-else-if="selectedProvider.name === 'ollama_local'">
                <h4>Ollama 本地服务诊断</h4>
                <ul>
                  <li>确认Ollama服务是否正在运行：检查进程列表</li>
                  <li>验证模型是否已正确下载到本地</li>
                  <li>检查Ollama服务日志以获取更多错误信息</li>
                </ul>
                <div class="code-block">
                  <pre>curl http://localhost:11434/api/tags</pre>
                </div>
              </div>
              
              <div v-else>
                <ul>
                  <li>检查API请求和响应日志以获取更详细的错误信息</li>
                  <li>尝试使用API提供商提供的官方客户端库进行测试</li>
                  <li>联系API提供商的支持团队获取帮助</li>
                </ul>
              </div>
            </div>
          </el-collapse-item>
        </el-collapse>
        
        <el-divider />
        
        <div class="system-info">
          <h3>错误详情</h3>
          <div v-if="selectedProvider.error" class="error-details">
            <pre>{{ selectedProvider.error }}</pre>
          </div>
          <div v-else>
            <p>未获取到详细错误信息。请尝试再次测试连接以获取错误详情。</p>
          </div>
        </div>
      </div>
      
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showTroubleshootingDialog = false">关闭</el-button>
          <el-button type="primary" @click="testConnection(selectedProvider.name)" :loading="testingProvider === selectedProvider.name">
            重新测试
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue';
import { ElMessage } from 'element-plus';
import { Refresh } from '@element-plus/icons-vue';

const props = defineProps({
  // 自动刷新间隔（毫秒），0表示禁用自动刷新
  refreshInterval: {
    type: Number,
    default: 60000 // 默认1分钟
  },
  // API地址前缀
  apiPrefix: {
    type: String,
    default: '/api'
  }
});

const emit = defineEmits(['provider-status-change', 'provider-set-default']);

// 状态变量
const loading = ref(false);
const refreshing = ref(false);
const providerStatusList = ref([]);
const detailsVisible = ref(false);
const selectedProvider = ref(null);
const testingProvider = ref('');
const refreshTimer = ref(null);
const showTroubleshootingDialog = ref(false);
const emptyText = ref('加载中...');

// 加载提供商状态
const loadProviderStatus = async () => {
  if (loading.value) return;
  
  loading.value = true;
  emptyText.value = '加载中...';
  
  try {
    const response = await fetch(`${props.apiPrefix}/providers/status`);
    
    if (response.ok) {
      const data = await response.json();
      providerStatusList.value = data.providers || [];
      
      if (providerStatusList.value.length === 0) {
        emptyText.value = '未找到API提供商';
      }
      
      emit('provider-status-change', providerStatusList.value);
    } else {
      const errorData = await response.json();
      console.error('获取提供商状态失败:', errorData);
      emptyText.value = '获取提供商状态失败';
      ElMessage.error('获取提供商状态失败');
    }
  } catch (error) {
    console.error('获取提供商状态异常:', error);
    emptyText.value = '连接服务器失败，请检查网络连接';
    ElMessage.error('连接服务器失败，请检查网络连接');
  } finally {
    loading.value = false;
  }
};

// 测试提供商连接
const testConnection = async (providerName) => {
  if (testingProvider.value) return;
  
  testingProvider.value = providerName;
  
  try {
    const response = await fetch(`${props.apiPrefix}/providers/test-connection`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ provider: providerName })
    });
    
    if (response.ok) {
      const result = await response.json();
      
      // 更新提供商状态
      const index = providerStatusList.value.findIndex(p => p.name === providerName);
      if (index !== -1) {
        providerStatusList.value[index] = {
          ...providerStatusList.value[index],
          ...result,
          last_tested: new Date().toISOString()
        };
      }
      
      // 更新选中的提供商（如果存在）
      if (selectedProvider.value && selectedProvider.value.name === providerName) {
        selectedProvider.value = {
          ...selectedProvider.value,
          ...result,
          last_tested: new Date().toISOString()
        };
      }
      
      if (result.status === 'connected') {
        ElMessage.success(`${providerName} 连接成功`);
      } else {
        ElMessage.error(`${providerName} 连接失败: ${result.error || '未知错误'}`);
      }
      
      emit('provider-status-change', providerStatusList.value);
    } else {
      const errorData = await response.json();
      ElMessage.error(`测试连接失败: ${errorData.detail || '未知错误'}`);
    }
  } catch (error) {
    console.error('测试连接异常:', error);
    ElMessage.error('连接服务器失败，请检查网络连接');
  } finally {
    testingProvider.value = '';
  }
};

// 刷新所有提供商状态
const refreshAllProviders = async () => {
  if (refreshing.value) return;
  
  refreshing.value = true;
  
  try {
    const response = await fetch(`${props.apiPrefix}/providers/refresh`, {
      method: 'POST'
    });
    
    if (response.ok) {
      await loadProviderStatus();
      ElMessage.success('提供商状态已刷新');
    } else {
      const errorData = await response.json();
      ElMessage.error(`刷新提供商状态失败: ${errorData.detail || '未知错误'}`);
    }
  } catch (error) {
    console.error('刷新提供商状态异常:', error);
    ElMessage.error('连接服务器失败，请检查网络连接');
  } finally {
    refreshing.value = false;
  }
};

// 设置默认提供商
const setDefaultProvider = async (providerName) => {
  try {
    const response = await fetch(`${props.apiPrefix}/providers/set-default`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ provider: providerName })
    });
    
    if (response.ok) {
      ElMessage.success(`已将 ${providerName} 设为默认提供商`);
      emit('provider-set-default', providerName);
      
      // 重新加载提供商状态
      await loadProviderStatus();
    } else {
      const errorData = await response.json();
      ElMessage.error(`设置默认提供商失败: ${errorData.detail || '未知错误'}`);
    }
  } catch (error) {
    console.error('设置默认提供商异常:', error);
    ElMessage.error('连接服务器失败，请检查网络连接');
  }
};

// 显示提供商详情
const showDetails = (provider) => {
  selectedProvider.value = { ...provider };
  detailsVisible.value = true;
};

// 获取状态类型
const getStatusType = (status) => {
  switch (status) {
    case 'connected':
      return 'success';
    case 'error':
      return 'danger';
    case 'unknown':
    default:
      return 'info';
  }
};

// 获取状态文本
const getStatusText = (status) => {
  switch (status) {
    case 'connected':
      return '已连接';
    case 'error':
      return '连接错误';
    case 'unknown':
    default:
      return '未知状态';
  }
};

// 格式化日期时间
const formatDate = (dateString) => {
  const date = new Date(dateString);
  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(date);
};

// 获取提供商名称带表情符号
const getProviderNameWithEmoji = (name) => {
  const emojis = {
    'openai': '🤖',
    'anthropic': '👤',
    'ollama_local': '🏠',
    'silicon_flow': '💻',
    'azure_openai': '☁️',
    'gemini': '👨‍🚀',
    'default': '🔌'
  };
  
  const emoji = emojis[name] || emojis.default;
  return `<span class="provider-emoji">${emoji}</span> ${name}`;
};

// 过滤敏感配置信息
const filterSensitiveConfigInfo = (config) => {
  const filtered = { ...config };
  delete filtered.api_key; // 总是移除API密钥
  return filtered;
};

// 检查是否是敏感信息字段
const isSensitiveKey = (key) => {
  const sensitiveKeys = ['api_key', 'password', 'secret', 'token'];
  return sensitiveKeys.some(k => key.toLowerCase().includes(k));
};

// 获取提供商官方网站链接
const getLinkForProvider = (name) => {
  const links = {
    'openai': 'https://platform.openai.com/account/api-keys',
    'anthropic': 'https://console.anthropic.com/account/keys',
    'ollama_local': 'https://ollama.com/',
    'silicon_flow': 'https://flowgpt.com/',
    'azure_openai': 'https://portal.azure.com/',
    'gemini': 'https://aistudio.google.com/'
  };
  
  return links[name] || null;
};

// 获取提供商服务状态页面
const getStatusPageForProvider = (name) => {
  const statusPages = {
    'openai': 'https://status.openai.com/',
    'anthropic': 'https://status.anthropic.com/',
    'azure_openai': 'https://status.azure.com/'
  };
  
  return statusPages[name] || null;
};

// 设置自动刷新
const setupAutoRefresh = () => {
  clearAutoRefresh();
  
  if (props.refreshInterval > 0) {
    refreshTimer.value = setInterval(() => {
      loadProviderStatus();
    }, props.refreshInterval);
  }
};

// 清除自动刷新
const clearAutoRefresh = () => {
  if (refreshTimer.value) {
    clearInterval(refreshTimer.value);
    refreshTimer.value = null;
  }
};

// 组件挂载时加载提供商状态并设置自动刷新
onMounted(() => {
  loadProviderStatus();
  setupAutoRefresh();
});

// 组件卸载时清除自动刷新
onUnmounted(() => {
  clearAutoRefresh();
});
</script>

<style lang="scss" scoped>
.provider-status-diagnostics {
  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
    
    h2 {
      margin: 0;
      font-size: 20px;
      font-weight: 500;
    }
  }
  
  .provider-name {
    display: flex;
    align-items: center;
    
    :deep(.provider-emoji) {
      margin-right: 4px;
    }
  }
  
  .provider-details {
    .config-item {
      margin-bottom: 4px;
    }
    
    .error-message {
      color: #f56c6c;
      background-color: #fef0f0;
      padding: 8px;
      border-radius: 4px;
      white-space: pre-wrap;
      word-break: break-all;
    }
    
    .actions {
      margin-top: 20px;
      display: flex;
      justify-content: flex-end;
      gap: 10px;
    }
  }
  
  .troubleshooting-guide {
    h3 {
      font-size: 18px;
      font-weight: 600;
      margin-top: 0;
      margin-bottom: 16px;
      color: #409eff;
    }
    
    h4 {
      font-size: 16px;
      font-weight: 600;
      margin-top: 16px;
      margin-bottom: 8px;
    }
    
    .troubleshooting-item {
      padding: 8px 0;
      
      p {
        margin: 8px 0;
      }
      
      ul {
        padding-left: 20px;
        margin: 8px 0;
      }
      
      .troubleshooting-links {
        margin: 12px 0;
        
        a {
          color: #409eff;
          text-decoration: none;
          
          &:hover {
            text-decoration: underline;
          }
        }
      }
      
      .code-block {
        background-color: #f7f7f7;
        padding: 10px;
        border-radius: 4px;
        margin: 12px 0;
        
        pre {
          margin: 0;
          font-family: monospace;
          white-space: pre-wrap;
          word-break: break-all;
        }
      }
    }
    
    .system-info {
      margin-top: 24px;
      
      h3 {
        font-size: 18px;
        font-weight: 600;
        margin-top: 0;
        margin-bottom: 16px;
      }
      
      .error-details {
        background-color: #f7f7f7;
        padding: 10px;
        border-radius: 4px;
        
        pre {
          margin: 0;
          white-space: pre-wrap;
          word-break: break-all;
          font-family: monospace;
          font-size: 14px;
        }
      }
    }
  }
}
</style> 