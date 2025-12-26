<template>
  <div class="backend-diagnostics" v-if="diagnosisAvailable() && !diagnosis.success">
    <el-alert
      type="error"
      :closable="false"
      show-icon
    >
      <template #title>
        <span class="error-title">
          后端服务连接失败
          <el-button type="primary" size="small" @click="retryConnection" :loading="loading">
            重试连接
          </el-button>
          <el-button type="info" size="small" @click="showTroubleshootGuide">
            故障排除
          </el-button>
        </span>
      </template>
      <div class="error-content">
        <p><strong>可能的问题：</strong></p>
        <ul>
          <li>后端服务未启动或未能正常运行</li>
          <li>网络连接或防火墙限制了前端访问后端的请求</li>
          <li>后端服务地址配置错误（默认应为http://localhost:8000）</li>
        </ul>
        <p v-if="diagnosis && diagnosis.message"><strong>错误详情：</strong> {{ diagnosis.message }}</p>
        <p><strong>建议：</strong></p>
        <ul>
          <li>确认后端服务已启动（在控制台运行 <code>python backend_main.py</code>）</li>
          <li>检查后端服务的控制台是否有错误信息</li>
          <li>确认您的浏览器能够访问 <code>http://localhost:8000/api/status</code></li>
        </ul>
      </div>
    </el-alert>
    
    <!-- 故障排除指南对话框 -->
    <el-dialog
      v-model="troubleshootDialogVisible"
      title="后端连接故障排除指南"
      width="60%"
    >
      <div class="troubleshoot-guide">
        <h3>常见问题及解决方法</h3>
        
        <el-collapse>
          <el-collapse-item title="1. 后端服务未启动" name="1">
            <div class="guide-content">
              <p><strong>症状：</strong> 无法连接到后端API，所有请求超时或返回"无法连接"错误。</p>
              <p><strong>解决方法：</strong></p>
              <ol>
                <li>打开命令行终端，导航到项目根目录</li>
                <li>确认Python虚拟环境已激活（如果使用虚拟环境）</li>
                <li>执行命令启动后端：<code>python backend_main.py</code></li>
                <li>检查控制台输出，确认服务成功启动并监听在端口8000</li>
              </ol>
              <p><strong>正常启动输出示例：</strong></p>
              <pre>INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)</pre>
            </div>
          </el-collapse-item>
          
          <el-collapse-item title="2. 后端依赖项缺失" name="2">
            <div class="guide-content">
              <p><strong>症状：</strong> 尝试启动后端时出现ModuleNotFoundError或ImportError错误。</p>
              <p><strong>解决方法：</strong></p>
              <ol>
                <li>确保已安装所有依赖项：<code>pip install -r requirements.txt</code></li>
                <li>如果特定模块仍然缺失，可以单独安装：<code>pip install [缺失的模块名]</code></li>
                <li>重新启动后端服务</li>
              </ol>
            </div>
          </el-collapse-item>
          
          <el-collapse-item title="3. 端口冲突" name="3">
            <div class="guide-content">
              <p><strong>症状：</strong> 后端启动时显示"Address already in use"错误。</p>
              <p><strong>解决方法：</strong></p>
              <ol>
                <li>检查8000端口是否被其他应用占用：
                  <ul>
                    <li>Windows: <code>netstat -ano | findstr 8000</code></li>
                    <li>Mac/Linux: <code>lsof -i :8000</code></li>
                  </ul>
                </li>
                <li>关闭占用端口的应用或修改项目配置使用不同端口</li>
                <li>如果是之前的后端进程没有正确关闭，找到进程ID并终止它</li>
              </ol>
            </div>
          </el-collapse-item>
          
          <el-collapse-item title="4. CORS配置问题" name="4">
            <div class="guide-content">
              <p><strong>症状：</strong> 浏览器控制台显示CORS相关错误，如"Access-Control-Allow-Origin"。</p>
              <p><strong>解决方法：</strong></p>
              <ol>
                <li>检查后端CORS配置是否正确</li>
                <li>确认前端开发服务器域名和端口在后端的允许列表中</li>
                <li>在开发环境中，可以考虑暂时设置CORS允许所有源（仅用于开发）</li>
              </ol>
            </div>
          </el-collapse-item>
          
          <el-collapse-item title="5. 环境变量配置问题" name="5">
            <div class="guide-content">
              <p><strong>症状：</strong> 后端启动但API访问返回环境变量或配置相关错误。</p>
              <p><strong>解决方法：</strong></p>
              <ol>
                <li>确认项目根目录中存在正确配置的.env文件</li>
                <li>检查.env中是否包含所有必要的变量和API密钥</li>
                <li>重启后端服务以加载最新的环境变量</li>
              </ol>
            </div>
          </el-collapse-item>
        </el-collapse>
        
        <h3 class="debug-title">调试步骤</h3>
        
        <div class="debug-steps">
          <ol>
            <li>确认后端服务状态：
              <pre>curl http://localhost:8000/api/status</pre>
              <p>应返回类似：<code>{"status":"running","version":"1.0.0"}</code></p>
            </li>
            <li>检查API提供商列表：
              <pre>curl http://localhost:8000/api/providers</pre>
              <p>应返回已配置的API提供商列表</p>
            </li>
            <li>检查日志文件：
              <p>检查 <code>logs/</code> 目录中的日志文件，寻找错误信息</p>
            </li>
          </ol>
        </div>
        
        <div class="contact-support">
          <h3>还需要帮助？</h3>
          <p>如果以上步骤无法解决问题，请：</p>
          <ul>
            <li>检查项目文档中的故障排除章节</li>
            <li>在GitHub项目页面提交Issue</li>
            <li>查看项目Wiki获取更多信息</li>
          </ul>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, defineProps, defineEmits } from 'vue';

const props = defineProps({
  diagnosis: {
    type: Object,
    default: () => null
  },
  loading: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['retry']);

const troubleshootDialogVisible = ref(false);

const showTroubleshootGuide = () => {
  troubleshootDialogVisible.value = true;
};

// 检查props和emit是否有效
const diagnosisAvailable = () => {
  return props.diagnosis !== null;
};

const retryConnection = () => {
  emit('retry');
};
</script>

<style lang="scss" scoped>
.backend-diagnostics {
  margin-bottom: 20px;

  .error-title {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .error-content {
    margin-top: 10px;
    
    ul {
      padding-left: 20px;
    }

    code {
      background-color: rgba(0, 0, 0, 0.1);
      padding: 2px 4px;
      border-radius: 3px;
      font-family: monospace;
    }
  }
}

.troubleshoot-guide {
  h3 {
    margin-top: 20px;
    margin-bottom: 10px;
    padding-bottom: 5px;
    border-bottom: 1px solid #eee;
    color: #409EFF;
  }

  .guide-content {
    padding: 10px;
    
    pre {
      background-color: #f5f7fa;
      padding: 10px;
      border-radius: 4px;
      overflow-x: auto;
      font-family: monospace;
      color: #476582;
    }
  }

  .debug-title {
    margin-top: 30px;
  }

  .debug-steps {
    background-color: #f8f9fb;
    padding: 15px;
    border-radius: 6px;
    border-left: 3px solid #409EFF;
    
    ol {
      padding-left: 20px;
    }
    
    pre {
      background-color: #eef0f5;
      padding: 8px;
      border-radius: 4px;
      margin: 5px 0;
    }
  }

  .contact-support {
    margin-top: 30px;
    background-color: #f0f9eb;
    padding: 15px;
    border-radius: 6px;
    border-left: 3px solid #67c23a;
  }
}
</style> 