import { ref } from 'vue';

export function useTypewriter() {
  const typewriterQueue = ref('');
  const isTyping = ref(false);
  let typewriterTimeoutId = null;
  const TYPEWRITER_DELAY_DEFAULT = 10; // 加快默认速度
  let typewriterDelay = TYPEWRITER_DELAY_DEFAULT;
  
  // 开始打字效果
  const startTypewriter = (textRef) => {
    if (!textRef) {
      console.error('无法启动打字机效果: 文本引用不存在');
      return;
    }
    
    if (isTyping.value) {
      console.log('打字机效果已在运行中，将继续处理队列');
    } else {
      isTyping.value = true;
      console.log('启动打字机效果，队列长度:', typewriterQueue.value.length);
    }
    
    typeCharacter(textRef);
  };
  
  // 打字字符
  const typeCharacter = (textRef) => {
    if (!textRef) {
      console.error('无法继续打字: 文本引用不存在');
      isTyping.value = false;
      return;
    }
    
    if (typewriterQueue.value.length === 0) {
      console.log('打字机队列为空，停止打字');
      isTyping.value = false;
      return;
    }
    
    // 每次处理更大的块，加快渲染速度
    const chunkSize = Math.min(30, typewriterQueue.value.length);
    const chunk = typewriterQueue.value.substring(0, chunkSize);
    typewriterQueue.value = typewriterQueue.value.substring(chunkSize);
    
    // 创建文本节点并附加到DOM
    if (textRef && textRef.nodeType === Node.ELEMENT_NODE) {
      // 使用textContent是最可靠且性能最好的方法
      const textNode = document.createTextNode(chunk);
      textRef.appendChild(textNode);
      
      // 如果使用innerHTML，文本会被解析而不是被当作纯文本
      // textRef.innerHTML += chunk;
    } else {
      console.warn('文本引用不是一个有效的DOM元素');
    }
    
    // 计算延迟时间 - 为更大的块使用更长的延迟
    const currentDelay = Math.max(1, typewriterDelay * (chunkSize / 10));
    
    // 继续下一个字符
    typewriterTimeoutId = setTimeout(() => typeCharacter(textRef), currentDelay);
  };
  
  // 停止打字
  const stopTypewriter = () => {
    if (typewriterTimeoutId) {
      clearTimeout(typewriterTimeoutId);
      typewriterTimeoutId = null;
      console.log('打字机效果已停止');
    }
    isTyping.value = false;
    typewriterQueue.value = '';
  };
  
  // 设置打字机速度
  const setTypewriterSpeed = (speed) => {
    // speed: 0.5 (慢) 到 2.0 (快)
    if (speed > 0) {
      typewriterDelay = TYPEWRITER_DELAY_DEFAULT / speed;
    }
  };
  
  return {
    typewriterQueue,
    isTyping,
    startTypewriter,
    stopTypewriter,
    setTypewriterSpeed
  };
}
