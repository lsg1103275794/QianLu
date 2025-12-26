<template>
  <div class="backend-connection-diagnostics">
    <!-- 连接失败警告 -->
    <el-alert
      v-if="connectionFailed"
      type="error"
      :closable="false"
      show-icon
    >
      <template #title>
        <div class="alert-title">
          <span>无法连接到后端服务</span>
          <el-button type="primary" size="small" @click="retryConnection" :loading="retrying">
            重试连接
          </el-button>
        </div>
      </template>
      <div class="alert-content">
        <p>无法连接到后端服务，可能的原因包括：</p>
        <ul>
          <li>后端服务未启动</li>
          <li>网络连接问题</li>
          <li>端口冲突</li>
        </ul>
        <el-button type="info" size="small" @click="showTroubleshootingDialog = true">
          查看排障指南
        </el-button>
      </div>
    </el-alert>

    <!-- 故障排除对话框 -->
    <el-dialog
      v-model="showTroubleshootingDialog"
      title="后端连接故障排除"
      width="70%"
      destroy-on-close
    >
      <div class="troubleshooting-guide">
        <h3>后端服务连接故障排除指南</h3>
        
        <el-divider />
        
        <el-collapse accordion>
          <el-collapse-item title="1. 确认后端服务是否正在运行" name="1">
            <div class="troubleshooting-item">
              <p>请检查后端服务是否已启动并正在运行：</p>
              <ul>
                <li>确认您已经在终端运行了 <code>python backend_main.py</code> 命令</li>
                <li>检查终端窗口中是否有显示 "服务已启动" 或类似的信息</li>
                <li>确认没有出现任何错误消息</li>
              </ul>
              <div class="code-block">
                <pre>python backend_main.py</pre>
              </div>
            </div>
          </el-collapse-item>
          
          <el-collapse-item title="2. 检查依赖项是否安装完毕" name="2">
            <div class="troubleshooting-item">
              <p>确保所有必要的依赖项已正确安装：</p>
              <ul>
                <li>运行以下命令安装所有依赖项：</li>
              </ul>
              <div class="code-block">
                <pre>pip install -r requirements.txt</pre>
              </div>
              <p>如果遇到依赖冲突，可以尝试：</p>
              <div class="code-block">
                <pre>pip install -r requirements.txt --force-reinstall</pre>
              </div>
            </div>
          </el-collapse-item>
          
          <el-collapse-item title="3. 检查端口冲突" name="3">
            <div class="troubleshooting-item">
              <p>默认情况下，后端服务在端口 <code>4000</code> 上运行。检查该端口是否被其他程序占用：</p>
              
              <h4>Windows操作系统</h4>
              <div class="code-block">
                <pre>netstat -ano | findstr :4000</pre>
              </div>
              
              <h4>Linux/Mac操作系统</h4>
              <div class="code-block">
                <pre>lsof -i :4000</pre>
              </div>
              
              <p>如果端口被占用，您可以：</p>
              <ul>
                <li>关闭占用端口的应用程序</li>
                <li>修改配置，让后端使用其他端口</li>
              </ul>
            </div>
          </el-collapse-item>
          
          <el-collapse-item title="4. 检查CORS配置" name="4">
            <div class="troubleshooting-item">
              <p>如果前端能够发送请求但接收到CORS错误，请检查CORS配置：</p>
              <ul>
                <li>确保后端服务的CORS设置允许来自前端的请求</li>
                <li>检查前端请求中的源(Origin)是否被后端允许</li>
                <li>检查浏览器控制台是否有CORS相关的错误信息</li>
              </ul>
              <p>典型的CORS错误看起来像这样：</p>
              <div class="code-block">
                <pre>Access to fetch at 'http://localhost:4000/api/providers/status' from origin 'http://localhost:3000' has been blocked by CORS policy</pre>
              </div>
            </div>
          </el-collapse-item>
          
          <el-collapse-item title="5. 检查环境变量和配置文件" name="5">
            <div class="troubleshooting-item">
              <p>确保所有必要的环境变量和配置文件存在并且设置正确：</p>
              <ul>
                <li>检查 <code>.env</code> 文件是否存在且包含了必要的变量</li>
                <li>确认 <code>config</code> 目录中的配置文件格式正确</li>
                <li>尝试复制 <code>.env.example</code> 文件（如果存在）创建新的 <code>.env</code> 文件</li>
              </ul>
            </div>
          </el-collapse-item>
          
          <el-collapse-item title="6. 检查网络配置" name="6">
            <div class="troubleshooting-item">
              <p>如果前端和后端部署在不同的主机上，请确保网络配置正确：</p>
              <ul>
                <li>确认主机之间可以互相访问</li>
                <li>检查防火墙设置是否允许端口访问</li>
                <li>验证网络代理设置</li>
              </ul>
            </div>
          </el-collapse-item>
          
          <el-collapse-item title="7. 查看日志文件" name="7">
            <div class="troubleshooting-item">
              <p>查看后端日志文件可能会提供有用的错误信息：</p>
              <ul>
                <li>检查 <code>logs</code> 目录中的日志文件</li>
                <li>查看终端窗口中的输出信息</li>
              </ul>
              <p>典型的日志目录结构：</p>
              <div class="code-block">
                <pre>logs/
├── app.log      # 应用日志
├── error.log    # 错误日志
└── access.log   # 访问日志</pre>
              </div>
            </div>
          </el-collapse-item>
        </el-collapse>
        
        <el-divider />
        
        <div class="system-info">
          <h3>系统信息</h3>
          <p>如果您需要联系支持，请提供以下信息：</p>
          
          <el-descriptions :column="1" border>
            <el-descriptions-item label="浏览器">{{ systemInfo.browser }}</el-descriptions-item>
            <el-descriptions-item label="操作系统">{{ systemInfo.os }}</el-descriptions-item>
            <el-descriptions-item label="前端URL">{{ systemInfo.frontendUrl }}</el-descriptions-item>
            <el-descriptions-item label="后端URL">{{ systemInfo.backendUrl }}</el-descriptions-item>
            <el-descriptions-item label="错误信息">{{ connectionError.value || '无详细错误信息' }}</el-descriptions-item>
          </el-descriptions>
          
          <div class="actions">
            <el-button type="primary" @click="copySystemInfo" size="small">
              复制系统信息
            </el-button>
          </div>
        </div>
      </div>
      
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="showTroubleshootingDialog = false">关闭</el-button>
          <el-button type="primary" @click="retryConnection" :loading="retrying">
            重试连接
          </el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue';
import { ElMessage } from 'element-plus';

const props = defineProps({
  // 后端API基础URL
  backendUrl: {
    type: String,
    default: '/api'
  },
  // 检查间隔（毫秒）
  checkInterval: {
    type: Number,
    default: 5000 // 默认5秒检查一次
  },
  // 最大重试次数
  maxRetries: {
    type: Number,
    default: 3
  }
});

const emit = defineEmits(['connection-status-change']);

// 状态变量
const connectionFailed = ref(false);
const connectionError = ref('');
const retrying = ref(false);
const retryCount = ref(0);
const checkTimer = ref(null);
const showTroubleshootingDialog = ref(false);

// 系统信息
const systemInfo = reactive({
  browser: getBrowserInfo(),
  os: getOSInfo(),
  frontendUrl: window.location.origin,
  backendUrl: props.backendUrl || '/api',
  timestamp: new Date().toISOString()
});

// 检查后端连接
const checkBackendConnection = async () => {
  try {
    const response = await fetch(`${props.backendUrl}/health-check`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json'
      },
      // 设置较短的超时时间，避免长时间等待
      signal: AbortSignal.timeout(3000)
    });
    
    if (response.ok) {
      // 连接成功
      if (connectionFailed.value) {
        // 如果之前连接失败，现在恢复了，发出通知
        ElMessage.success('后端服务连接已恢复');
      }
      
      connectionFailed.value = false;
      connectionError.value = '';
      retryCount.value = 0;
      emit('connection-status-change', { connected: true });
    } else {
      // 服务器返回错误
      handleConnectionFailure(`服务器返回错误: ${response.status} ${response.statusText}`);
    }
  } catch (error) {
    // 连接异常
    handleConnectionFailure(error.message || '连接后端服务失败');
  }
};

// 处理连接失败
const handleConnectionFailure = (errorMessage) => {
  connectionFailed.value = true;
  connectionError.value = errorMessage;
  
  console.error('后端连接失败:', errorMessage);
  emit('connection-status-change', { 
    connected: false, 
    error: errorMessage 
  });
};

// 重试连接
const retryConnection = async () => {
  if (retrying.value) return;
  
  retrying.value = true;
  retryCount.value += 1;
  
  try {
    await checkBackendConnection();
    
    // 如果连接恢复，重置计数器
    if (!connectionFailed.value) {
      retryCount.value = 0;
    } else if (retryCount.value >= props.maxRetries) {
      // 超过最大重试次数
      ElMessage.error(`连接重试${props.maxRetries}次失败，请检查后端服务`);
    }
  } catch (error) {
    console.error('重试连接失败:', error);
  } finally {
    retrying.value = false;
  }
};

// 设置定期检查
const setupPeriodicCheck = () => {
  clearPeriodicCheck();
  
  // 仅当未设置为0时才启用定期检查
  if (props.checkInterval > 0) {
    checkTimer.value = setInterval(() => {
      if (!retrying.value) {
        checkBackendConnection();
      }
    }, props.checkInterval);
  }
};

// 清除定期检查
const clearPeriodicCheck = () => {
  if (checkTimer.value) {
    clearInterval(checkTimer.value);
    checkTimer.value = null;
  }
};

// 复制系统信息到剪贴板
const copySystemInfo = () => {
  // 更新时间戳
  systemInfo.timestamp = new Date().toISOString();
  
  const infoText = `
后端连接故障报告:
-------------------
时间: ${systemInfo.timestamp}
浏览器: ${systemInfo.browser}
操作系统: ${systemInfo.os}
前端URL: ${systemInfo.frontendUrl}
后端URL: ${systemInfo.backendUrl}
错误信息: ${connectionError.value || '无详细错误信息'}
`.trim();

  navigator.clipboard.writeText(infoText)
    .then(() => {
      ElMessage.success('系统信息已复制到剪贴板');
    })
    .catch(err => {
      console.error('复制失败:', err);
      ElMessage.error('复制系统信息失败');
    });
};

// 获取浏览器信息
function getBrowserInfo() {
  const ua = navigator.userAgent;
  let browser = 'Unknown';
  
  if (ua.includes('Chrome')) {
    browser = `Chrome ${ua.match(/Chrome\/(\d+)/)?.[1] || ''}`;
  } else if (ua.includes('Firefox')) {
    browser = `Firefox ${ua.match(/Firefox\/(\d+)/)?.[1] || ''}`;
  } else if (ua.includes('Safari') && !ua.includes('Chrome')) {
    browser = `Safari ${ua.match(/Version\/(\d+)/)?.[1] || ''}`;
  } else if (ua.includes('Edge')) {
    browser = `Edge ${ua.match(/Edge\/(\d+)/)?.[1] || ''}`;
  } else if (ua.includes('MSIE') || ua.includes('Trident/')) {
    browser = 'Internet Explorer';
  }
  
  return browser;
}

// 获取操作系统信息
function getOSInfo() {
  const ua = navigator.userAgent;
  let os = 'Unknown';
  
  if (ua.includes('Windows')) {
    os = `Windows ${ua.match(/Windows NT (\d+\.\d+)/)?.[1] || ''}`;
  } else if (ua.includes('Mac OS X')) {
    os = `macOS ${ua.match(/Mac OS X (\d+[._]\d+)/)?.[1]?.replace('_', '.') || ''}`;
  } else if (ua.includes('Linux')) {
    os = 'Linux';
  } else if (ua.includes('Android')) {
    os = `Android ${ua.match(/Android (\d+\.\d+)/)?.[1] || ''}`;
  } else if (ua.includes('iOS')) {
    os = `iOS ${ua.match(/OS (\d+_\d+)/)?.[1]?.replace('_', '.') || ''}`;
  }
  
  return os;
}

// 组件挂载时检查连接并设置定期检查
onMounted(() => {
  checkBackendConnection();
  setupPeriodicCheck();
});

// 组件卸载时清除定时器
onUnmounted(() => {
  clearPeriodicCheck();
});
</script>

<style lang="scss" scoped>
.backend-connection-diagnostics {
  .alert-title {
    display: flex;
    justify-content: space-between;
    align-items: center;
    width: 100%;
  }
  
  .alert-content {
    ul {
      padding-left: 20px;
      margin: 8px 0;
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
      
      code {
        background-color: #f2f2f2;
        padding: 2px 4px;
        border-radius: 3px;
        font-family: monospace;
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
      
      .actions {
        margin-top: 16px;
        display: flex;
        justify-content: flex-end;
      }
    }
  }
}
</style> 