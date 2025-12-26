import { ref, nextTick } from 'vue';

export function useScroll() {
  const isNearBottom = ref(true);
  
  // 处理滚动事件
  const handleScroll = (event) => {
    const container = event.target;
    if (container) {
      const { scrollTop, scrollHeight, clientHeight } = container;
      const threshold = 150; // 增大阈值，距离底部150px内认为接近底部
      isNearBottom.value = scrollHeight - scrollTop - clientHeight < threshold;
    } else {
      isNearBottom.value = false;
    }
  };
  
  // 滚动到底部
  const scrollToBottom = (force = false, container = null) => {
    if (!container) return;
    
    if (force || isNearBottom.value) {
      nextTick(() => {
        try {
          // 确保DOM已更新后再滚动
          setTimeout(() => {
            container.scrollTop = container.scrollHeight;
          }, 0);
        } catch (e) {
          console.error('滚动到底部失败:', e);
        }
      });
    }
  };
  
  return {
    isNearBottom,
    handleScroll,
    scrollToBottom
  };
}
