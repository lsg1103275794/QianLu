<template>
  <div class="chat-header">
    <div class="header-left">
      <div class="logo-container">
        <span class="app-logo">{{ getEmoji('menu', 'brain') }} GlyphChat</span>
      </div>
      <div class="model-selector" v-if="provider && model">
        <el-badge value="活跃" type="success" :hidden="!isProcessing">
          <el-tag size="large" effect="light" class="model-tag">
            {{ provider }} / {{ model }}
          </el-tag>
        </el-badge>
      </div>
      <div class="model-info" v-if="provider || model">
        <span class="provider-name">{{ provider }}</span>
        <span class="model-name" v-if="model">{{ model }}</span>
      </div>
    </div>

    <div class="header-actions">
      <el-tooltip content="查看历史记录" placement="top" :hide-after="1500">
        <el-button
          type="primary"
          plain
          size="small"
          :icon="Tickets"
          :loading="loadingHistory"
          @click="$emit('load-history')"
          class="action-button history-button"
        >
          历史记录
        </el-button>
      </el-tooltip>
      
      <el-dropdown trigger="click" @command="handleCommand">
        <el-button type="info" plain size="small" :icon="MoreFilled" class="action-button">
          菜单
        </el-button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="clear" :icon="Delete">
              清空对话
            </el-dropdown-item>
            <el-dropdown-item command="reset" :icon="RefreshRight">
              重置界面
            </el-dropdown-item>
            <el-dropdown-item command="help" :icon="QuestionFilled" divided>
              帮助
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
      
      <el-tooltip content="紧急重置（在界面卡住时使用）" placement="bottom" effect="dark" v-if="isProcessing">
        <el-button 
          type="danger" 
          :icon="WarningFilled" 
          circle 
          size="small"
          @click="$emit('emergency-reset')"
          class="emergency-btn"
        ></el-button>
      </el-tooltip>
    </div>
  </div>
</template>

<script setup>
import { 
  Delete, 
  RefreshRight, 
  MoreFilled, 
  Tickets, 
  QuestionFilled, 
  WarningFilled, 
} from '@element-plus/icons-vue';
import { getEmoji } from '../../../assets/emojiMap';
import { ElMessageBox } from 'element-plus';

defineProps({
  provider: { type: String, default: '' },
  model: { type: String, default: '' },
  isProcessing: { type: Boolean, default: false },
  loadingHistory: { type: Boolean, default: false }
});

const emit = defineEmits([
  'clear-chat', 
  'emergency-reset', 
  'load-history'
]);

const handleCommand = (command) => {
  switch (command) {
    case 'clear':
      handleClearChat();
      break;
    case 'reset':
      handleReset();
      break;
    case 'help':
      showHelp();
      break;
  }
};

const handleClearChat = () => {
  ElMessageBox.confirm(
    '确定要清空当前所有对话内容吗？此操作不可恢复。',
    '清空对话',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  )
    .then(() => {
      emit('clear-chat');
    })
    .catch(() => {});
};

const handleReset = () => {
  ElMessageBox.confirm(
    '确定要重置界面状态吗？这将中断当前正在进行的请求。',
    '重置界面',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  )
    .then(() => {
      emit('emergency-reset');
    })
    .catch(() => {});
};

const showHelp = () => {
  ElMessageBox.alert(
    `
    <p><strong>基本操作</strong></p>
    <ul>
      <li>按 <kbd>Enter</kbd> 发送消息</li>
      <li>按 <kbd>Shift</kbd> + <kbd>Enter</kbd> 输入换行符</li>
      <li>点击历史记录按钮查看之前的对话</li>
    </ul>
    <p><strong>提示</strong></p>
    <ul>
      <li>长消息可以通过展开按钮查看完整内容</li>
      <li>可以通过"清空对话"来开始新的对话</li>
      <li>如果生成卡住，可以通过"重置界面"来恢复</li>
    </ul>
    `,
    '使用帮助',
    {
      dangerouslyUseHTMLString: true,
      confirmButtonText: '了解了'
    }
  );
};
</script>

<style lang="scss" scoped>
.chat-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 20px;
  background: var(--el-bg-color);
  border-bottom: 1px solid var(--el-border-color-light);
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  z-index: 10;
  
  .header-left {
    display: flex;
    align-items: center;
    gap: 16px;
    
    .logo-container {
      .app-logo {
        font-size: 16px;
        font-weight: 600;
        color: var(--el-color-primary);
        display: flex;
        align-items: center;
        gap: 6px;
      }
    }
    
    .model-selector {
      .model-tag {
        font-size: 13px;
      }
    }
    
    .model-info {
      .provider-name {
        font-size: 13px;
        font-weight: 600;
        color: var(--el-color-primary);
      }
      .model-name {
        font-size: 13px;
        color: var(--el-color-primary);
      }
    }
  }
  
  .header-actions {
    display: flex;
    align-items: center;
    gap: 12px;
    
    .action-button {
      &.history-button {
        min-width: 88px;
      }
    }
  }
}

// 响应式设计
@media (max-width: 640px) {
  .chat-header {
    padding: 12px 16px;
    
    .header-left {
      .logo-container {
        .app-logo {
          font-size: 15px;
        }
      }
    }
    
    .header-actions {
      .action-button {
        span {
          display: none;
        }
        
        &.history-button {
          min-width: unset;
        }
      }
    }
  }
}
</style>
