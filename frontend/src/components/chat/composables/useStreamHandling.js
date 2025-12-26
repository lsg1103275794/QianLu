import { ref } from 'vue';
// 移除未使用的ElMessage导入
// import { ElMessage } from 'element-plus';
import { cleanStreamData } from '../../../utils/thinkingUtils';

export function useStreamHandling() {
  const streamBuffer = ref(''); // 原始流缓存
  const isStreamFinished = ref(false);
  const isStreaming = ref(false);
  const currentMessageIndex = ref(-1);
  const currentStreamContent = ref(''); // 完整流内容存储
  let isFinishing = false; // 添加标志位防止finishStreaming被多次调用
  let lastUpdateTime = Date.now(); // 最后一次更新时间
  let timeoutDetector = null; // 超时检测器
  
  // 启动超时检测
  const startTimeoutDetection = (onTimeout) => {
    clearTimeout(timeoutDetector);
    lastUpdateTime = Date.now();
    
    timeoutDetector = setInterval(() => {
      // 如果超过10秒没有更新，且流未完成，判定为超时
      if (Date.now() - lastUpdateTime > 10000 && isStreaming.value && !isStreamFinished.value) {
        console.warn('检测到流传输超时，自动触发完成流程');
        if (typeof onTimeout === 'function') {
          onTimeout();
        }
        clearTimeout(timeoutDetector);
      }
    }, 2000); // 每2秒检查一次
  };
  
  // 停止超时检测
  const stopTimeoutDetection = () => {
    clearTimeout(timeoutDetector);
    timeoutDetector = null;
  };
  
  // 清理流内容，移除控制字符和元数据
  const cleanStreamContent = (content) => {
    if (!content) return '';
    
    // 移除常见的控制信息模式
    let cleaned = content;
    
    // 移除JSON格式的控制消息
    const controlPatterns = [
      /\{"choices":\[\{"delta":\{"role":"assistant"\}\}\]\}/g,
      /\{"choices":\[\{"delta":\{\}\}\]\}/g,
      /\{"done":true\}/g,
      /\[DONE\]/g,
      /data: \[DONE\]/g,
      /data: {"done":true}/g,
      /data: ping - \d{4}-\d{2}-\d{2}[^}]+}/g,
      /ping - \d{4}-\d{2}-\d{2}[^}]+}/g,
      /data:data:/g,  // 添加过滤data:data:格式
      /data:data[^:]*:/g,  // 过滤各种变体如data:data, data:data123:等
      /^\s*data:\s*/gm,  // 移除每行开头的data:前缀
    ];
    
    controlPatterns.forEach(pattern => {
      cleaned = cleaned.replace(pattern, '');
    });
    
    // 移除换行符中可能包含的JSON控制消息
    cleaned = cleaned.split('\n')
      .filter(line => {
        // 过滤掉控制行
        const isControlLine = 
          line.includes('{"choices":[{"delta":{"role":') || 
          line.includes('{"done":true}') ||
          line.includes('[DONE]') ||
          line.includes('ping - ') ||
          line.includes('data: ping') ||
          line.includes('data:data:') ||  // 添加过滤data:data:格式
          line.match(/^data:data[^:]*:/);  // 过滤各种变体
        return !isControlLine;
      })
      .join('\n');
    
    // 压缩连续的空行
    cleaned = cleaned.replace(/\n\s*\n\s*\n/g, '\n\n');
    
    // 检查并移除重复的data:data:数据格式
    cleaned = cleaned.replace(/^data:data:.*$/gm, '');
    cleaned = cleaned.replace(/^data:data.*:.*$/gm, '');
    
    // 移除开头和结尾的空白
    cleaned = cleaned.trim();
    
    return cleaned;
  };
  
  // 初始化流处理（未使用）
  // const initializeStreaming = () => {
  //   if (isStreaming.value) return;
  //   
  //   console.log('初始化流处理状态');
  //   isStreaming.value = true;
  //   currentStreamContent.value = '';
  //   streamBuffer.value = '';
  //   
  //   return {
  //     success: true
  //   };
  // };
  
  // 处理流消息
  const handleStreamMessage = (chunkData, typewriterQueue, onContentUpdate = null, onTimeout = null) => {
    if (typeof chunkData !== 'string') {
      console.error('收到非字符串事件:', chunkData);
      return { error: '非字符串事件' };
    }
    
    // 启动超时检测
    if (!timeoutDetector && !isStreamFinished.value && onTimeout) {
      startTimeoutDetection(onTimeout);
    }
    
    // 更新最后一次收到数据的时间
    lastUpdateTime = Date.now();
    
    // 过滤ping消息
    const isPingMessage = (content) => {
      return content === '[DONE]' || 
             content === 'ping' || 
             content === '"ping"' || 
             content.includes('"ping"') || 
             content.includes("'ping'") ||
             content.includes('ping - ');
    };
    
    try {
      // 检查各种结束标记
      if (chunkData === '[DONE]' || 
          chunkData.includes('[DONE]') || 
          chunkData.includes('"done":true') || 
          chunkData.includes('"stop":true') || 
          chunkData.includes('"finished":true') || 
          chunkData.includes('{"done":') ||
          chunkData.includes('data: [DONE]')) {
        console.log('收到结束标记:', chunkData);
        stopTimeoutDetection();
        setTimeout(() => {
          finishStreaming();
        }, 100);
        return { done: true };
      }
      
      // 如果是保活消息，跳过处理
      if (isPingMessage(chunkData)) {
        console.log('收到保活消息，跳过:', chunkData);
        return { ping: true };
      }
      
      // 标记正在流式处理
      isStreaming.value = true;
      
      // 使用中央清理函数处理数据
      let content = cleanStreamData(chunkData);
      
      // 过滤OpenAI控制消息
      if (content.match(/^\s*\{"choices":\s*\[/) && !content.match(/"content"/)) {
        console.log('过滤OpenAI控制消息:', content);
        return { filtered: true };
      }
      
      // 尝试解析JSON格式的内容
      try {
        if (chunkData.startsWith('data: ')) {
          content = chunkData.slice(6);
          // 再次清理，以防data:前缀后还有控制消息
          content = cleanStreamData(content);
        }
        
        // 尝试解析JSON
        if (content.trim().startsWith('{') || content.trim().startsWith('[')) {
          // 可能是JSON数据
          const jsonData = JSON.parse(content);
          
          // 处理常见的AI API响应格式
          if (jsonData.choices && jsonData.choices.length > 0) {
            // OpenAI格式: { "choices": [{ "delta": {"content": "text"} }] }
            if (jsonData.choices[0].delta && jsonData.choices[0].delta.content !== undefined) {
              content = jsonData.choices[0].delta.content || '';
            } 
            // 完整消息格式: { "choices": [{ "message": {"content": "text"} }] }
            else if (jsonData.choices[0].message && jsonData.choices[0].message.content !== undefined) {
              content = jsonData.choices[0].message.content || '';
            }
            // 文本格式: { "choices": [{ "text": "content" }] }
            else if (jsonData.choices[0].text !== undefined) {
              content = jsonData.choices[0].text || '';
            }
            // 如果只有delta对象但没有内容，可能是控制消息
            else if (jsonData.choices[0].delta && Object.keys(jsonData.choices[0].delta).length === 0) {
              console.log('过滤空delta对象');
              return { filtered: true };
            }
          } 
          // Ollama/本地模型格式: { "response": "text" } 或 { "message": { "content": "text" } }
          else if (jsonData.response !== undefined) {
            content = jsonData.response || '';
          } 
          else if (jsonData.message && jsonData.message.content !== undefined) {
            content = jsonData.message.content || '';
          }
          
          // 如果处理后content还是对象，则转换为字符串
          if (typeof content !== 'string') {
            content = JSON.stringify(content);
          }
        }
      } catch (e) {
        // 解析失败，保持原内容
        console.log('JSON解析失败，保持原内容:', e.message);
      }
      
      // 如果content为空，跳过处理
      if (content === '') {
        return { empty: true };
      }
      
      // 更新当前内容
      currentStreamContent.value += content;
      
      // 将内容传递给打字机队列
      if (typewriterQueue && typeof typewriterQueue === 'object' && 'value' in typewriterQueue) {
        typewriterQueue.value += content;
      }
      
      // 如果有提供回调，则调用
      if (typeof onContentUpdate === 'function') {
        onContentUpdate(currentStreamContent.value, content);
      }
      
      // 更新缓冲区
      streamBuffer.value = currentStreamContent.value;
      
      return { 
        success: true, 
        content, 
        fullContent: currentStreamContent.value 
      };
    } catch (error) {
      console.error('处理流消息时出错:', error);
      return { error: error.message };
    }
  };
  
  // 处理流错误（未使用）
  // const handleStreamError = (error) => {
  //   console.error('流式连接错误:', error);
  //   ElMessage.error(`连接错误: ${error.message || '无法连接到服务器'}`);
  // };
  
  // 处理流致命错误（未使用）
  // const handleStreamFatalError = (error) => {
  //   console.error('流式传输致命错误:', error);
  //   ElMessage.error(`传输错误: ${error.message || '传输过程发生错误'}`);
  // };
  
  // 重置流处理状态
  const resetStreamState = () => {
    streamBuffer.value = '';
    currentStreamContent.value = '';
    isStreamFinished.value = false;
    isStreaming.value = false;
    currentMessageIndex.value = -1;
    isFinishing = false;
    stopTimeoutDetection();
  };
  
  // 设置当前消息索引
  const setCurrentMessageIndex = (index) => {
    currentMessageIndex.value = index;
  };
  
  // 完成流处理
  const finishStreaming = () => {
    // 如果已经在进行完成操作，则直接返回
    if (isFinishing || isStreamFinished.value) {
      console.log('流处理已经在完成中或已完成，忽略重复调用');
      return { skipped: true };
    }
    
    isFinishing = true;
    stopTimeoutDetection();
    
    // 最后一次清理
    currentStreamContent.value = cleanStreamData(currentStreamContent.value);
    streamBuffer.value = currentStreamContent.value;
    
    isStreamFinished.value = true;
    isStreaming.value = false;
    currentMessageIndex.value = -1;
    
    console.log('流处理已完成');
    
    // 延迟恢复finishStreaming可用状态
    setTimeout(() => {
      isFinishing = false;
    }, 1000);
    
    return { success: true, content: currentStreamContent.value };
  };
  
  return {
    streamBuffer,
    isStreamFinished,
    isStreaming,
    currentMessageIndex,
    currentStreamContent,
    handleStreamMessage,
    cleanStreamContent,
    resetStreamState,
    setCurrentMessageIndex,
    finishStreaming,
  };
}
