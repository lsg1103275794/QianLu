<template>
  <div class="backend-health-check">
    <div class="header">
      <h2>系统健康状态</h2>
      <el-button 
        type="primary" 
        circle 
        @click="checkAllServices"
        :loading="checking"
      >
        <el-icon><Refresh /></el-icon>
      </el-button>
    </div>

    <el-table
      :data="serviceStatusList"
      style="width: 100%"
      :empty-text="emptyText"
      v-loading="loading"
    >
      <el-table-column prop="name" label="服务">
        <template #default="scope">
          <div class="service-name">
            <el-icon class="service-icon">
              <component :is="getServiceIcon(scope.row.type)" />
            </el-icon>
            <span>{{ scope.row.name }}</span>
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

      <el-table-column prop="description" label="描述">
        <template #default="scope">
          {{ scope.row.description || '-' }}
        </template>
      </el-table-column>

      <el-table-column prop="last_checked" label="最后检查时间" width="180">
        <template #default="scope">
          <span v-if="scope.row.last_checked">
            {{ formatDate(scope.row.last_checked) }}
          </span>
          <span v-else>未检查</span>
        </template>
      </el-table-column>

      <el-table-column label="操作" width="120">
        <template #default="scope">
          <el-button
            type="primary"
            size="small"
            @click="checkService(scope.row.id)"
            :loading="checkingServices[scope.row.id]"
          >
            检查
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 系统资源状态 -->
    <div class="system-resources" v-if="systemResources">
      <h3>系统资源</h3>
      <el-row :gutter="20">
        <el-col :xs="24" :sm="12" :md="8" :lg="6">
          <el-card shadow="hover">
            <template #header>
              <div class="card-header">
                <span>CPU使用率</span>
              </div>
            </template>
            <div class="resource-value">
              <el-progress
                type="dashboard"
                :percentage="systemResources.cpu_percent || 0"
                :color="getResourceColor(systemResources.cpu_percent, 80, 90)"
              />
            </div>
          </el-card>
        </el-col>
        
        <el-col :xs="24" :sm="12" :md="8" :lg="6">
          <el-card shadow="hover">
            <template #header>
              <div class="card-header">
                <span>内存使用率</span>
              </div>
            </template>
            <div class="resource-value">
              <el-progress
                type="dashboard"
                :percentage="systemResources.memory_percent || 0"
                :color="getResourceColor(systemResources.memory_percent, 80, 90)"
              />
            </div>
          </el-card>
        </el-col>
        
        <el-col :xs="24" :sm="12" :md="8" :lg="6">
          <el-card shadow="hover">
            <template #header>
              <div class="card-header">
                <span>磁盘使用率</span>
              </div>
            </template>
            <div class="resource-value">
              <el-progress
                type="dashboard"
                :percentage="systemResources.disk_percent || 0"
                :color="getResourceColor(systemResources.disk_percent, 85, 95)"
              />
            </div>
          </el-card>
        </el-col>
        
        <el-col :xs="24" :sm="12" :md="8" :lg="6">
          <el-card shadow="hover">
            <template #header>
              <div class="card-header">
                <span>运行时间</span>
              </div>
            </template>
            <div class="resource-value uptime">
              {{ formatUptime(systemResources.uptime) }}
            </div>
          </el-card>
        </el-col>
      </el-row>
    </div>

    <!-- 问题检测与修复 -->
    <div class="problem-detection" v-if="detectedProblems.length > 0">
      <h3>检测到的问题</h3>
      <el-alert
        v-for="(problem, index) in detectedProblems"
        :key="index"
        :title="problem.title"
        :description="problem.description"
        :type="problem.severity"
        :closable="false"
        show-icon
        style="margin-bottom: 10px;"
      >
        <template #default>
          <div class="problem-actions" v-if="problem.fixable">
            <el-button 
              type="primary" 
              size="small" 
              @click="fixProblem(problem.id)"
              :loading="fixingProblems[problem.id]"
            >
              修复问题
            </el-button>
          </div>
        </template>
      </el-alert>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue';
import { ElMessage } from 'element-plus';
import { 
  Refresh, 
  Monitor, 
  Database, 
  Connection, 
  Platform, 
  Cpu, 
  Folder
} from '@element-plus/icons-vue';

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

const emit = defineEmits(['health-status-change', 'problem-detected', 'problem-fixed']);

// 状态变量
const loading = ref(false);
const checking = ref(false);
const serviceStatusList = ref([]);
const systemResources = ref(null);
const detectedProblems = ref([]);
const checkingServices = reactive({});
const fixingProblems = reactive({});
const refreshTimer = ref(null);
const emptyText = ref('加载中...');

// 加载服务状态
const loadServiceStatus = async () => {
  if (loading.value) return;
  
  loading.value = true;
  emptyText.value = '加载中...';
  
  try {
    const response = await fetch(`${props.apiPrefix}/system/health`);
    
    if (response.ok) {
      const data = await response.json();
      serviceStatusList.value = data.services || [];
      systemResources.value = data.resources || null;
      detectedProblems.value = data.problems || [];
      
      if (serviceStatusList.value.length === 0) {
        emptyText.value = '未找到服务状态信息';
      }
      
      emit('health-status-change', { 
        services: serviceStatusList.value,
        resources: systemResources.value,
        problems: detectedProblems.value
      });
    } else {
      const errorData = await response.json();
      console.error('获取服务状态失败:', errorData);
      emptyText.value = '获取服务状态失败';
      ElMessage.error('获取服务状态失败');
    }
  } catch (error) {
    console.error('获取服务状态异常:', error);
    emptyText.value = '连接服务器失败，请检查网络连接';
    ElMessage.error('连接服务器失败，请检查网络连接');
  } finally {
    loading.value = false;
  }
};

// 检查单个服务
const checkService = async (serviceId) => {
  if (checkingServices[serviceId]) return;
  
  checkingServices[serviceId] = true;
  
  try {
    const response = await fetch(`${props.apiPrefix}/system/health/service/${serviceId}`, {
      method: 'POST'
    });
    
    if (response.ok) {
      const result = await response.json();
      
      // 更新服务状态
      const index = serviceStatusList.value.findIndex(s => s.id === serviceId);
      if (index !== -1) {
        serviceStatusList.value[index] = {
          ...serviceStatusList.value[index],
          ...result,
          last_checked: new Date().toISOString()
        };
      }
      
      ElMessage.success(`服务 ${result.name} 检查完成`);
      
      // 更新问题列表
      if (result.problems && result.problems.length > 0) {
        updateDetectedProblems(result.problems);
      }
      
      emit('health-status-change', { 
        services: serviceStatusList.value,
        resources: systemResources.value,
        problems: detectedProblems.value
      });
    } else {
      const errorData = await response.json();
      ElMessage.error(`检查服务失败: ${errorData.detail || '未知错误'}`);
    }
  } catch (error) {
    console.error('检查服务异常:', error);
    ElMessage.error('连接服务器失败，请检查网络连接');
  } finally {
    checkingServices[serviceId] = false;
  }
};

// 检查所有服务
const checkAllServices = async () => {
  if (checking.value) return;
  
  checking.value = true;
  
  try {
    const response = await fetch(`${props.apiPrefix}/system/health/check-all`, {
      method: 'POST'
    });
    
    if (response.ok) {
      const data = await response.json();
      serviceStatusList.value = data.services || [];
      systemResources.value = data.resources || null;
      
      if (data.problems && data.problems.length > 0) {
        updateDetectedProblems(data.problems);
      } else {
        detectedProblems.value = [];
      }
      
      emit('health-status-change', { 
        services: serviceStatusList.value,
        resources: systemResources.value,
        problems: detectedProblems.value
      });
      
      ElMessage.success('所有服务检查完成');
    } else {
      const errorData = await response.json();
      ElMessage.error(`检查所有服务失败: ${errorData.detail || '未知错误'}`);
    }
  } catch (error) {
    console.error('检查所有服务异常:', error);
    ElMessage.error('连接服务器失败，请检查网络连接');
  } finally {
    checking.value = false;
  }
};

// 修复问题
const fixProblem = async (problemId) => {
  if (fixingProblems[problemId]) return;
  
  fixingProblems[problemId] = true;
  
  try {
    const response = await fetch(`${props.apiPrefix}/system/health/fix/${problemId}`, {
      method: 'POST'
    });
    
    if (response.ok) {
      const result = await response.json();
      
      if (result.success) {
        ElMessage.success(`问题已修复: ${result.message || '修复成功'}`);
        
        // 移除已修复的问题
        detectedProblems.value = detectedProblems.value.filter(p => p.id !== problemId);
        
        // 重新加载服务状态
        await loadServiceStatus();
        
        emit('problem-fixed', { problemId, result });
      } else {
        ElMessage.error(`修复失败: ${result.message || '未知错误'}`);
      }
    } else {
      const errorData = await response.json();
      ElMessage.error(`修复问题失败: ${errorData.detail || '未知错误'}`);
    }
  } catch (error) {
    console.error('修复问题异常:', error);
    ElMessage.error('连接服务器失败，请检查网络连接');
  } finally {
    fixingProblems[problemId] = false;
  }
};

// 更新检测到的问题
const updateDetectedProblems = (newProblems) => {
  // 合并新旧问题列表，避免重复
  const existingIds = detectedProblems.value.map(p => p.id);
  const uniqueNewProblems = newProblems.filter(p => !existingIds.includes(p.id));
  
  if (uniqueNewProblems.length > 0) {
    detectedProblems.value = [...detectedProblems.value, ...uniqueNewProblems];
    emit('problem-detected', uniqueNewProblems);
  }
};

// 获取状态类型
const getStatusType = (status) => {
  switch (status) {
    case 'running':
    case 'ok':
      return 'success';
    case 'error':
    case 'stopped':
      return 'danger';
    case 'warning':
      return 'warning';
    case 'unknown':
    default:
      return 'info';
  }
};

// 获取状态文本
const getStatusText = (status) => {
  switch (status) {
    case 'running':
      return '运行中';
    case 'ok':
      return '正常';
    case 'error':
      return '错误';
    case 'stopped':
      return '已停止';
    case 'warning':
      return '警告';
    case 'unknown':
    default:
      return '未知状态';
  }
};

// 获取服务图标
const getServiceIcon = (type) => {
  switch (type) {
    case 'web':
      return Monitor;
    case 'database':
      return Database;
    case 'api':
      return Connection;
    case 'system':
      return Platform;
    case 'processor':
      return Cpu;
    case 'storage':
      return Folder;
    default:
      return Monitor;
  }
};

// 获取资源颜色
const getResourceColor = (value, warningThreshold, dangerThreshold) => {
  if (!value && value !== 0) return '';
  
  if (value >= dangerThreshold) {
    return '#F56C6C'; // 危险红色
  } else if (value >= warningThreshold) {
    return '#E6A23C'; // 警告黄色
  } else {
    return '#67C23A'; // 正常绿色
  }
};

// 格式化运行时间
const formatUptime = (seconds) => {
  if (!seconds && seconds !== 0) return '-';
  
  const days = Math.floor(seconds / (3600 * 24));
  const hours = Math.floor((seconds % (3600 * 24)) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  
  let result = '';
  
  if (days > 0) {
    result += `${days}天 `;
  }
  
  if (hours > 0 || days > 0) {
    result += `${hours}小时 `;
  }
  
  result += `${minutes}分钟`;
  
  return result;
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

// 设置自动刷新
const setupAutoRefresh = () => {
  clearAutoRefresh();
  
  if (props.refreshInterval > 0) {
    refreshTimer.value = setInterval(() => {
      loadServiceStatus();
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

// 组件挂载时加载服务状态并设置自动刷新
onMounted(() => {
  loadServiceStatus();
  setupAutoRefresh();
});

// 组件卸载时清除自动刷新
onUnmounted(() => {
  clearAutoRefresh();
});
</script>

<style lang="scss" scoped>
.backend-health-check {
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
  
  .service-name {
    display: flex;
    align-items: center;
    
    .service-icon {
      margin-right: 8px;
      font-size: 18px;
    }
  }
  
  .system-resources {
    margin-top: 30px;
    
    h3 {
      font-size: 18px;
      font-weight: 600;
      margin-top: 0;
      margin-bottom: 16px;
    }
    
    .card-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      
      span {
        font-size: 15px;
        font-weight: 500;
      }
    }
    
    .resource-value {
      display: flex;
      justify-content: center;
      align-items: center;
      height: 120px;
      
      &.uptime {
        font-size: 20px;
        font-weight: 600;
        color: #409eff;
      }
    }
  }
  
  .problem-detection {
    margin-top: 30px;
    
    h3 {
      font-size: 18px;
      font-weight: 600;
      margin-top: 0;
      margin-bottom: 16px;
    }
    
    .problem-actions {
      margin-top: 10px;
      display: flex;
      justify-content: flex-end;
    }
  }
}
</style> 