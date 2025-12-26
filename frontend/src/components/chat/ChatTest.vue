<template>
  <div class="chat-main-container">
    <!-- 头部组件 -->
    <ChatHeader 
      :provider="selectedProvider"
      :model="selectedModel"
      :is-processing="isProcessing"
      :loading-history="loadingChatLogs"
      @load-history="loadChatLogs"
      @clear-chat="clearChat"
      @emergency-reset="emergencyReset"
    />
    
    <!-- 进度条组件 -->
    <ChatProgress 
      v-if="isLoading || isProcessing"
      :progress="loadingProgress"
      :message="loadingMessage"
    />
    
    <!-- 消息列表区域 - 使用外部滚动条 -->
    <div class="messages-wrapper custom-scrollbar" ref="messagesWrapperRef" @scroll="handleScroll">
      <ChatMessages
        :messages="chatMessages"
        :visible-messages="visibleMessages"
        :is-processing="isProcessing"
        :stream-buffer="streamBuffer"
        :is-typing="isTyping"
        :is-near-bottom="isNearBottom"
        :thinking-collapsed="thinkingCollapsed"
        :message-meta="messageMeta"
        ref="chatMessagesRef"
        @toggle-raw="toggleRawView"
        @toggle-thinking="toggleThinking"
        @toggle-expand="toggleMessageExpand"
        @copy-message="copyMessage"
        @scroll-to-bottom="scrollToBottom"
      />
      
      <!-- 滚动到底部按钮 -->
      <div v-if="!isNearBottom" class="scroll-to-bottom-btn" @click="scrollToBottom(true)">
        <el-button type="primary" circle size="small" :icon="ArrowDown" title="滚动到底部"></el-button>
      </div>
    </div>
    
    <!-- 输入组件 -->
    <ChatInput
      v-model="chatInput"
      :is-processing="isProcessing"
      :is-composing="isComposing"
      :selected-provider="selectedProvider"
      :selected-model="selectedModel"
      @send="sendChatMessage"
      @insert-newline="insertNewline"
      ref="chatInputRef"
    />
    
    <!-- 历史记录对话框 -->
    <ChatHistoryDialog
      v-model="chatLogsDialogVisible"
      :loading="loadingChatLogs"
      :chat-logs="chatLogs"
      @load-detail="handleLoadChatDetail"
    />
  </div>
</template>

<script setup>
import { ref, onMounted, computed, onUnmounted, nextTick, defineExpose, watch } from 'vue';
import { ElMessage } from 'element-plus';
import { ArrowDown } from '@element-plus/icons-vue';
import api from '../../services/api';
import { parseThinkingContent, cleanStreamData } from '../../utils/thinkingUtils';
// 直接引入需要的函数
import { streamChat } from '../../services/chatService';

// 导入子组件
import ChatHeader from './components/ChatHeader.vue';
import ChatProgress from './components/ChatProgress.vue';
import ChatMessages from './components/ChatMessages.vue';
import ChatInput from './components/ChatInput.vue';
import ChatHistoryDialog from './components/ChatHistoryDialog.vue';

// 导入可复用逻辑
import { useTypewriter } from './composables/useTypewriter';
import { useStreamHandling } from './composables/useStreamHandling';
import { useChatHistory } from './composables/useChatHistory';

// Props
const props = defineProps({
  selectedProvider: { type: String, default: '' },
  selectedModel: { type: String, default: '' },
  isDarkMode: { type: Boolean, default: false }
});

// Emits
const emit = defineEmits(['update-chat-context', 'chat-ready', 'chat-state-change']);

// 使用组合式函数
const { 
  typewriterQueue, 
  isTyping,
  startTypewriter,
  stopTypewriter 
} = useTypewriter();

const {
  streamBuffer,
  isStreamFinished,
  isStreaming,
  currentMessageIndex,
  currentStreamContent,
  handleStreamMessage,
  resetStreamState,
  // 注释掉未使用的函数
  // handleStreamError,
  // handleStreamFatalError,
} = useStreamHandling();

const {
  chatLogs,
  loadingChatLogs,
  chatLogsDialogVisible,
  loadChatLogs,
  loadChatDetail,
} = useChatHistory();

// 滚动逻辑简化
const isNearBottom = ref(true);
const messagesWrapperRef = ref(null);

const handleScroll = (event) => {
  const container = event.target;
  if (container) {
    const { scrollTop, scrollHeight, clientHeight } = container;
    const threshold = 150; // 距离底部150px内认为接近底部
    isNearBottom.value = scrollHeight - scrollTop - clientHeight < threshold;
  }
};

const scrollToBottom = (force = false) => {
  const container = messagesWrapperRef.value;
  if (!container) return;
  
  // 只有在强制滚动或用户已在底部时才执行滚动
  if (force || isNearBottom.value) {
    nextTick(() => {
      try {
        setTimeout(() => {
          container.scrollTop = container.scrollHeight;
        }, 10);
      } catch (e) {
        console.error('滚动到底部失败:', e);
      }
    });
  }
};

// 核心状态
const chatMessages = ref([]);
const chatInput = ref('');
const isProcessing = ref(false);
const isComposing = ref(false);
const isLoading = ref(false);
const loadingProgress = ref(0);
const loadingMessage = ref('正在加载...');
const thinkingCollapsed = ref({});
const messageMeta = ref({});
const currentAssistantTokens = ref(null);

// 组件引用
const chatMessagesRef = ref(null);
const chatInputRef = ref(null);

// 请求取消控制器
let abortController = null;

// 计算属性
const visibleMessages = computed(() => {
  if (chatMessages.value.length <= 20) {
    return chatMessages.value;
  }
  return chatMessages.value.slice(-20);
});

// 监听typewriterQueue变化，触发打字机效果
watch(typewriterQueue, (newVal) => {
  if (newVal && chatMessagesRef.value) {
    const streamingSpan = chatMessagesRef.value.getStreamingSpan();
    if (streamingSpan) {
      startTypewriter(streamingSpan);
    }
  }
});

// 监听消息变化，只有在 isNearBottom 时才自动滚动
watch(chatMessages, () => {
  if (isNearBottom.value) {
    nextTick(() => {
      scrollToBottom();
    });
  }
});

// 方法
// 加载动画控制
const startLoading = (message = '正在加载...') => {
  isLoading.value = true;
  loadingProgress.value = 0;
  loadingMessage.value = message;
};

const stopLoading = () => {
  isLoading.value = false;
  loadingProgress.value = 0;
  loadingMessage.value = '';
};

// 发送消息
const sendChatMessage = async () => {
  if (!chatInput.value || isProcessing.value) return;
  
  // 检查所选提供商和模型
  if (!props.selectedProvider || !props.selectedModel) {
    ElMessage.warning('请先选择提供商和模型');
    return;
  }
  
  try {
    // 清理前一次请求状态
    clearPreviousRequest();
    
    // 获取并格式化用户输入
    const userMessage = chatInput.value.trim();
    chatInput.value = ''; // 清空输入框
    
    // 创建新的中止控制器
    abortController = new AbortController();
    
    // 准备请求参数
    const requestParams = {
      provider: props.selectedProvider,
      model: props.selectedModel,
      messages: getFinalMessagesList(userMessage),
      timestamp: Date.now(),
      stream: true
    };
    
    // 更新状态为处理中
    isProcessing.value = true;
    isStreamFinished.value = false;
    
    // 添加用户消息
    addChatMessage({
      role: 'user',
      content: userMessage,
      timestamp: Date.now()
    });
    
    // 创建助手消息占位符
    const assistantMessageIndex = chatMessages.value.length;
    let thinkingStartTime = Date.now(); // 记录思考开始时间
    let contentGenerationStartTime = null; // 标记内容生成开始时间
    let responseReady = false;
    
    // 添加助手消息（初始为空）
    addChatMessage({
      role: 'assistant',
      content: '',
      isStreaming: true,
      isThinking: true, // 新增标记，初始为思考阶段
      timestamp: Date.now(),
      id: Date.now().toString() // 添加唯一ID用于折叠思考内容
    });
    
    // 设置当前消息索引
    currentMessageIndex.value = assistantMessageIndex;
    
    // 开始发送请求，使用流式处理
    streamBuffer.value = '';
    startLoading('生成回复中...');
    
    // 创建异步请求
    try {
      await streamChat(
        requestParams,
        {
          signal: abortController.signal,
          
          // 处理数据块
          onMessage: (chunkData) => {
            if (!responseReady) {
              // 检查是否包含非思考内容（实际回复内容）
              const parsedChunk = parseThinkingContent(chunkData);
              
              // 检测是否从思考阶段转换到内容生成阶段
              if (!contentGenerationStartTime && parsedChunk.visible && parsedChunk.visible.trim()) {
                // 找到第一个实际内容的时间点，标记为内容生成开始时间
                contentGenerationStartTime = Date.now();
                
                // 计算思考阶段持续时间（秒）
                const thinkingDuration = Math.round((contentGenerationStartTime - thinkingStartTime) / 1000);
                
                // 更新助手消息，添加思考时间
                const currentAssistantMessage = chatMessages.value[assistantMessageIndex];
                if (currentAssistantMessage) {
                  currentAssistantMessage.thinkingDuration = thinkingDuration;
                  currentAssistantMessage.isThinking = false; // 标记思考阶段结束
                  
                  // 新增：自动折叠思考过程
                  thinkingCollapsed.value[currentAssistantMessage.id] = true;
                  
                  // 新增：存储思考时长到 messageMeta
                  if (messageMeta.value[currentAssistantMessage.id]) {
                    messageMeta.value[currentAssistantMessage.id].thinkingDuration = thinkingDuration;
                  } else {
                    messageMeta.value[currentAssistantMessage.id] = { thinkingDuration };
                  }
                }
              }
            }
            
            // 处理流数据
            const result = handleStreamMessage(
              chunkData, 
              typewriterQueue,
              (fullContent) => {
                // 内容更新回调
                updateAssistantResponse(assistantMessageIndex, fullContent); 
              },
              // 添加超时处理函数
              () => {
                console.warn('流处理超时，执行紧急恢复');
                const currentMessage = chatMessages.value[assistantMessageIndex];
                if (currentMessage) {
                  // 停止streaming状态
                  currentMessage.isStreaming = false;
                  // 确保保存已收到的内容
                  currentMessage.content = streamBuffer.value || currentStreamContent.value || "回复生成超时";
                  // 添加提示
                  currentMessage.content += "\n\n[响应超时，内容可能不完整]";
                }
                // 重置流状态
                stopTypewriter();
                resetStreamState();
                isLoading.value = false;
                isProcessing.value = false;
              }
            );
            
            if (result && result.success) {
              // 更新loadingMessage
              if (contentGenerationStartTime) {
                const contentDuration = Math.round((Date.now() - contentGenerationStartTime) / 1000);
                loadingMessage.value = `思考: ${Math.round((contentGenerationStartTime - thinkingStartTime) / 1000)}秒 | 生成: ${contentDuration}秒`;
              } else {
                loadingMessage.value = `思考: ${Math.round((Date.now() - thinkingStartTime) / 1000)}秒...`;
              }
              
              // 处理完成后滚动到底部
              smoothScrollToBottom();
            }
          },
          
          // 处理流完成
          onFinish: (stats) => {
            console.log('Stream finished. Received stats:', stats);
            stopTypewriter();
            
            // Update token stats if received
            if (stats && typeof stats.prompt === 'number' && typeof stats.completion === 'number') {
              currentAssistantTokens.value = stats; // Store the received stats
              // Add stats to the specific assistant message's meta
              if (assistantMessageIndex >= 0 && assistantMessageIndex < chatMessages.value.length) {
                const assistantMessage = chatMessages.value[assistantMessageIndex];
                if (messageMeta.value[assistantMessage.id]) {
                  messageMeta.value[assistantMessage.id].tokens = currentAssistantTokens.value;
                } else {
                  messageMeta.value[assistantMessage.id] = { tokens: currentAssistantTokens.value };
                }
                console.log(`Token stats for message ${assistantMessage.id} stored in messageMeta.`);
              }
            } else {
              currentAssistantTokens.value = null; // Reset if no stats received
            }
            
            // Update message state
            if (assistantMessageIndex >= 0 && assistantMessageIndex < chatMessages.value.length) {
              chatMessages.value[assistantMessageIndex].isStreaming = false;
            }
            
            // 重置状态
            resetStreamState();
            stopLoading();
            isProcessing.value = false;
            
            // 更新聊天上下文（可选）
            // updateChatContext();
            
            // 延迟保存聊天记录
            setTimeout(() => saveChatSession(), 500);
          },
          
          // 处理错误
          onError: (error) => {
            console.error('流处理错误:', error);
            
            // 更新消息状态，添加错误提示
            if (assistantMessageIndex >= 0 && assistantMessageIndex < chatMessages.value.length) {
              const errorMessage = chatMessages.value[assistantMessageIndex];
              errorMessage.isStreaming = false;
              errorMessage.hasError = true;
              // 如果已经有一些内容，保留它并添加错误消息
              if (errorMessage.content) {
                errorMessage.content += '\n\n[发生错误: ' + (error.message || '未知错误') + ']';
              } else {
                errorMessage.content = '生成回复时发生错误: ' + (error.message || '未知错误');
              }
            }
            
            // 重置状态
            stopTypewriter();
            resetStreamState();
            stopLoading();
            isProcessing.value = false;
          },
          
          // 处理致命错误
          onFatalError: (error) => {
            console.error('致命错误:', error);
            ElMessage.error(`发生错误: ${error.message || '未知错误'}`);
            
            // 移除助手消息（可选）或保留错误提示
            if (assistantMessageIndex >= 0 && assistantMessageIndex < chatMessages.value.length) {
              const errorMessage = chatMessages.value[assistantMessageIndex];
              errorMessage.isStreaming = false;
              errorMessage.hasError = true;
              errorMessage.content = '无法生成回复: ' + (error.message || '服务器错误');
            }
            
            // 重置状态
            stopTypewriter();
            resetStreamState();
            stopLoading();
            isProcessing.value = false;
          }
        }
      );
    } catch (error) {
      console.error('发送请求失败:', error);
      ElMessage.error(`请求错误: ${error.message || '未知错误'}`);
      
      // 更新错误消息
      if (assistantMessageIndex >= 0 && assistantMessageIndex < chatMessages.value.length) {
        const errorMessage = chatMessages.value[assistantMessageIndex];
        errorMessage.isStreaming = false;
        errorMessage.hasError = true;
        errorMessage.content = '请求失败: ' + (error.message || '未知错误');
      }
      
      // 重置状态
      stopTypewriter();
      resetStreamState();
      stopLoading();
      isProcessing.value = false;
    }
  } catch (error) {
    console.error('发送消息时出错:', error);
    ElMessage.error('发送消息失败: ' + (error.message || String(error)));
    isProcessing.value = false;
    stopLoading();
  }
};

// 聊天操作
const clearChat = () => {
  // 如果有内容，先尝试保存
  if (chatMessages.value.length > 1) {
    saveChatSession();
  }
  
  // 清理状态
  if (abortController) { 
    abortController.abort(); 
    abortController = null; 
  }
  
  chatMessages.value = [];
  streamBuffer.value = '';
  isProcessing.value = false;
  isStreamFinished.value = false;
  isStreaming.value = false;
  currentMessageIndex.value = -1;
  
  // 清理打字机状态
  typewriterQueue.value = '';
  stopTypewriter();
  
  ElMessage.info('聊天记录已清空');
};

const copyMessage = (content) => {
  // 获取要复制的文本内容
  let textToCopy = '';
  
  // 检查content是否是字符串
  if (typeof content === 'string') {
    // 清理内容
    const cleanedContent = cleanStreamData(content);
    // 提取可见内容（排除思考过程标签）
    const { visible } = parseThinkingContent(cleanedContent);
    textToCopy = visible.trim();
  } else {
    // 不是字符串则转为JSON
    textToCopy = JSON.stringify(content);
  }
  
  // 复制到剪贴板
  navigator.clipboard.writeText(textToCopy)
    .then(() => {
      ElMessage.success('内容已复制到剪贴板');
    })
    .catch(err => {
      console.error('复制失败:', err);
      ElMessage.error('复制失败');
    });
};

const insertNewline = () => {
  const el = chatInputRef.value?.$refs.inputRef?.$refs.textarea;
  if (el) {
    const { selectionStart, selectionEnd, value } = el;
    const newValue = value.substring(0, selectionStart) + '\n' + value.substring(selectionEnd);
    chatInput.value = newValue;
    nextTick(() => {
       el.selectionStart = el.selectionEnd = selectionStart + 1;
    });
  }
};

const toggleRawView = (index) => {
  // 如果这条消息没有showRaw属性，添加一个默认值为false
  if (typeof chatMessages.value[index].showRaw === 'undefined') {
    chatMessages.value[index].showRaw = false;
  }
  
  // 切换状态
  chatMessages.value[index].showRaw = !chatMessages.value[index].showRaw;
};

const toggleThinking = (index) => {
  // 如果索引不存在或未初始化，初始化为true（折叠状态）
  if (typeof thinkingCollapsed.value[index] === 'undefined') {
    thinkingCollapsed.value[index] = true;
  } else {
    // 否则切换折叠状态
    thinkingCollapsed.value[index] = !thinkingCollapsed.value[index];
  }
};

const emergencyReset = () => {
  console.log('执行紧急重置');
  ElMessage.warning('执行紧急重置...');
  
  // 中止当前请求
  if (abortController) { 
    abortController.abort(); 
    abortController = null; 
  }
  
  // 重置状态
  isProcessing.value = false;
  isStreamFinished.value = true;
  isStreaming.value = false;
  isLoading.value = false;
  loadingProgress.value = 0;
  loadingMessage.value = '';
  
  // 尝试保存已接收到的内容
  if (currentMessageIndex.value >= 0 && currentMessageIndex.value < chatMessages.value.length) {
    const currentMessage = chatMessages.value[currentMessageIndex.value];
    // 更新消息内容
    currentMessage.content = streamBuffer.value || currentStreamContent.value || "消息生成被中断";
    currentMessage.isStreaming = false;
    currentMessage.isThinking = false;
    // 如果有部分内容，添加一个中断标记
    if (streamBuffer.value || currentStreamContent.value) {
      currentMessage.content += "\n\n[消息生成被中断]";
    }
  }
  
  // 重置打字机状态
  typewriterQueue.value = '';
  stopTypewriter();
  
  // 清空流式状态
  streamBuffer.value = '';
  currentStreamContent.value = '';
  currentMessageIndex.value = -1;
  
  // 强制一次DOM更新
  nextTick(() => {
    scrollToBottom(true);
    ElMessage.success('界面已重置，现在可以继续发送消息');
  });
};

// 通知状态变化
const notifyStateChange = () => {
  emit('chat-state-change', {
    isProcessing: isProcessing.value,
    messagesCount: chatMessages.value.length,
    provider: props.selectedProvider,
    model: props.selectedModel
  });
};

// 生命周期钩子
onMounted(() => {
  console.log('聊天组件已挂载');
  messagesWrapperRef.value = document.querySelector('.messages-wrapper');
  
  // 添加滚动事件监听
  if (messagesWrapperRef.value) {
    messagesWrapperRef.value.addEventListener('scroll', handleScroll);
  }
  
  setTimeout(() => {
    try { 
      chatInputRef.value?.focus(); 
      scrollToBottom();
    } catch (e) { 
      console.warn('聚焦输入框或滚动失败:', e); 
    }
    emit('chat-ready');
  }, 100);
});

onUnmounted(() => {
  console.log('聊天组件销毁');
  if (abortController) { 
    abortController.abort(); 
    abortController = null; 
  }
  
  // 移除滚动事件监听
  if (messagesWrapperRef.value) {
    messagesWrapperRef.value.removeEventListener('scroll', handleScroll);
  }
});

// 重置界面
const resetChatInterface = () => {
  console.log('重置聊天界面');
  if (abortController) { 
    abortController.abort(); 
    abortController = null; 
  }
  
  isStreamFinished.value = true; 
  isProcessing.value = false;
  isStreaming.value = false;
  streamBuffer.value = '';
  currentMessageIndex.value = -1;
  
  // 停止打字机效果
  stopTypewriter();
  
  nextTick(() => {
    chatInputRef.value?.focus();
  });
  
  notifyStateChange();
};

// 替换原有的loadChatDetail方法(如果存在)或添加新的方法
const handleLoadChatDetail = async (chatId) => {
  try {
    loadingChatLogs.value = true;
    ElMessage.info('正在加载聊天记录...');
    
    // 确保停止任何进行中的请求
    if (isProcessing.value) {
      if (abortController) {
        abortController.abort();
        abortController = null;
      }
      isProcessing.value = false;
      stopTypewriter();
    }
    
    // 加载聊天记录
    const chatData = await loadChatDetail(chatId);
    if (!chatData || !chatData.messages || !chatData.messages.length) {
      ElMessage.error('加载的聊天记录无效或为空');
      return;
    }
    
    // 设置提供商和模型（如果有效）
    if (chatData.provider && chatData.model) {
      emit('update-chat-context', {
        provider: chatData.provider,
        model: chatData.model
      });
    }
    
    // 清空当前消息并替换为加载的消息
    chatMessages.value = chatData.messages.map(msg => ({
      role: msg.role,
      content: msg.content,
      timestamp: msg.timestamp || new Date().toISOString(),
      isExpanded: false
    }));
    
    // 关闭对话框
    chatLogsDialogVisible.value = false;
    
    // 滚动到底部
    nextTick(() => {
      scrollToBottom();
      ElMessage.success('聊天记录加载成功');
    });
  } catch (error) {
    console.error('加载聊天记录失败:', error);
    ElMessage.error('加载聊天记录失败');
  } finally {
    loadingChatLogs.value = false;
  }
};

// 清理前一次请求的状态
const clearPreviousRequest = () => {
  if (abortController) {
    abortController.abort();
    abortController = null;
  }
  stopTypewriter();
  streamBuffer.value = '';
  isStreamFinished.value = true;
  isStreaming.value = false;
};

// 获取最终消息列表
const getFinalMessagesList = (userMessage) => {
  // 准备历史消息列表，只包含完成的消息
  const messageHistory = chatMessages.value.filter(msg => !msg.isStreaming).map(msg => ({
    role: msg.role,
    content: msg.content
  }));
  
  // 添加当前用户消息
  messageHistory.push({
    role: 'user',
    content: userMessage
  });
  
  return messageHistory;
};

// 添加聊天消息到列表
const addChatMessage = (message) => {
  chatMessages.value.push(message);
};

// 更新聊天上下文
// const updateChatContext = () => {
//   // 可选: 发送更新给父组件
//   emit('update-chat-context', {
//     provider: props.selectedProvider,
//     model: props.selectedModel,
//     messagesCount: chatMessages.value.length
//   });
// };

// 为ChatTest.vue添加缺失的函数定义
const updateAssistantResponse = (messageIndex, content) => {
  if (messageIndex >= 0 && messageIndex < chatMessages.value.length) {
    chatMessages.value[messageIndex].content = content;
  }
};

const smoothScrollToBottom = () => {
  if (isNearBottom.value) {
    scrollToBottom();
  }
};

// 保存聊天会话记录
const saveChatSession = async () => {
  if (chatMessages.value.length < 2) {
    console.log('聊天内容太少，不保存');
    return;
  }
  
  try {
    // 准备保存的消息数据，过滤掉流处理中的消息
    const messagesToSave = chatMessages.value
      .filter(msg => !msg.isStreaming)
      .map(msg => ({
        role: msg.role,
        content: cleanStreamData(msg.content), // 确保内容已清理
        timestamp: msg.timestamp
      }));
    
    // 创建聊天日志对象
    const chatLog = {
      provider: props.selectedProvider,
      model: props.selectedModel,
      messages: messagesToSave,
      timestamp: new Date().toISOString(), // 使用 ISO 字符串格式
      // title: generateChatTitle() // 暂时移除 title 字段进行测试
    };
    
    console.log('正在保存聊天记录...', chatLog);
    
    // 调用API保存聊天记录
    const response = await api.saveChatLog(chatLog);
    console.log('保存聊天记录成功:', response.data);
    
    // 刷新聊天历史记录列表（如果需要）
    if (chatLogsDialogVisible.value) {
      loadChatLogs();
    }
  } catch (error) {
    console.error('保存聊天记录失败:', error);
    ElMessage.warning('保存聊天记录失败，请稍后再试');
  }
};



// 切换消息的展开/收起状态
const toggleMessageExpand = (index) => {
  if (!chatMessages.value[index]) return;
  
  // 直接修改消息对象的展开状态
  chatMessages.value[index].isExpanded = !chatMessages.value[index].isExpanded;
  
  // 展开后更新DOM，保持滚动位置
  nextTick(() => {
    // 获取当前滚动位置
    const container = messagesWrapperRef.value;
    if (container) {
      const currentScroll = container.scrollTop;
      // 调整后恢复滚动位置
      setTimeout(() => {
        container.scrollTop = currentScroll;
      }, 10);
    }
  });
};

// 导出方法
defineExpose({
  resetChatInterface
});
</script>

<style lang="scss" scoped>
.chat-main-container {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 160px);
  min-height: 480px;
  max-height: 88vh;
  border-radius: 8px;
  border: 1px solid var(--el-border-color-light);
  background-color: var(--el-bg-color);
  overflow: hidden;
  box-shadow: 0 3px 16px rgba(0, 0, 0, 0.06);
  margin: 0 auto;
  max-width: 100%;
  width: 100%;
  position: relative;
  
  // 让聊天组件在深色模式下有边框
  :deep(html.dark) & {
    border-color: var(--el-border-color-darker);
    box-shadow: 0 3px 16px rgba(0, 0, 0, 0.12);
    background-color: var(--el-bg-color-overlay);
  }
  
  // 消息容器包装器，改为直接滚动而不是内部滚动
  .messages-wrapper {
    flex: 1;
    position: relative;
    overflow-y: auto;
    overflow-x: hidden;
    display: flex;
    flex-direction: column;
    background-color: var(--el-bg-color-page, #f5f7fa);
    min-width: 0;
    min-height: 420px;
    max-height: 75vh;
    scrollbar-width: thin;
    scrollbar-color: var(--el-border-color) transparent;
    
    // 响应式宽度处理
    @media (max-width: 768px) {
      // 在小屏幕上使内容能够更好地自适应
      .chat-content {
        min-width: 100%;
      }
    }
    
    // 显著的垂直滚动条样式
    &::-webkit-scrollbar {
      width: 10px;
      background: transparent;
    }
    
    &::-webkit-scrollbar-thumb {
      background: var(--el-border-color);
      border-radius: 6px;
      min-height: 50px;
      transition: background 0.2s;
      &:hover { background: var(--el-color-primary-light-3); }
    }
    
    // 水平滚动条样式
    &::-webkit-scrollbar-corner {
      background-color: transparent;
    }
    
    // 深色模式背景
    :deep(html.dark) & {
      background-color: var(--el-bg-color);
      
      &::-webkit-scrollbar-thumb {
        background-color: rgba(255, 255, 255, 0.2);
        border: 2px solid var(--el-bg-color);
        
        &:hover {
          background-color: rgba(255, 255, 255, 0.3);
        }
      }
    }
    
    // 确保消息容器内容能正确流动并适应空间
    :deep(.chat-content) {
      width: 100%;
      
      .chat-messages-container {
        width: 100%;
        box-sizing: border-box;
        
        .message {
          width: 100%;
          max-width: 100%;
          box-sizing: border-box;
          overflow: hidden;
          
          // 确保消息内容有正确的宽度处理
          .message-content {
            width: 100%;
            box-sizing: border-box;
            overflow-x: auto;
            
            // 确保代码和预格式化文本可以水平滚动
            pre, code {
              max-width: 100%;
              overflow-x: auto;
            }
            
            // 优化表格显示
            table {
              width: 100%;
              max-width: 100%;
              margin: 10px 0;
              border-collapse: collapse;
              display: block;
              overflow-x: auto;
            }
          }
        }
      }
    }
  }
}

// 确保动画关键帧也直接定义在组件中
@keyframes messagePopIn {
  0% {
    opacity: 0;
    transform: translateY(10px) scale(0.98);
  }
  100% {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@keyframes blink {
  0%, 49% { opacity: 1; }
  50%, 100% { opacity: 0; }
}

@keyframes pulse {
  0% { transform: scale(0.8) translateX(-50%); opacity: 0.7; }
  50% { transform: scale(1.2) translateX(-50%); opacity: 1; }
  100% { transform: scale(0.8) translateX(-50%); opacity: 0.7; }
}

@keyframes contentFadeIn {
  from {
    opacity: 0.5;
    transform: translateY(0);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

// 响应式设计
@media (max-width: 768px) {
  .chat-main-container {
    border-radius: 0;
    height: 100vh;
    max-height: 100vh;
    margin: 0;
    border: none;
  }
}

// 滚动到底部按钮
.scroll-to-bottom-btn {
  position: absolute;
  bottom: 16px;
  right: 16px;
  z-index: 10;
  transition: all 0.3s;
  
  .el-button {
    box-shadow: 0 2px 6px rgba(0, 0, 0, 0.12);
    width: 36px;
    height: 36px;
    
    &:hover {
      transform: translateY(-1px);
      box-shadow: 0 3px 8px rgba(0, 0, 0, 0.16);
    }
  }
}
</style> 
