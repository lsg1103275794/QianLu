<template>
  <el-drawer
    v-model="isVisible"
    :title="`${providerName} 高级模型参数设置`"
    direction="rtl"
    size="600px"
    destroy-on-close
    custom-class="model-params-drawer"
  >
    <div class="model-params-editor">
      <!-- 使用操作指南组件 -->
      <OperationGuide v-if="props.showGuide" />
      
      <!-- 使用参数影响指南组件 -->
      <ParamGuide v-if="props.showGuide" />
      
      <!-- 使用悬浮保存按钮组件 -->
      <FloatingSaveButton 
        :visible="isVisible"
        :loading="isSaving"
        :disabled="!paramsDirty"
        :show-reset="paramsDirty"
        @save="saveParams"
        @reset="resetParams"
      />

      <!-- 提供商提示 -->
      <h2 style="margin-top: 20px">{{ providerName }} 模型参数</h2>
      
      <!-- 温度参数 -->
      <div class="param-section">
        <div class="param-header">
          <div class="param-title">
            <el-icon><Setting /></el-icon>
            <h3>{{ paramDescriptions.temperature.title }}</h3>
          </div>
          <el-tooltip effect="dark" content="恢复默认值" placement="top">
            <el-button 
              @click="localSettings.temperature = paramDescriptions.temperature.defaultValue" 
              size="small" 
              text 
              :icon="RefreshRight"
            />
          </el-tooltip>
        </div>
        
        <div class="param-description">
          <p v-html="paramDescriptions.temperature.description.replace(/\n/g, '<br>')"></p>
        </div>
        
        <div class="param-control">
          <div class="slider-labels">
            <span>精确</span>
            <span>平衡</span>
            <span>创造</span>
          </div>
          <el-slider
            v-model="localSettings.temperature"
            :min="paramDescriptions.temperature.min"
            :max="paramDescriptions.temperature.max"
            :step="paramDescriptions.temperature.step"
            show-input
          />
          <div class="value-explanation">
            当前值: <span :class="getTempValueClass(localSettings.temperature)">{{ localSettings.temperature }}</span> - 
            {{ getTempValueDescription(localSettings.temperature) }}
          </div>
        </div>
      </div>
      
      <!-- 最大长度参数 -->
      <div class="param-section">
        <div class="param-header">
          <div class="param-title">
            <el-icon><Setting /></el-icon>
            <h3>{{ paramDescriptions.max_tokens.title }}</h3>
          </div>
          <el-tooltip effect="dark" content="恢复默认值" placement="top">
            <el-button 
              @click="localSettings.max_tokens = paramDescriptions.max_tokens.defaultValue" 
              size="small" 
              text 
              :icon="RefreshRight"
            />
          </el-tooltip>
        </div>
        
        <div class="param-description">
          <p v-html="paramDescriptions.max_tokens.description.replace(/\n/g, '<br>')"></p>
        </div>
        
        <div class="param-control">
          <div class="tokens-input-group">
            <el-input-number
              v-model="localSettings.max_tokens"
              :min="paramDescriptions.max_tokens.min"
              :max="paramDescriptions.max_tokens.max"
              :step="paramDescriptions.max_tokens.step"
              style="width: 180px"
            />
            <div class="preset-buttons">
              <el-button @click="localSettings.max_tokens = 1024" size="small">短</el-button>
              <el-button @click="localSettings.max_tokens = 2048" size="small">中</el-button>
              <el-button @click="localSettings.max_tokens = 4096" size="small">长</el-button>
            </div>
          </div>
          <div class="value-explanation" style="margin-top: 12px;">
            {{ getTokensValueDescription(localSettings.max_tokens) }}
          </div>
        </div>
      </div>
      
      <!-- Top P参数 -->
      <div v-if="showTopP" class="param-section">
        <div class="param-header">
          <div class="param-title">
            <el-icon><Setting /></el-icon>
            <h3>{{ paramDescriptions.top_p.title }}</h3>
          </div>
          <el-tooltip effect="dark" content="恢复默认值" placement="top">
            <el-button 
              @click="localSettings.top_p = paramDescriptions.top_p.defaultValue" 
              size="small" 
              text 
              :icon="RefreshRight"
            />
          </el-tooltip>
        </div>
        
        <div class="param-description">
          <p v-html="paramDescriptions.top_p.description.replace(/\n/g, '<br>')"></p>
        </div>
        
        <div class="param-control">
          <el-slider
            v-model="localSettings.top_p"
            :min="paramDescriptions.top_p.min"
            :max="paramDescriptions.top_p.max"
            :step="paramDescriptions.top_p.step"
            show-input
          />
          <div class="value-explanation">
            {{ getTopPValueDescription(localSettings.top_p) }}
          </div>
        </div>
      </div>
      
      <!-- 提示区域 -->
      <el-alert
        type="success"
        title="建议设置"
        :closable="false"
        class="param-tips"
        v-if="props.showTips"
      >
        <div class="tips-content">
          <p><b>通用对话:</b> 温度 0.7, 最大长度 2048</p>
          <p><b>创意写作:</b> 温度 0.9, 最大长度 4096</p>
          <p><b>精确回答:</b> 温度 0.3, 最大长度 1024</p>
          <p><b>代码生成:</b> 温度 0.5, 最大长度 4096</p>
        </div>
      </el-alert>
    </div>
    
    <FixedDrawerButtons>
      <el-button @click="resetParams" :icon="RefreshRight">
        重置到默认值
      </el-button>
      <div style="width: 10px"></div>
      <el-button type="primary" @click="saveParams" :loading="isSaving" :icon="Check">
        确认并保存
      </el-button>
    </FixedDrawerButtons>
  </el-drawer>
</template>

<script setup>
import { ref, reactive, computed, watch, onMounted, defineProps, defineEmits } from 'vue';
import { Setting, RefreshRight, Check } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import FixedDrawerButtons from './FixedDrawerButtons.vue';
import OperationGuide from './OperationGuide.vue';
import ParamGuide from './ParamGuide.vue';
import FloatingSaveButton from './FloatingSaveButton.vue';

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  provider: {
    type: String,
    required: true
  },
  settings: {
    type: Object,
    default: () => ({})
  },
  showTopP: {
    type: Boolean,
    default: true
  },
  showGuide: {
    type: Boolean,
    default: true
  },
  showTips: {
    type: Boolean,
    default: true
  }
});

const emit = defineEmits(['update:visible', 'save', 'update:settings']);

// 参数设置对象，包含默认值
const paramSettings = {
  temperature: 0.7,
  max_tokens: 2048,
  top_p: 0.9,
  top_k: 40,
  frequency_penalty: 0,
  presence_penalty: 0,
  repeat_penalty: 1.1
};

// 本地设置副本，用于编辑
const localSettings = reactive({
  ...paramSettings
});

// 保存中状态
const isSaving = ref(false);

// 计算提供商名称（用于标题显示）
const providerName = computed(() => props.provider || '未知提供商');

// 同步visible属性
const isVisible = computed({
  get: () => props.visible,
  set: (value) => emit('update:visible', value)
});

// 添加参数是否改变的计算属性
const paramsDirty = computed(() => {
  if (!props.settings || !props.provider) return false;
  
  const providerSettings = props.settings[props.provider] || {};
  
  // 比较当前值和原始值是否有差异
  if (providerSettings.temperature !== undefined && 
      localSettings.temperature !== Number(providerSettings.temperature)) {
    return true;
  }
  
  if (providerSettings.max_tokens !== undefined && 
      localSettings.max_tokens !== Number(providerSettings.max_tokens)) {
    return true;
  }
  
  if (providerSettings.top_p !== undefined && 
      localSettings.top_p !== Number(providerSettings.top_p)) {
    return true;
  }
  
  return false;
});

// 初始化参数
const initParams = () => {
  // 重置为默认值
  Object.keys(paramSettings).forEach(key => {
    localSettings[key] = paramSettings[key];
  });
  
  // 安全检查：确保settings和provider存在
  if (!props.settings || !props.provider) {
    console.warn('无法初始化参数: settings或provider不存在');
    return;
  }
  
  // 安全地获取provider设置
  const providerSettings = props.settings[props.provider] || {};
  
  // 使用安全的赋值方式，确保数值类型正确
  if (providerSettings?.temperature !== undefined && providerSettings?.temperature !== null) {
    localSettings.temperature = Number(providerSettings.temperature);
  }
  
  if (providerSettings?.max_tokens !== undefined && providerSettings?.max_tokens !== null) {
    localSettings.max_tokens = Number(providerSettings.max_tokens);
  }
  
  if (providerSettings?.top_p !== undefined && providerSettings?.top_p !== null) {
    localSettings.top_p = Number(providerSettings.top_p);
  }
  
  if (providerSettings?.top_k !== undefined && providerSettings?.top_k !== null) {
    localSettings.top_k = Number(providerSettings.top_k);
  }
  
  if (providerSettings?.frequency_penalty !== undefined && providerSettings?.frequency_penalty !== null) {
    localSettings.frequency_penalty = Number(providerSettings.frequency_penalty);
  }
  
  if (providerSettings?.presence_penalty !== undefined && providerSettings?.presence_penalty !== null) {
    localSettings.presence_penalty = Number(providerSettings.presence_penalty);
  }
  
  if (providerSettings?.repeat_penalty !== undefined && providerSettings?.repeat_penalty !== null) {
    localSettings.repeat_penalty = Number(providerSettings.repeat_penalty);
  }
};

// 监听visible变化，当打开抽屉时初始化参数
watch(() => props.visible, (newVal) => {
  if (newVal) {
    initParams();
  }
});

// 监听provider变化，当切换提供商时初始化参数
watch(() => props.provider, (newVal, oldVal) => {
  if (newVal && newVal !== oldVal && props.visible) {
    initParams();
  }
});

// 监听settings变化，当设置更新时初始化参数
watch(() => props.settings, (newVal) => {
  if (newVal && props.visible) {
    initParams();
  }
}, { deep: true });

// 初始化
onMounted(() => {
  if (props.visible) {
    initParams();
  }
});

// 重置所有参数为默认值
const resetParams = () => {
  Object.keys(paramSettings).forEach(key => {
    localSettings[key] = paramSettings[key];
  });
  ElMessage.success('参数已重置为默认值');
};

// 保存参数
const saveParams = async () => {
  if (!props.provider) {
    ElMessage.warning('无法保存：未指定提供商');
    return;
  }
  
  isSaving.value = true;
  
  try {
    const updatedParams = {
      temperature: localSettings.temperature,
      max_tokens: localSettings.max_tokens,
      top_p: localSettings.top_p,
      top_k: localSettings.top_k,
      frequency_penalty: localSettings.frequency_penalty,
      presence_penalty: localSettings.presence_penalty,
      repeat_penalty: localSettings.repeat_penalty
    };
    
    emit('save', props.provider, updatedParams);
    // 也支持新的事件名称
    emit('update:settings', updatedParams);
    
    isVisible.value = false;
    ElMessage.success('参数已保存并应用');
  } catch (error) {
    console.error('保存参数失败:', error);
    ElMessage.error('参数保存失败，请重试');
  } finally {
    isSaving.value = false;
  }
};

// 模型参数描述
const paramDescriptions = {
  temperature: {
    title: '温度参数 (Temperature)',
    description: `温度参数控制模型输出的随机性和多样性。这是影响文本生成风格最关键的参数。
    • 较低的值(接近0)：使输出更确定、更一致，适合需要准确、保守回答的场景。
    • 较高的值(接近1)：使输出更多样化和创造性，适合头脑风暴和创意场景。
    • 0.7是通常的平衡点，既保持一定可预测性，又有创意空间。`,
    min: 0,
    max: 1,
    step: 0.1,
    defaultValue: 0.7
  },
  max_tokens: {
    title: '最大输出长度 (Max Tokens)',
    description: `控制模型单次回复可以生成的最大标记(token)数量。一个汉字通常是1-2个token，英文单词约1个token。
    • 较小的值：限制回复简短，适合需要简要总结或快速回答的场景。
    • 较大的值：允许更长回复，适合详细解释或生成长文本的场景。
    • 注意：更大的值会增加生成时间和资源消耗，不同模型对最大长度有不同限制。`,
    min: 10,
    max: 32000,
    step: 10,
    defaultValue: 2048
  },
  top_p: {
    title: '采样阈值 (Top-P)',
    description: `也称为核采样(Nucleus Sampling)，控制模型生成的多样性，通过概率质量截断。
    • 较低的值(如0.1)：仅考虑最可能的几个词，产生更确定和一致的输出。
    • 较高的值(如0.9)：考虑更多可能性，产生更多样化的输出。
    • 与温度参数配合使用时，可以在保持相对随机性的同时防止完全无关的输出。`,
    min: 0,
    max: 1, 
    step: 0.05,
    defaultValue: 0.9
  },
  top_k: {
    title: '词汇限制 (Top-K)',
    description: `限制模型每一步可以考虑的词汇数量。
    • 较低的值：限制选择范围，产生更可预测的输出。
    • 较高的值：允许更广泛的选择，可能产生更多样的输出。
    • 通常与Top-P结合使用效果更好。`,
    min: 1,
    max: 100,
    step: 1,
    defaultValue: 40
  },
  frequency_penalty: {
    title: '频率惩罚 (Frequency Penalty)',
    description: `降低模型重复使用相同词汇的倾向。
    • 较高的值：减少重复，使输出更多样化。
    • 较低的值：允许更多重复，可能导致循环或固定模式。
    • 对于需要创意和变化的场景很有用。`,
    min: -2.0,
    max: 2.0,
    step: 0.1,
    defaultValue: 0
  },
  presence_penalty: {
    title: '存在惩罚 (Presence Penalty)',
    description: `降低模型讨论已经提到过的主题的倾向。
    • 较高的值：鼓励模型探索新主题。
    • 较低的值：允许模型继续讨论已经提到的主题。
    • 对于保持对话新鲜感和减少重复很有用。`,
    min: -2.0,
    max: 2.0,
    step: 0.1,
    defaultValue: 0
  },
  repeat_penalty: {
    title: '重复惩罚 (Repeat Penalty)',
    description: `特别针对Ollama等本地模型的参数，减少重复输出的可能性。
    • 较高的值：大幅减少重复。
    • 1.0表示无惩罚，建议值为1.1-1.3。
    • 对于避免本地模型陷入循环很有用。`,
    min: 1.0,
    max: 2.0,
    step: 0.05,
    defaultValue: 1.1
  }
};

// 获取温度参数值的描述文本
const getTempValueDescription = (value) => {
  if (value <= 0.2) return '非常确定性强、保守的回答';
  if (value <= 0.4) return '较为确定性强、保守的回答';
  if (value <= 0.6) return '平衡的回答，有一定变化性';
  if (value <= 0.8) return '较为创造性、随机的回答';
  return '非常创造性、随机的回答';
};

// 获取温度参数值对应的CSS类
const getTempValueClass = (value) => {
  if (value <= 0.3) return 'value-conservative';
  if (value >= 0.8) return 'value-creative';
  return 'value-balanced';
};

// 获取最大tokens值的描述文本
const getTokensValueDescription = (value) => {
  if (value <= 1024) return '短回复 (约200-500个汉字)';
  if (value <= 2048) return '中等长度回复 (约500-1000个汉字)';
  if (value <= 4096) return '长回复 (约1000-2000个汉字)';
  return '非常长的回复 (2000+个汉字)';
};

// 获取Top-P值的描述文本
const getTopPValueDescription = (value) => {
  if (value <= 0.3) return '保守选词，更加聚焦';
  if (value <= 0.6) return '中等多样性，偏向聚焦';
  if (value <= 0.8) return '较高多样性，允许更多选择';
  return '最大多样性，考虑几乎所有可能性';
};

</script>

<style lang="scss" scoped>
.model-params-drawer {
  .model-params-editor {
    padding: 16px;
    padding-bottom: 80px; /* 为底部按钮留出空间 */
  }
  
  .param-guide {
    margin-bottom: 24px;
    
    .guide-title {
      font-weight: bold;
      margin-bottom: 5px;
    }
    
    .guide-text {
      margin: 0;
      line-height: 1.5;
    }
  }
  
  .param-section {
    margin-bottom: 24px;
    padding: 16px;
    border-radius: 8px;
    background-color: #f9fafc;
    border: 1px solid #ebeef5;
    
    .param-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 8px;
      
      .param-title {
        display: flex;
        align-items: center;
        gap: 8px;
        
        h3 {
          margin: 0;
          color: #303133;
        }
      }
    }
    
    .param-description {
      margin-bottom: 16px;
      color: #606266;
      font-size: 14px;
    }
    
    .param-control {
      margin-top: 12px;
    }
  }
  
  .param-tips {
    margin-top: 24px;
    
    .tips-content {
      p {
        margin: 6px 0;
        font-size: 13px;
        line-height: 1.4;
      }
    }
  }
}

.drawer-footer {
  display: flex;
  justify-content: flex-end;
  padding: 16px 0;
}

.floating-save {
  position: fixed;
  top: 16px;
  right: 16px;
  z-index: 100;
}

.floating-save button {
  font-weight: 600;
  padding: 8px 16px;
  transition: all 0.2s;
}

.floating-save button:hover {
  transform: scale(1.05);
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

.operation-guide,
.param-guide,
.param-tips {
  margin-bottom: 20px;
}

.tips-content {
  font-size: 14px;
  color: #606266;
}

.tips-content p {
  margin: 4px 0;
}

.tokens-input-group {
  display: flex;
  align-items: center;
  gap: 16px;
}

.preset-buttons {
  display: flex;
  gap: 8px;
}

/* 温度值样式 */
.temp-cold {
  color: #409eff;
  font-weight: 600;
}

.temp-mild {
  color: #67c23a;
  font-weight: 600;
}

.temp-warm {
  color: #e6a23c;
  font-weight: 600;
}

.temp-hot {
  color: #f56c6c;
  font-weight: 600;
}
</style> 