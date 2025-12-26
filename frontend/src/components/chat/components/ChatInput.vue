<template>
  <div class="chat-input-container">
    <el-form @submit.prevent="submit" class="input-form">
      <div class="input-wrapper">
        <el-input
          ref="inputRef"
          v-model="inputValue"
          type="textarea"
          :rows="textareaRows"
          :placeholder="placeholderText"
          :disabled="isProcessing"
          resize="none"
          @keydown.enter.exact.prevent="handleEnterPress"
          @keydown.ctrl.enter.prevent="addNewLine"
          @keydown.meta.enter.prevent="addNewLine"
          @keydown.shift.enter.prevent="addNewLine"
          @compositionstart="onCompositionStart"
          @compositionend="onCompositionEnd"
          @input="autoResize"
        />
        <div class="input-actions">
          <el-tooltip content="发送消息 (Enter)" placement="top" :hide-after="1500">
            <el-button
              type="primary"
              :disabled="!canSend"
              @click="submit"
              :loading="isProcessing"
              class="send-button"
              :icon="ArrowUpBold"
              circle
            ></el-button>
          </el-tooltip>
        </div>
      </div>
      <div class="input-tips">
        <span class="tip-item"><kbd>Enter</kbd> 发送 &nbsp;|&nbsp; <kbd>Shift</kbd> + <kbd>Enter</kbd> 换行</span>
        <span v-if="selectedModel" class="model-indicator">
          <el-tag size="small" type="info" effect="plain">{{ selectedProvider }} / {{ selectedModel }}</el-tag>
        </span>
      </div>
    </el-form>
  </div>
</template>

<script setup>
import { ref, computed, watch, nextTick, defineExpose } from 'vue';
import { ArrowUpBold } from '@element-plus/icons-vue';

const props = defineProps({
  modelValue: { type: String, default: '' },
  isProcessing: { type: Boolean, default: false },
  isComposing: { type: Boolean, default: false },
  selectedProvider: { type: String, default: '' },
  selectedModel: { type: String, default: '' }
});

const emit = defineEmits(['update:modelValue', 'send', 'insert-newline']);

// 内部输入值
const inputValue = ref('');
const isInternalComposing = ref(false);
const inputRef = ref(null);
const textareaRows = ref(1);
const maxRows = 5;

// 计算属性
const canSend = computed(() => {
  return inputValue.value.trim() && !props.isProcessing && !isInternalComposing.value;
});

const placeholderText = computed(() => {
  return props.isProcessing ? '处理中，请稍候...' : '输入消息，按Enter发送...';
});

// 监听外部值变化
watch(() => props.modelValue, (newValue) => {
  inputValue.value = newValue;
});

// 输入值变化时发出事件
watch(inputValue, (newValue) => {
  emit('update:modelValue', newValue);
});

// 自动调整高度
const autoResize = () => {
  if (!inputRef.value || !inputRef.value.$refs.textarea) return;
  
  const textarea = inputRef.value.$refs.textarea;
  textarea.style.height = 'auto';
  
  // 计算行数
  const lineHeight = parseInt(getComputedStyle(textarea).lineHeight);
  const paddingTop = parseInt(getComputedStyle(textarea).paddingTop);
  const paddingBottom = parseInt(getComputedStyle(textarea).paddingBottom);
  const lines = Math.min(
    Math.max(
      Math.ceil((textarea.scrollHeight - paddingTop - paddingBottom) / lineHeight),
      1
    ),
    maxRows
  );
  
  textareaRows.value = lines;
  
  // 确保滚动条在最大行数时可见
  if (lines >= maxRows) {
    textarea.style.overflowY = 'auto';
  } else {
    textarea.style.overflowY = 'hidden';
  }
};

// 输入法事件处理
const onCompositionStart = () => {
  isInternalComposing.value = true;
};

const onCompositionEnd = () => {
  isInternalComposing.value = false;
};

// 快捷键处理
const handleEnterPress = () => {
  if (canSend.value) {
    submit();
  }
};

const addNewLine = () => {
  emit('insert-newline');
};

// 提交表单
const submit = () => {
  if (!canSend.value) return;
  
  emit('send');
  nextTick(() => {
    autoResize();
  });
};

// 聚焦方法
const focus = () => {
  nextTick(() => {
    inputRef.value?.focus();
  });
};

// 暴露方法
defineExpose({
  focus,
  $refs: {
    inputRef
  }
});
</script>

<style lang="scss" scoped>
.chat-input-container {
  padding: 16px;
  border-top: 1px solid var(--el-border-color-light);
  background-color: var(--el-bg-color);
  position: relative;
  
  .input-form {
    width: 100%;
  }
  
  .input-wrapper {
    position: relative;
    display: flex;
    align-items: flex-end;
    
    :deep(.el-textarea) {
      .el-textarea__inner {
        padding: 12px 50px 12px 16px;
        min-height: 24px;
        line-height: 1.5;
        border-radius: 20px;
        resize: none;
        border-color: var(--el-border-color);
        box-shadow: 0 2px 6px rgba(0, 0, 0, 0.05);
        font-size: 15px;
        transition: all 0.3s;
        
        &:hover, &:focus {
          border-color: var(--el-color-primary);
          box-shadow: 0 3px 10px rgba(var(--el-color-primary-rgb), 0.1);
        }
        
        &:disabled {
          background-color: var(--el-fill-color-light);
          cursor: not-allowed;
        }
      }
    }
  }
  
  .input-actions {
    position: absolute;
    right: 8px;
    bottom: 8px;
    display: flex;
    align-items: center;
    gap: 8px;
    
    .send-button {
      box-shadow: 0 2px 6px rgba(var(--el-color-primary-rgb), 0.2);
      transition: all 0.2s;
      
      &:hover:not(:disabled) {
        transform: translateY(-2px);
        box-shadow: 0 4px 10px rgba(var(--el-color-primary-rgb), 0.3);
      }
      
      &:disabled {
        opacity: 0.6;
      }
    }
  }
  
  .input-tips {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-top: 8px;
    padding: 0 8px;
    color: var(--el-text-color-secondary);
    font-size: 12px;
    
    kbd {
      background-color: var(--el-bg-color-page);
      border: 1px solid var(--el-border-color-lighter);
      border-radius: 3px;
      box-shadow: 0 1px 1px rgba(0, 0, 0, 0.1);
      display: inline-block;
      font-size: 0.9em;
      line-height: 1;
      padding: 2px 5px;
      white-space: nowrap;
      margin: 0 2px;
    }
    
    .model-indicator {
      font-size: 12px;
    }
  }
}

// 深色模式适配
:deep(html.dark) {
  .chat-input-container {
    border-top-color: var(--el-border-color-darker);
    
    .input-wrapper {
      .el-textarea__inner {
        background-color: var(--el-bg-color-overlay);
        border-color: var(--el-border-color-darker);
        color: var(--el-text-color-primary);
        
        &:hover, &:focus {
          border-color: var(--el-color-primary);
        }
      }
    }
    
    kbd {
      background-color: var(--el-bg-color);
      border-color: var(--el-border-color);
    }
  }
}
</style>
