<!-- eslint-disable no-unused-vars -->
<template>
  <div class="chat-content">
    <div class="chat-messages-container">
      <!-- 空状态 -->
      <el-empty 
        v-if="messages.length === 0"
        description="开始聊天吧！"
        :image-size="80"
      />
      
      <!-- 消息列表区域 - 使用外部滚动条 -->
      <div class="messages-wrapper custom-scrollbar" @scroll="handleScroll">
        <div 
          v-for="(message, index) in visibleMessages" 
          :key="index" 
          :class="['message', message.role, { 'is-error': message.isError }]"
        >
          <div class="message-header">
            <strong>{{ message.role === 'user' ? '用户' : '助手' }}</strong>
            <div class="header-actions">
              <span class="message-time" v-if="message.timestamp">
                {{ formatTime(message.timestamp) }}
              </span>
              <el-button 
                v-if="message.role === 'assistant'" 
                type="info" 
                size="small" 
                circle 
                class="copy-btn"
                @click.stop="copyMessageContent(message)"
                :icon="CopyDocument"
                title="复制消息内容(已清理)"
              ></el-button>
              <el-button 
                v-if="message.role === 'assistant'" 
                type="warning" 
                size="small" 
                circle 
                class="raw-btn"
                @click.stop="$emit('toggle-raw', index)"
                :icon="Document"
                title="查看原始内容"
              ></el-button>
              <!-- 添加展开按钮 -->
              <el-button
                v-if="message.role === 'assistant' && isMessageTruncated(message)"
                type="primary"
                size="small"
                circle
                @click="toggleMessageExpand(index)"
                :icon="message.isExpanded ? Minus : Plus"
                title="展开/收起完整内容"
              ></el-button>
            </div>
          </div>
          
          <!-- 普通（非流式）消息内容 -->
          <template v-if="!message.isStreaming">
            <!-- 错误消息 -->
            <div v-if="message.isError" class="error-message">
              <el-alert type="error" :closable="false" show-icon>
                {{ message.content || '发生错误，请重试' }}
              </el-alert>
            </div>
            
            <!-- 普通消息渲染 -->
            <template v-else>
              <!-- 思考内容 -->
              <div 
                v-if="getThinkingContent(message.content).thinking" 
                class="thinking-content"
                :class="{ 'collapsed': localThinkingCollapsed[message.id] }"
              >
                <div class="thinking-header" @click="toggleThinking(message)">
                  <el-icon><MoreFilled /></el-icon>
                  <span>思考过程</span>
                  <span v-if="messageMeta[message.id] && typeof messageMeta[message.id].thinkingDuration === 'number'" class="thinking-duration">
                    (耗时: {{ messageMeta[message.id].thinkingDuration }}s)
                  </span>
                  <el-icon style="margin-left: auto">
                    <ArrowDown v-if="!localThinkingCollapsed[message.id]" />
                    <ArrowRight v-else />
                  </el-icon>
                </div>
                <div 
                  class="thinking-body" 
                  :class="{ 'collapsed': localThinkingCollapsed[message.id] }"
                  v-html="renderMarkdown(getThinkingContent(message.content).thinking)"
                ></div>
              </div>
              
              <!-- 可见内容（主要回复） -->
              <div 
                class="message-content markdown-body"
                :class="{
                  'assistant-content': message.role === 'assistant',
                  'user-content': message.role === 'user',
                  'message-expanded': message.isExpanded,
                  'animate-fade-in': true
                }"
                v-html="renderMarkdown(getThinkingContent(message.content).visible)"
              ></div>

              <!-- Token Usage Info -->
              <div v-if="message.role === 'assistant' && !message.isStreaming && !isTyping && messageMeta[message.id] && messageMeta[message.id].tokens" class="token-usage-info">
                <el-icon size="small"><PriceTag /></el-icon> 
                <span>
                  Tokens: {{ messageMeta[message.id].tokens.total }}
                  (输入: {{ messageMeta[message.id].tokens.prompt }}, 输出: {{ messageMeta[message.id].tokens.completion }})
                </span>
              </div>
              
              <div 
                v-if="false"
                class="message-expand-indicator"
                @click="toggleMessageExpand(index)"
              >
                <span>内容过长，点击展开完整内容 <el-icon><ArrowDown /></el-icon></span>
              </div>
            </template>
          </template>
          
          <!-- 处理流式消息，但只有当isStreaming为true且isProcessing为true时才渲染 -->
          <template v-else-if="message.isStreaming && isProcessing">
            <!-- 流式内容渲染使用currentStreamContent -->
            <div class="streaming-message-content">
              <!-- 流式分离渲染：思考内容和正文实时分离 -->
              <div class="streaming-content-wrapper">
                <!-- 思考内容在上方 -->
                <div v-if="parseThinkingContent(cleanStreamData(streamBuffer)).thinking" class="thinking-content streaming-thinking">
                  <div class="thinking-header" @click="toggleStreamingThinking">
                    <el-icon><MoreFilled /></el-icon>
                    <span>思考过程（生成中...）</span>
                    <el-icon style="margin-left: auto">
                      <ArrowDown v-if="!streamingThinkingCollapsed" />
                      <ArrowRight v-else />
                    </el-icon>
                  </div>
                  <div class="thinking-body" :class="{ 'collapsed': streamingThinkingCollapsed }" v-html="renderMarkdown(parseThinkingContent(cleanStreamData(streamBuffer)).thinking)"></div>
                </div>
                <!-- 正文内容在下方 -->
                <div class="message-content assistant-content markdown-body streaming-content"
                      :class="{'streaming-animate': isProcessing, 'animate-fade-in': true}"
                      v-html="renderMarkdown(parseThinkingContent(cleanStreamData(streamBuffer)).visible)"></div>
                <span ref="streamingTextSpanRef" class="streaming-text-span"></span>
                <span v-if="isTyping" class="typing-cursor"></span>
                <span v-if="!streamBuffer && !isTyping" class="placeholder-text">...</span>
              </div>
            </div>
          </template>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
/* eslint-disable no-unused-vars */
import { ref, defineExpose, watch, onMounted, computed, nextTick } from 'vue';
import { 
  CopyDocument, 
  MoreFilled, 
  Document,
  ArrowDown,
  ArrowRight,
  Plus,
  Minus,
  PriceTag
} from '@element-plus/icons-vue';
import { renderMarkdown, formatTimestamp, parseThinkingContent, cleanStreamData } from '../../../utils/thinkingUtils';
// eslint-disable-next-line no-unused-vars
import { getEmoji } from '../../../assets/emojiMap';
import { ElMessage } from 'element-plus';

const props = defineProps({
  messages: { type: Array, default: () => [] },
  visibleMessages: { type: Array, default: () => [] },
  isProcessing: { type: Boolean, default: false },
  streamBuffer: { type: String, default: '' },
  isTyping: { type: Boolean, default: false },
  isNearBottom: { type: Boolean, default: true },
  thinkingCollapsed: { type: Object, default: () => ({}) },
  loadingMessage: { type: String, default: '' },
  messageMeta: { type: Object, default: () => ({}) }
});

const emit = defineEmits([
  'scroll', 
  'toggle-raw', 
  'toggle-thinking', 
  'copy-message', 
  'scroll-to-bottom',
  'toggle-expand'
]);

// refs
const messagesContainerRef = ref(null);
const streamingTextSpanRef = ref(null);

// 动态窗口状态
const isExpanded = ref(false);
const thinkingProgress = ref(0);
const thinkingStep = ref(0);
const displayTokens = ref([]);
// 创建本地思考折叠状态副本，而不是直接修改props
const localThinkingCollapsed = ref({...props.thinkingCollapsed});
// 流式思考内容的折叠状态 - 默认折叠
const streamingThinkingCollapsed = ref(true);

// 监听props.thinkingCollapsed变化，更新本地状态
watch(() => props.thinkingCollapsed, (newVal) => {
  localThinkingCollapsed.value = {...newVal};
}, {deep: true});

// 默认情况下折叠所有思考过程
watch(() => props.messages.length, (newVal) => {
  // 当消息数量发生变化时，确保所有消息的思考过程都是折叠的
  for (let i = 0; i < newVal; i++) {
    if (!Object.prototype.hasOwnProperty.call(localThinkingCollapsed.value, i)) {
      // 默认折叠所有消息的思考内容
      localThinkingCollapsed.value[i] = true;
    }
  }
});

// 强制所有新增消息的思考内容默认折叠
watch(() => props.visibleMessages, (newVal) => {
  if (newVal && newVal.length > 0) {
    nextTick(() => {
      for (let i = 0; i < newVal.length; i++) {
        if (newVal[i].role === 'assistant' && getThinkingContent(newVal[i].content).thinking) {
          if (typeof localThinkingCollapsed.value[i] === 'undefined') {
            localThinkingCollapsed.value[i] = true;
          }
        }
      }
    });
  }
}, { deep: true, immediate: true });

// 当消息处理完成时自动折叠思考过程
watch(() => props.isProcessing, (newVal, oldVal) => {
  if (oldVal && !newVal) {
    // 当消息处理从正在进行变为完成时
    const lastIndex = props.messages.length - 1;
    if (lastIndex >= 0) {
      nextTick(() => {
        localThinkingCollapsed.value[lastIndex] = true;
      });
    }
  }
});

// 模拟思考过程
const simulateThinking = () => {
  if (!props.isProcessing) {
    resetThinking();
    return;
  }
  
  const maxProgress = 95; // 保留余量，等待最终结果
  const progressInterval = setInterval(() => {
    if (!props.isProcessing) {
      clearInterval(progressInterval);
      thinkingProgress.value = 100;
      thinkingStep.value = 4;
      return;
    }
    
    // 进度增加（随机性）
    if (thinkingProgress.value < maxProgress) {
      thinkingProgress.value += Math.random() * 2;
    }
    
    // 思考阶段进展
    if (thinkingProgress.value > 20 && thinkingStep.value < 1) {
      thinkingStep.value = 1;
    } else if (thinkingProgress.value > 40 && thinkingStep.value < 2) {
      thinkingStep.value = 2;
    } else if (thinkingProgress.value > 65 && thinkingStep.value < 3) {
      thinkingStep.value = 3;
    } else if (thinkingProgress.value >= 95 && thinkingStep.value < 4) {
      thinkingStep.value = 4;
    }
  }, 300);
  
  return progressInterval;
};

// 重置思考状态
const resetThinking = () => {
  thinkingProgress.value = 0;
  thinkingStep.value = 0;
  displayTokens.value = [];
};

// 模拟显示token生成
const updateDisplayTokens = () => {
  if (!props.streamBuffer || props.streamBuffer.length === 0) {
    displayTokens.value = [];
    return;
  }
  
  // 简单拆分成词或字符
  const tokens = props.streamBuffer.split(/(\s+|[,.!?;:|])/g).filter(t => t);
  // 只显示最新的几个token
  displayTokens.value = tokens.slice(-15);
};

// eslint-disable-next-line no-unused-vars
// 切换扩展窗口
const toggleExpand = () => {
  isExpanded.value = !isExpanded.value;
};

// 格式化时间戳
const formatTime = (timestamp) => {
  return formatTimestamp(timestamp);
};

// 对原始内容进行格式化，主要用于查看原始内容时
const formatRawContent = (content) => {
  if (!content) return '';
  
  try {
    // 尝试解析为JSON并美化
    if (content.trim().startsWith('{') || content.trim().startsWith('[')) {
      const obj = JSON.parse(content);
      return JSON.stringify(obj, null, 2);
    }
  } catch (e) {
    // 解析失败，进行常规清理
    console.log('JSON解析失败，使用标准清理');
  }
  
  return cleanStreamData(content);
};

// 获取思考内容和可见内容
const getThinkingContent = (content) => {
  if (!content) return { thinking: '', visible: '' };
  
  // 先清理内容再解析思考标签
  const cleanedContent = cleanStreamData(content);
  return parseThinkingContent(cleanedContent);
};

// 监听处理状态
watch(() => props.isProcessing, (newVal) => {
  if (newVal) {
    // 开始处理时初始化动画
    resetThinking();
    simulateThinking();
  } else {
    // 结束处理时完成进度
    thinkingProgress.value = 100;
    thinkingStep.value = 4;
  }
});

// 监听流内容更新token显示
watch(() => props.streamBuffer, () => {
  updateDisplayTokens();
});

// 检查消息是否被截断（过长需要展开）
const isMessageTruncated = (message) => {
  // 如果消息已被标记为展开，不需要再检查
  if (message.isExpanded) return true;
  
  // 检查内容长度，超过1500字符视为长消息
  const content = message.content || '';
  return content.length > 1500 || content.split('\n').length > 25;
};

// 切换消息展开状态
const toggleMessageExpand = (index) => {
  const message = props.messages[index];
  if (!message) return;
  
  // 触发事件给父组件处理状态变更
  emit('toggle-expand', index);
};

// 切换流式思考内容的折叠状态
const toggleStreamingThinking = () => {
  streamingThinkingCollapsed.value = !streamingThinkingCollapsed.value;
};

// 获取消息内容（用于复制）
const getMessageContent = (message) => {
  // 如果消息内容为空，返回空字符串
  if (!message || !message.content) return '';
  
  // 如果是流式生成中的消息，从流缓冲区获取
  if (message.isStreaming && props.streamBuffer) {
    // 先清理流数据中的控制信息
    return cleanStreamData(props.streamBuffer);
  }
  
  // 普通消息也要清理一次内容
  return cleanStreamData(message.content);
};

// 复制消息内容
const copyMessageContent = (message) => {
  const content = getMessageContent(message);
  
  // 复制到剪贴板
  navigator.clipboard.writeText(content)
    .then(() => {
      ElMessage.success('已复制到剪贴板');
    })
    .catch(err => {
      console.error('复制失败:', err);
      ElMessage.error('复制失败');
    });
  
  // 触发复制事件
  emit('copy-message', content);
};

// 方法暴露
defineExpose({
  scrollToBottom: (force = false) => {
    // 滚动操作现在交由父组件处理
    emit('scroll-to-bottom', force);
  },
  $el: computed(() => messagesContainerRef.value),
  getStreamingSpan: () => streamingTextSpanRef.value
});

// 组件挂载时初始化
onMounted(() => {
  if (props.isProcessing) {
    simulateThinking();
  }
});

// 切换消息的思考内容折叠状态
const toggleThinking = (message) => {
  if (!message.id) return;
  localThinkingCollapsed.value[message.id] = !localThinkingCollapsed.value[message.id];
};
</script>

<style lang="scss" scoped>
// 只导入标准样式路径的文件
@import '../styles/chat-base.scss';
@import '../styles/chat-message.scss';

// 组件特定的覆盖样式
.chat-content {
  position: relative;
  flex: 1;
  display: flex;
  flex-direction: column;
  width: 100%;
  min-width: 500px; // 设置最小宽度，避免内容过度挤压
}

.chat-messages-container {
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
  width: 100%; 
  box-sizing: border-box;
  
  // 为避免第一条消息顶到最上面，添加顶部间距
  &:before {
    content: '';
    display: block;
    height: 8px;
  }
  
  // 为避免最后一条消息贴到底部，添加底部间距
  &:after {
    content: '';
    display: block;
    height: 16px;
  }
}

// 添加淡入动画效果
.animate-fade-in {
  animation: fadeIn 0.4s ease-in-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

// 添加代码内容样式优化
.message {
  max-width: 100%;
  box-sizing: border-box;
  width: 100%;
  
  .message-header {
    padding: 8px 12px;
    font-size: 14px;
    
    .header-actions {
      .message-time {
        font-size: 12px;
      }
    }
  }
  
  pre {
    overflow-x: auto;
    white-space: pre;
    background-color: var(--el-fill-color-light);
    padding: 10px;
    border-radius: 5px;
    margin: 8px 0;
    position: relative;
    max-width: 100%;
  }
  
  code {
    font-family: 'Menlo', 'Monaco', 'Courier New', monospace;
    font-size: 0.9em;
  }
  
  .raw-content {
    overflow-x: auto;
    width: 100%;
    box-sizing: border-box;
    
    pre {
      max-width: 100%;
      overflow-x: auto;
      white-space: pre;
      font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
      font-size: 12px;
      line-height: 1.4;
      background-color: var(--el-color-info-light-9);
      padding: 12px;
      border-radius: 6px;
      margin: 0;
      
      // 为水平滚动条添加样式
      &::-webkit-scrollbar {
        height: 6px;
        background-color: transparent;
      }
      
      &::-webkit-scrollbar-thumb {
        background-color: rgba(0, 0, 0, 0.2);
        border-radius: 3px;
        
        &:hover {
          background-color: rgba(0, 0, 0, 0.3);
        }
      }
    }
  }
}

// 消息内容展开样式
.message-content {
  width: 100%;
  overflow-x: auto; 
  max-width: 100%;
  box-sizing: border-box;
  position: relative;
  word-break: break-word;
  
  &.message-expanded {
    max-height: none !important;
  }
  
  &:not(.message-expanded) {
    max-height: none;
  }
  
  // 优化表格样式，防止溢出
  :deep(table) {
    display: block;
    width: 100%;
    overflow-x: auto;
    border-collapse: collapse;
  }
  
  // 优化图片样式，防止溢出
  :deep(img) {
    max-width: 100%;
    height: auto;
  }
}

// 优化助手和用户消息的样式差异
.assistant-content {
  background-color: var(--el-color-info-light-9);
  border-radius: 6px;
  padding: 10px 14px;
}

.user-content {
  background-color: var(--el-color-primary-light-9);
  border-radius: 6px;
  padding: 10px 14px;
}

// 添加深色模式特定样式
:deep(.dark) {
  .assistant-content {
    background-color: rgba(80, 80, 80, 0.3);
  }
  
  .user-content {
    background-color: rgba(64, 158, 255, 0.1);
  }
}

.streaming-animate {
  animation: contentFadeIn 0.5s cubic-bezier(0.23, 1, 0.32, 1);
}
@keyframes contentFadeIn {
  0% {
    opacity: 0.3;
    transform: translateY(12px) scale(0.98);
  }
  100% {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.streaming-message-content {
  width: 100%;
  position: relative;
}

.streaming-content-wrapper {
  display: flex;
  flex-direction: column;
  width: 100%;
}

.thinking-content.streaming-thinking {
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  margin-bottom: 16px; /* Add margin to separate thinking from main content */
  overflow: hidden;
  background-color: var(--el-color-info-light-9);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.thinking-header {
  display: flex;
  align-items: center;
  padding: 8px 12px;
  background-color: var(--el-color-info-light-8);
  border-bottom: 1px solid var(--el-border-color-light);
  cursor: pointer;
  user-select: none;
  font-size: 13px;
  font-weight: 600;
  color: var(--el-text-color-secondary);
}

.thinking-body {
  padding: 12px;
  max-height: 300px;
  overflow-y: auto;
  transition: all 0.3s;
  font-size: 14px;
  color: var(--el-text-color-secondary);
}

.thinking-body.collapsed {
  max-height: 0;
  padding: 0;
  overflow: hidden;
}

// 添加样式 for thinking-duration
.thinking-duration {
  font-size: 0.8em;
  color: var(--el-text-color-secondary);
  margin-left: 8px;
}

// 新 style for token usage info
.token-usage-info {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 11px;
  color: var(--el-text-color-secondary);
  margin-top: 10px;
  padding: 4px 16px 8px 28px; // Match content padding somewhat
  opacity: 0.8;
}

// .messages-wrapper {
//   // ... existing code ...
// }
</style>
