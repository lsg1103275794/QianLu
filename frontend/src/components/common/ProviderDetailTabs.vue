<template>
  <div class="provider-tabs">
    <el-tabs v-model="activeTab" tab-position="left" @tab-click="handleTabClick">
      <el-tab-pane
        v-for="(prov, index) in providers"
        :key="index"
        :label="prov.display_name"
        :name="prov.name"
      >
        <div class="provider-header">
          <h3>{{ prov.display_name }} 配置</h3>
          <div class="provider-actions">
            <el-button @click="$emit('test-connection', prov.name)" :loading="testingConnection === prov.name">
              测试连接
            </el-button>
            <el-button type="primary" @click="$emit('edit-config', prov.name)">
              编辑配置
            </el-button>
            <el-button 
              v-if="hasModelParams(prov.name)" 
              type="warning" 
              @click="$emit('edit-model-params', prov.name)"
            >
              高级模型参数
            </el-button>
          </div>
        </div>

        <!-- 提供商状态显示 -->
        <div class="provider-status-display">
          <el-alert
            v-if="!isConfigured(prov.name)"
            title="尚未配置"
            type="warning"
            :closable="false"
            show-icon
          >
            请点击"编辑配置"按钮完成必要设置
          </el-alert>
          <el-alert
            v-else-if="getStatus(prov.name) === 'connected'"
            title="连接正常"
            type="success"
            :closable="false"
            show-icon
          >
            此提供商已正确配置并可用
          </el-alert>
          <el-alert
            v-else-if="getStatus(prov.name) === 'error'"
            title="连接错误"
            type="error"
            :closable="false"
            show-icon
          >
            连接失败，请检查配置
          </el-alert>
          <el-alert
            v-else
            title="状态未知"
            type="info"
            :closable="false"
            show-icon
          >
            请点击"测试连接"按钮检查状态
          </el-alert>
        </div>

        <!-- 配置项显示 -->
        <div class="config-display">
          <template v-if="hasSettings(prov.name)">
            <div v-for="(value, key) in getBasicSettings(prov.name)" :key="key" class="config-item">
              <span class="config-key">{{ getKeyLabel(prov.name, key) }}:</span>
              <span class="config-value">{{ formatConfigValue(prov.name, key, value) }}</span>
            </div>
            
            <!-- 模型参数显示 -->
            <div v-if="hasModelParams(prov.name)" class="model-params-summary">
              <div class="params-header">
                <h4>模型参数</h4>
                <el-button 
                  type="primary" 
                  size="small" 
                  @click="$emit('edit-model-params', prov.name)"
                  plain
                >
                  编辑参数
                </el-button>
              </div>
              <div class="params-list">
                <div v-for="(value, key) in getModelParams(prov.name)" :key="key" class="param-item">
                  <span class="param-key">{{ getKeyLabel(prov.name, key) }}:</span>
                  <span class="param-value">{{ value }}</span>
                </div>
              </div>
            </div>
          </template>
          <div v-else class="no-config">
            <el-empty description="尚未配置" />
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { computed } from 'vue';

const props = defineProps({
  providers: {
    type: Array,
    default: () => []
  },
  activeProvider: {
    type: String,
    default: ''
  },
  providerSettings: {
    type: Object,
    default: () => ({})
  },
  providerStatus: {
    type: Object,
    default: () => ({})
  },
  testingConnection: {
    type: String,
    default: ''
  },
  utilFunctions: {
    type: Object,
    required: true,
    // 期望包含: isModelParam, getNormalizedPrefix, isSensitiveKey, getKeyLabel
  }
});

const emit = defineEmits([
  'test-connection', 
  'edit-config', 
  'edit-model-params', 
  'update:active-provider'
]);

// 同步active属性
const activeTab = computed({
  get: () => props.activeProvider,
  set: (value) => emit('update:active-provider', value)
});

// 处理标签页点击
const handleTabClick = (tab) => {
  if (tab && tab.props && tab.props.name) {
    emit('update:active-provider', tab.props.name);
  }
};

// 检查提供商是否已配置
const isConfigured = (providerName) => {
  return props.providerStatus[providerName]?.configured || false;
};

// 获取提供商状态
const getStatus = (providerName) => {
  return props.providerStatus[providerName]?.status || 'unknown';
};

// 检查是否有设置
const hasSettings = (providerName) => {
  return props.providerSettings[providerName] && 
         Object.keys(props.providerSettings[providerName]).length > 0;
};

// 获取基本设置(非模型参数)
const getBasicSettings = (providerName) => {
  if (!providerName || !props.providerSettings[providerName]) {
    return {};
  }
  
  const result = {};
  
  Object.keys(props.providerSettings[providerName]).forEach(key => {
    if (!props.utilFunctions.isModelParam(key)) {
      result[key] = props.providerSettings[providerName][key];
    }
  });
  
  return result;
};

// 获取模型参数
const getModelParams = (providerName) => {
  if (!providerName || !props.providerSettings[providerName]) {
    return {};
  }
  
  const result = {};
  
  Object.keys(props.providerSettings[providerName]).forEach(key => {
    if (props.utilFunctions.isModelParam(key)) {
      result[key] = props.providerSettings[providerName][key];
    }
  });
  
  return result;
};

// 判断提供商是否有模型参数
const hasModelParams = (providerName) => {
  if (!providerName || !props.providerSettings[providerName]) {
    return false;
  }
  
  return Object.keys(props.providerSettings[providerName]).some(key => 
    props.utilFunctions.isModelParam(key));
};

// 格式化配置值
const formatConfigValue = (providerName, key, value) => {
  if (!value) return '(未设置)';
  
  // 对于敏感信息，显示掩码
  if (props.utilFunctions.isSensitiveKey(key)) {
    if (value === '********') return '(已设置)';
    
    // 如果是API密钥，显示前4位和后4位
    if (value.length > 8) {
      return `${value.substring(0, 4)}...${value.substring(value.length - 4)}`;
    }
    return '********';
  }
  
  // 对于模型参数，根据不同类型格式化
  if (props.utilFunctions.isModelParam(key)) {
    if (key.includes('TEMPERATURE')) {
      return parseFloat(value).toFixed(2);
    }
    if (key.includes('MAX_TOKENS')) {
      return parseInt(value, 10).toString();
    }
    if (key.includes('TOP_P')) {
      return parseFloat(value).toFixed(2);
    }
  }
  
  return value;
};

// 获取键标签
const getKeyLabel = (providerName, key) => {
  return props.utilFunctions.getKeyLabel(providerName, key);
};
</script>

<style lang="scss" scoped>
.provider-tabs {
  margin-top: 20px;
}

.provider-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

.provider-actions {
  display: flex;
  gap: 10px;
}

.provider-status-display {
  margin-bottom: 20px;
}

.config-display {
  background-color: #f9f9f9;
  border-radius: 8px;
  padding: 16px;
}

.config-item {
  margin-bottom: 8px;
  display: flex;
}

.config-key {
  font-weight: bold;
  width: 150px;
}

.config-value {
  color: #606266;
}

.no-config {
  padding: 40px 0;
  text-align: center;
}

.model-params-summary {
  margin-top: 20px;
  background-color: #f0f9eb;
  border-radius: 8px;
  padding: 16px;
}

.params-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
}

.params-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px;
}

.param-item {
  display: flex;
  flex-direction: column;
}

.param-key {
  font-weight: bold;
  font-size: 12px;
  color: #303133;
}

.param-value {
  color: #606266;
}
</style> 