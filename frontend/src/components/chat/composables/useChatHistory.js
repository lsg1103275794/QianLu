import { ref } from 'vue';
import api from '../../../services/api';
import { ElMessage } from 'element-plus';

export function useChatHistory() {
  const chatLogs = ref([]);
  const loadingChatLogs = ref(false);
  const chatLogsDialogVisible = ref(false);
  
  // 加载聊天历史记录
  const loadChatLogs = async () => {
    loadingChatLogs.value = true;
    chatLogsDialogVisible.value = true;
    
    try {
      const response = await api.getChatLogs();
      chatLogs.value = response.data || [];
    } catch (error) {
      console.error('获取聊天记录失败:', error);
      ElMessage.error('获取聊天记录失败');
      chatLogs.value = [];
    } finally {
      loadingChatLogs.value = false;
    }
  };
  
  // 加载指定聊天记录详情
  const loadChatDetail = async (chatId) => {
    loadingChatLogs.value = true;
    
    try {
      const response = await api.getChatLogDetail(chatId);
      const chatData = response.data;
      
      if (chatData && chatData.messages) {
        return chatData;
      } else {
        throw new Error('聊天记录格式无效');
      }
    } catch (error) {
      console.error(`获取聊天记录 ${chatId} 详情失败:`, error);
      ElMessage.error('获取聊天记录详情失败');
      return null;
    } finally {
      loadingChatLogs.value = false;
    }
  };
  
  // 处理聊天记录点击
  const handleChatLogClick = (row) => {
    loadChatDetail(row.id);
  };
  
  return {
    chatLogs,
    loadingChatLogs,
    chatLogsDialogVisible,
    loadChatLogs,
    loadChatDetail,
    handleChatLogClick
  };
}
