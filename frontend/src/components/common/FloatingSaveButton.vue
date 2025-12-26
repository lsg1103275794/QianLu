<template>
  <div class="floating-save-container" v-if="visible">
    <el-button type="primary" :loading="loading" @click="onSave" :disabled="disabled">
      <el-icon class="el-icon--left" v-if="!loading"><Check /></el-icon>{{ saveText }}
    </el-button>
    <el-button v-if="showReset" plain type="info" @click="onReset" size="small" class="reset-btn">
      <el-icon class="el-icon--left"><RefreshRight /></el-icon>{{ resetText }}
    </el-button>
  </div>
</template>

<script setup>
import { Check, RefreshRight } from '@element-plus/icons-vue';
import { defineProps, defineEmits } from 'vue';

defineProps({
  visible: {
    type: Boolean,
    default: true
  },
  loading: {
    type: Boolean,
    default: false
  },
  disabled: {
    type: Boolean,
    default: false
  },
  showReset: {
    type: Boolean,
    default: true
  },
  saveText: {
    type: String,
    default: '保存参数'
  },
  resetText: {
    type: String,
    default: '重置'
  }
});

const emit = defineEmits(['save', 'reset']);

const onSave = () => {
  emit('save');
};

const onReset = () => {
  emit('reset');
};
</script>

<style lang="scss">
/* 使用全局变量和合并共享样式，去除scoped以允许全局样式应用 */
.floating-save-container {
  position: fixed;
  top: 70px;
  right: 20px;
  z-index: 1000;
  display: flex;
  flex-direction: column;
  gap: 8px;
  background-color: rgba(255, 255, 255, 0.7); /* 使用半透明背景 */
  backdrop-filter: blur(10px); /* 添加毛玻璃效果 */
  padding: 12px;
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.2); /* 添加微妙的边框 */
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.08), 0 2px 8px rgba(0, 0, 0, 0.04); /* 立体阴影 */
  transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
  
  &:hover {
    transform: translateY(-3px);
    box-shadow: 0 12px 28px rgba(0, 0, 0, 0.1), 0 4px 12px rgba(0, 0, 0, 0.07);
  }
  
  /* 深色模式支持 */
  html.dark & {
    background-color: rgba(10, 10, 10, 0.7);
    border-color: rgba(34, 34, 34, 0.5);
    box-shadow: 0 8px 20px rgba(0, 0, 0, 0.25), 0 2px 8px rgba(0, 0, 0, 0.15);
    
    &:hover {
      box-shadow: 0 12px 28px rgba(0, 0, 0, 0.3), 0 4px 12px rgba(0, 0, 0, 0.2);
    }
  }
  
  /* 按钮强调动画效果 */
  .el-button--primary {
    animation: pulse 2s infinite;
  }
  
  @keyframes pulse {
    0% { box-shadow: 0 0 0 0 rgba(138, 109, 59, 0.4); }
    70% { box-shadow: 0 0 0 10px rgba(138, 109, 59, 0); }
    100% { box-shadow: 0 0 0 0 rgba(138, 109, 59, 0); }
  }
  
  html.dark & .el-button--primary {
    @keyframes pulse-dark {
      0% { box-shadow: 0 0 0 0 rgba(66, 185, 131, 0.4); }
      70% { box-shadow: 0 0 0 10px rgba(66, 185, 131, 0); }
      100% { box-shadow: 0 0 0 0 rgba(66, 185, 131, 0); }
    }
    & {
      animation: pulse-dark 2s infinite;
    }
  }
}

.reset-btn {
  margin-top: 2px;
}
</style> 