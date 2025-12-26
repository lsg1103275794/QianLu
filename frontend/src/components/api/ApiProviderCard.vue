<template>
  <el-card shadow="hover" class="provider-card" :class="cardClasses">
    <div class="flex justify-between items-center mb-4">
      <div class="text-lg font-bold flex items-center">
        <span v-html="providerEmoji"></span>
        <span class="ml-2">{{ provider.display_name }}</span>
        
        <!-- 配置状态指示器 -->
        <el-tag v-if="status?.configured" type="success" size="small" class="ml-2">已配置</el-tag>
        <el-tag v-else type="info" size="small" class="ml-2">未配置</el-tag>
        
        <!-- 连接状态指示器 -->
        <el-tag v-if="status?.isConnected" type="success" size="small" class="ml-2">已连接</el-tag>
        <el-tag v-if="status?.isConnecting" type="warning" size="small" class="ml-2">连接中...</el-tag>
        <el-tag v-if="status?.error" type="danger" size="small" class="ml-2">连接失败</el-tag>
      </div>
      <div>
        <!-- 设为默认按钮 -->
        <el-button 
          :type="isDefaultProvider ? 'primary' : 'default'" 
          size="small" 
          @click="$emit('set-default', provider.name)"
          :disabled="!status?.configured"
        >
          {{ isDefaultProvider ? '默认' : '设为默认' }}
        </el-button>
        <!-- 配置按钮 -->
        <el-button type="primary" size="small" @click="$emit('open-config', provider.name)">
          <el-icon><Setting /></el-icon>
          <span class="ml-1">配置</span>
        </el-button>
        <!-- 测试连接按钮 -->
        <el-button 
          type="success" 
          size="small" 
          :loading="status?.isConnecting"
          :disabled="!status?.isConfigured"
          @click="$emit('test-connection', provider.name)"
        >
          <el-icon><Connection /></el-icon>
          <span class="ml-1">测试连接</span>
        </el-button>
      </div>
    </div>
    
    <!-- 模型列表 -->
    <div v-if="status?.configured">
      <div class="mb-2 font-medium">可用模型：</div>
      <div v-if="isCurrentProvider && modelsList.length > 0" class="models-grid">
        <el-tag
          v-for="model in modelsList"
          :key="`${provider.name}-${model.id}`"
          class="model-tag"
          :type="defaultModel === model.id ? 'primary' : 'info'"
          @click="$emit('set-default-model', provider.name, model.id)"
        >
          {{ model.name || model.id }}
        </el-tag>
      </div>
      <div v-else-if="isCurrentProvider && modelsList.length === 0" class="empty-models">
        未找到可用模型
      </div>
      <div v-else class="load-models">
        <el-button type="text" @click="$emit('load-models', provider.name)">加载模型列表</el-button>
      </div>
    </div>
    
    <!-- 未配置提示 -->
    <div v-else class="empty-models">
      请先完成配置以显示可用模型
    </div>
  </el-card>
</template>

<script setup>
import { computed } from 'vue';
import { Setting, Connection } from '@element-plus/icons-vue';

const props = defineProps({
  provider: {
    type: Object,
    required: true
  },
  status: {
    type: Object,
    default: () => ({})
  },
  isCurrentProvider: {
    type: Boolean,
    default: false
  },
  isDefaultProvider: {
    type: Boolean,
    default: false
  },
  modelsList: {
    type: Array,
    default: () => []
  },
  defaultModel: {
    type: String,
    default: ''
  }
});

defineEmits([
  'set-default', 
  'open-config', 
  'test-connection', 
  'set-default-model',
  'load-models'
]);

// 计算卡片样式类
const cardClasses = computed(() => {
  const classes = [];
  
  if (props.isDefaultProvider) {
    classes.push('default-provider');
  }
  
  if (props.status?.configured) {
    classes.push('configured-provider');
  }
  
  if (props.status?.error) {
    classes.push('error-provider');
  }
  
  return classes;
});

// 计算提供商图标
const providerEmoji = computed(() => {
  if (!props.provider || !props.provider.name) return '🔌';
  
  switch (props.provider.name) {
    case 'ollama_local':
      return '🦙';
    case 'google_gemini':
      return '🌌';
    case 'openai':
      return '🧠';
    case 'zhipu_ai':
      return '🧩';
    case 'deepseek_ai':
      return '🔍';
    case 'volc_engine':
      return '🌋';
    case 'silicon_flow':
      return '🔄';
    default:
      return '🤖';
  }
});
</script>

<style lang="scss">
/* 去除scoped限制以允许全局样式应用 */

.provider-card {
  margin-bottom: 16px;
  width: 100%;
  
  /* 覆盖全局卡片样式，使用CSS变量 */
  &.default-provider {
    .el-card__body {
      background: linear-gradient(135deg, rgba(240, 249, 235, 0.2), rgba(236, 245, 255, 0.2));
      border-left: 3px solid var(--light-accent-primary);
    }
    
    html.dark & .el-card__body {
      background: linear-gradient(135deg, rgba(66, 185, 131, 0.1), rgba(79, 126, 255, 0.1));
      border-left: 3px solid var(--dark-accent-primary);
    }
  }
  
  &.configured-provider {
    .el-card__header {
      background-color: rgba(240, 249, 235, 0.7);
      
      html.dark & {
        background-color: rgba(66, 185, 131, 0.1);
      }
    }
  }
  
  &.error-provider {
    .el-card__header {
      background-color: rgba(254, 240, 240, 0.7);
      
      html.dark & {
        background-color: rgba(245, 108, 108, 0.1);
      }
    }
  }
  
  /* 模型列表样式 */
  .models-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
    gap: 8px;
    margin-bottom: 16px;
    
    .model-tag {
      margin-bottom: 0;
      cursor: pointer;
      transition: all 0.2s ease;
      
      &:hover {
        transform: translateY(-2px);
        box-shadow: 0 2px 5px rgba(0, 0, 0, 0.1);
      }
    }
  }
  
  .empty-models, .load-models {
    color: var(--light-text-secondary);
    padding: 12px;
    border-radius: 6px;
    background-color: rgba(0, 0, 0, 0.02);
    
    html.dark & {
      color: var(--dark-text-secondary);
      background-color: rgba(255, 255, 255, 0.02);
    }
  }
}
</style> 