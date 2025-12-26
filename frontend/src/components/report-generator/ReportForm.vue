<template>
  <el-form @submit.prevent="onSubmit" class="report-form">
    <el-form-item :label="addEmoji('研报主题', 'menu', 'edit')" prop="topic">
      <el-input
        :model-value="topic"
        @update:model-value="$emit('update:topic', $event)"
        placeholder="例如：人工智能最新进展、新能源汽车市场分析等"
        clearable
        :disabled="isLoading"
      />
    </el-form-item>

    <el-form-item :label="addEmoji('API 类型', 'menu', 'options')">
       <el-radio-group 
         :model-value="apiType" 
         @update:model-value="$emit('update:apiType', $event)" 
         :disabled="isLoading">
        <el-radio value="ollama">本地 Ollama</el-radio>
        <el-radio value="cloud">云端 API</el-radio>
      </el-radio-group>
    </el-form-item>

    <!-- Ollama 模型选择 (Conditional) -->
    <el-form-item :label="addEmoji('Ollama 模型 (可选)', 'provider', 'ollama_local')" v-if="apiType === 'ollama'" prop="selectedOllamaModel">
      <el-select 
        :model-value="selectedOllamaModel"
        @update:model-value="$emit('update:selectedOllamaModel', $event)"
        placeholder="请选择Ollama模型 (留空使用默认)"
        clearable
        :disabled="isLoading || loadingOllamaModels"
        :loading="loadingOllamaModels"
        style="width: 100%;"
      >
        <el-option
          v-for="item in ollamaModels"
          :key="item.value"
          :label="item.label"
          :value="item.value"
        />
        <template #empty>
          <div style="padding: 10px; text-align: center; color: #999;">
            {{ loadingOllamaModels ? '正在加载模型列表...' : '无可用模型或加载失败' }}
          </div>
        </template>
      </el-select>
      <div class="el-form-item__description" style="font-size: 12px; color: #909399;">
        请确保所选模型已在本地Ollama中拉取。
      </div>
    </el-form-item>

    <!-- 云 API Provider 选择 (Conditional) -->
    <el-form-item :label="addEmoji('云服务商', 'menu', 'cloud')" v-if="apiType === 'cloud'" prop="selectedCloudProvider">
      <el-select
        :model-value="selectedCloudProvider"
        @update:model-value="handleCloudProviderChange($event)" 
        placeholder="请选择云服务商"
        clearable
        filterable
        :disabled="isLoading || loadingCloudProviders"
        :loading="loadingCloudProviders"
        style="width: 100%;"
      >
        <el-option
          v-for="item in cloudProviders"
          :key="item.value"
          :label="item.label"
          :value="item.value"
        />
         <template #empty>
          <div style="padding: 10px; text-align: center; color: #999;">
            {{ loadingCloudProviders ? '正在加载服务商...' : '无可用云服务商或加载失败' }}
          </div>
        </template>
      </el-select>
    </el-form-item>

    <!-- 云 API Model 选择 (Conditional) -->
    <el-form-item :label="addEmoji('云模型', 'menu', 'robot')" v-if="apiType === 'cloud'" prop="selectedCloudModel">
       <el-select
        :model-value="selectedCloudModel"
        @update:model-value="$emit('update:selectedCloudModel', $event)"
        placeholder="请选择模型 (留空使用默认)"
        clearable
        filterable
        :disabled="isLoading || loadingCloudModels || !selectedCloudProvider"
        :loading="loadingCloudModels"
        style="width: 100%;"
      >
        <el-option
          v-for="item in cloudModels"
          :key="item.value"
          :label="item.label"
          :value="item.value"
        />
        <template #empty>
          <div style="padding: 10px; text-align: center; color: #999;">
            {{ loadingCloudModels ? '正在加载模型...' : (selectedCloudProvider ? '无可用模型或加载失败' : '请先选择服务商') }}
          </div>
        </template>
      </el-select>
    </el-form-item>

    <el-form-item>
      <el-button 
        type="primary" 
        @click="onSubmit" 
        :loading="isLoading"
        :disabled="isSubmitDisabled"
        :icon="Search"
      >
        {{ isLoading ? addEmoji('生成中...', 'menu', 'loading') : addEmoji('开始生成', 'menu', 'start') }}
      </el-button>
    </el-form-item>
  </el-form>
</template>

<script setup>
import { computed } from 'vue';
import { Search } from '@element-plus/icons-vue';
import { addEmoji } from '@/assets/emojiMap';

const props = defineProps({
  topic: { type: String, required: true },
  apiType: { type: String, required: true, validator: (value) => ['ollama', 'cloud'].includes(value) },
  // Ollama props
  selectedOllamaModel: { type: String, default: null },
  ollamaModels: { type: Array, default: () => [] },
  loadingOllamaModels: { type: Boolean, default: false },
  // Cloud props
  cloudProviders: { type: Array, default: () => [] },
  loadingCloudProviders: { type: Boolean, default: false },
  selectedCloudProvider: { type: String, default: null },
  cloudModels: { type: Array, default: () => [] },
  loadingCloudModels: { type: Boolean, default: false },
  selectedCloudModel: { type: String, default: null },
  // General props
  isLoading: { type: Boolean, default: false }
});

const emit = defineEmits([
  'update:topic',
  'update:apiType',
  'update:selectedOllamaModel',
  'update:selectedCloudProvider',
  'update:selectedCloudModel',
  'generate-report',
  'cloud-provider-changed' // Emit when cloud provider changes to trigger model fetch
]);

const isSubmitDisabled = computed(() => {
  if (props.isLoading) return true;
  if (!props.topic.trim()) return true;
  if (props.apiType === 'cloud' && !props.selectedCloudProvider) {
    // Optionally make provider selection mandatory for cloud
    // return true; 
  }
  return false;
});

const onSubmit = () => {
  emit('generate-report');
};

// Emit an event when the cloud provider changes so the parent can fetch models
const handleCloudProviderChange = (providerValue) => {
  emit('update:selectedCloudProvider', providerValue);
  emit('cloud-provider-changed', providerValue); // Pass the new provider value
};

</script>

<style scoped>
.report-form .el-form-item {
  margin-bottom: 22px;
}
.el-form-item__description {
  line-height: 1.2;
  margin-top: 4px;
}
</style> 