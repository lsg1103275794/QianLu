/**
 * 思考标签与Markdown渲染工具函数
 * 用于解析和处理聊天消息中的思考标签(<think>)和Markdown格式化
 */

import { marked } from 'marked';
import DOMPurify from 'dompurify';
import hljs from 'highlight.js';

/**
 * 解析消息内容中的思考标签
 * @param {string} content - 原始消息内容
 * @returns {Object} - 包含思考内容和可见内容的对象
 */
export const preprocessContent = (raw) => {
  if (!raw || typeof raw !== 'string') return raw;
  let content = raw;
  
  // 1. 过滤掉常见的噪声前缀（###1., ---##1., 等标识符）
  content = content.replace(/(^|\n)[-*#]{1,}[\d.]{1,}(?=\s)/g, '$1');
  
  // 2. 确保标题格式正确（Markdown格式的标题必须有空格）
  content = content.replace(/(^|\n)(#+)([^\s])/g, '$1$2 $3');
  
  // 3. 处理标题前后换行
  content = content.replace(/([^\n])(#+) /g, '$1\n\n$2 '); // 标题前添加双空行
  content = content.replace(/(#+) (.+?)(\n)(?!\n)/g, '$1 $2$3\n'); // 标题后添加一个空行
  
  // 4. 更加强化段落换行处理
  // 首先标准化所有换行为单换行
  content = content.replace(/\n{2,}/g, '\n');
  
  // 然后在句子结束符号后添加双换行（但排除已有双空行的情况）
  content = content.replace(/([.!?。！？])([\s]*[\n]?)([^#\s*\->\n])/g, '$1\n\n$3');
  
  // 在冒号、分号等后面添加单换行（如果后面跟着大写字母或中文开头的新句子）
  // content = content.replace(/([;:：；])([\s]*[\n]?)([A-Z\u4e00-\u9fa5])/g, '$1\n$3'); // 注释掉此行以修复冒号换行问题
  
  // 5. 确保列表项正确渲染 - 更多强化
  // 列表项之间有一个换行，但不是双空行
  content = content.replace(/(\n[*\-+] .+)(?!\n)/g, '$1\n');
  // 确保列表项有正确的缩进和间距
  content = content.replace(/(\n[*\-+] .+\n)(?=[*\-+] )/g, '$1\n');
  
  // 6. 去除连续超过两个的换行，保留至多两个换行符
  content = content.replace(/\n{3,}/g, '\n\n');
  
  // 7. 增强引用块处理
  content = content.replace(/(^|\n)>(?! )/g, '$1> '); // 确保引用块后有空格
  // 引用块之间添加适当间距
  content = content.replace(/(^|\n)(> .+)(\n)(?!>)/g, '$1$2\n\n');
  
  // 8. 增强代码块格式处理
  content = content.replace(/([^\n])```/g, '$1\n\n```'); // 代码块前确保有双空行
  content = content.replace(/```(?!\n)/g, '```\n'); // 代码块后确保有换行
  content = content.replace(/```(\w*)\n(?!\n)/g, '```$1\n\n'); // 代码块语言标识后确保有双空行
  content = content.replace(/\n```\n(?!\n)/g, '\n```\n\n'); // 代码块结束后确保有双空行
  
  // 9. 表格相关增强
  content = content.replace(/([^\n])\n(\|.*\|.*\n)/g, '$1\n\n$2'); // 表格前确保有双空行
  content = content.replace(/(\|.*\|[^\n]*)\n(?!\n)/g, '$1\n\n'); // 表格后确保有双空行
  
  // 10. 自动检测代码内容并包装为代码块（保留原有逻辑）
  if (!/```/.test(content)) {
    // 检测是否像代码
    const looksLikeCode = /^[ \t]*(import|export|function|class|const|let|var|if|for|while|switch|return)\b/.test(content) || 
                          (/[;{}=()[\]<>]/.test(content) && /\n/.test(content) && !/[。，、；''""《》？]/.test(content) && 
                          content.split('\n').length > 2);
    
    // 检测常见编程语言结构
    const hasJavaScriptSyntax = /^[ \t]*(import|export|const|let|var|function|class|=>)\b/.test(content);
    const hasPythonSyntax = /^[ \t]*(def|class|import|from|if __name__)\b/.test(content);
    const hasHTMLSyntax = /^[ \t]*<(!DOCTYPE|html|head|body|div|span|p|a|img|table)\b/.test(content);
    const hasCSSSyntax = /^[ \t]*(\.|#|body|html|@media|@keyframes)\s*\{/.test(content);
    const hasSQLSyntax = /^[ \t]*(SELECT|INSERT|UPDATE|DELETE|CREATE|DROP|ALTER)\b/i.test(content);
    
    // 确定语言标识
    let language = '';
    if (hasJavaScriptSyntax) language = 'javascript';
    else if (hasPythonSyntax) language = 'python';
    else if (hasHTMLSyntax) language = 'html';
    else if (hasCSSSyntax) language = 'css';
    else if (hasSQLSyntax) language = 'sql';
    
    // 如果内容看起来是代码，自动包装为代码块
    if (looksLikeCode) {
      content = '```' + language + '\n' + content.trim() + '\n```';
    }
  }
  
  // 11. 优化中文标点符号与正文间距
  content = content.replace(/([。，、；：？！])([^\s\n])/g, '$1 $2');
  
  // 12. 增强长段落自动分段处理
  if (content.length > 200) {
    const lines = content.split('\n');
    const newLines = [];
    
    for (let i = 0; i < lines.length; i++) {
      // 如果一行文字超过80个字符且没有明显的段落标记，尝试在句号等位置分段
      if (lines[i].length > 80 && !/^[#>*\-+\d|`]/.test(lines[i])) {
        // 首先按句号等标点符号分割
        let segmented = lines[i]
          .replace(/([。！？.!?])\s*/g, '$1\n')  // 在句号等后添加换行
          .replace(/([；;])\s*/g, '$1\n')  // 在分号后添加换行
          .replace(/([,，])\s*(?=[^,，]{20,})/g, '$1\n');  // 在逗号后添加换行(如果后面还有较长文本)
        
        // 移除过短的段落分割（少于15个字符通常不应该独立成段）
        segmented = segmented.split('\n').filter(seg => seg.trim()).map((seg, idx, arr) => {
          // 如果当前段落很短且不是最后一段，可能与下一段合并
          if (seg.length < 15 && idx < arr.length - 1 && 
              !seg.match(/[。！？.!?]$/) && // 不以句号等结尾
              arr[idx + 1].length < 40) {   // 下一段不太长
            return seg;                     // 保留原样，不加换行
          }
          return seg + '\n';                // 其他情况加换行
        }).join('');
        
        newLines.push(segmented);
      } else {
        newLines.push(lines[i]);
      }
    }
    
    content = newLines.join('\n');
    
    // 再次合并过多的空行
    content = content.replace(/\n{3,}/g, '\n\n');
  }
  
  // 13. 英文单词空格优化
  content = content.replace(/([a-zA-Z])([a-zA-Z])/g, function(match, p1, p2) {
    if (p1 === p1.toUpperCase() && p2 === p2.toLowerCase()) {
      return p1 + ' ' + p2; // 在大写字母后面跟小写字母时添加空格
    }
    return match;
  });
  
  // 14. 最终整理：去除文档首尾多余空行但保留文档内部的格式
  content = content.trim();
  
  return content;
};

/**
 * 清理原始流数据中的重复前缀和控制信息
 * @param {string} content - 原始内容
 * @returns {string} - 清理后的内容
 */
export const cleanStreamData = (content) => {
  if (!content || typeof content !== 'string') return content || '';
  
  // 移除data:data:格式和变体
  let cleaned = content.replace(/data:data:/g, '');
  cleaned = cleaned.replace(/data:data[^:]*:/g, '');
  
  // 移除开头的data:前缀（每行）
  cleaned = cleaned.replace(/^\s*data:\s*/gm, '');
  cleaned = cleaned.replace(/\n\s*data:\s*/gm, '\n');
  
  // 移除完整的OpenAI格式控制消息
  cleaned = cleaned.replace(/\{"choices":\[\{"delta":\{"role":"assistant"\}\}\]\}/g, '');
  cleaned = cleaned.replace(/\{"choices":\[\{"delta":\{\}\}\]\}/g, '');
  cleaned = cleaned.replace(/\{"done":true\}/g, '');
  cleaned = cleaned.replace(/\[DONE\]/g, '');
  cleaned = cleaned.replace(/\{"status":\s*"done"\}/g, '');
  
  // 移除可能连续出现的data:data数据
  cleaned = cleaned.replace(/data:data:data:/g, '');
  cleaned = cleaned.replace(/datadata:/g, '');
  cleaned = cleaned.replace(/datadatadata:/g, '');
  
  // 处理常见的API响应格式字段（如果只有控制字段没有实际内容）
  cleaned = cleaned.replace(/\{"choices":\[\{"delta":\{\}\}\]\}/g, '');
  cleaned = cleaned.replace(/\{"choices":\[\{\}\]\}/g, '');
  
  // 移除控制消息行
  cleaned = cleaned.split('\n')
    .filter(line => {
      return !line.includes('{"choices":[{"delta":{"role":') && 
             !line.includes('{"done":true}') &&
             !line.includes('[DONE]') &&
             !line.includes('data:data:') &&
             // Filter out lines that are exactly {"status": "done"} or similar variations
             !line.match(/^\s*\{\s*"status"\s*:\s*"done"\s*\}\s*$/) &&
             // 过滤JSON格式控制消息（完整行匹配）
             !line.match(/^\s*\{"choices":\s*\[\s*\{\s*"delta"\s*:\s*\{\s*"role"\s*:\s*"assistant"\s*\}\s*\}\s*\]\s*\}\s*$/) &&
             !/^\s*$/.test(line); // 移除空行
    })
    .join('\n');
  
  // 使用正则表达式删除类似 {"choices": [{"delta": {"role": "assistant"}}]} 的内容
  cleaned = cleaned.replace(/\{\s*"choices"\s*:\s*\[\s*\{\s*"delta"\s*:\s*\{\s*"role"\s*:\s*"assistant"\s*\}\s*\}\s*\]\s*\}/g, '');
  cleaned = cleaned.replace(/\{\s*"choices"\s*:\s*\[\s*\{\s*"delta"\s*:\s*\{\s*\}\s*\}\s*\]\s*\}/g, '');
  cleaned = cleaned.replace(/\{\s*"status"\s*:\s*"done"\s*\}/g, '');
  
  // 压缩连续空行
  cleaned = cleaned.replace(/\n\s*\n\s*\n/g, '\n\n');
  
  // 移除开头和结尾的空白
  return cleaned.trim();
};

export const parseThinkingContent = (() => {
  // 缓存上一次输入和结果
  let lastInput = '';
  let lastResult = { thinking: '', visible: '' };
  
  // 返回实际函数
  return (content) => {
    try {
      if (!content || typeof content !== 'string') {
        return { thinking: '', visible: content || '' };
      }
      
      // 如果内容没变，直接返回缓存结果
      if (content === lastInput) {
        return lastResult;
      }
      
      // 先清理stream数据中的重复前缀
      let raw = cleanStreamData(content);
      
      // 自动解码 HTML escape
      raw = raw
        .replace(/&lt;/g, '<')
        .replace(/&gt;/g, '>')
        .replace(/&amp;/g, '&');
      
      // 支持 <think>...</think> 和 <thinking>...</thinking> 标签
      const tagRegex = /<(think|thinking)>([\s\S]*?)<\/(think|thinking)>/g;
      let tagMatches = [...(raw.matchAll(tagRegex) || [])];
      let thinkingParts = [];
      if (tagMatches.length > 0) {
        thinkingParts = tagMatches.map(match => match[2].trim());
        // 移除所有标签内容
        raw = raw.replace(tagRegex, '').trim();
      }
      // 支持 ***思考过程 ... ***思考结束
      const starThinkRegex = /\*\*\*思考过程([\s\S]*?)\*\*\*思考结束/g;
      let starThinkMatches = [...(raw.matchAll(starThinkRegex) || [])];
      if (starThinkMatches.length > 0) {
        thinkingParts = thinkingParts.concat(starThinkMatches.map(match => match[1].trim()));
        raw = raw.replace(starThinkRegex, '').trim();
      }
      // 合并所有思考内容
        const thinking = thinkingParts.join('\n\n');
        
      // 更新缓存
      lastInput = content;
      lastResult = { thinking, visible: raw };
      return lastResult;
    } catch (error) {
      console.error('解析思考标签出错:', error);
      // 出错时返回原始内容
      return { thinking: '', visible: content || '' };
    }
  };
})();

/**
 * 渲染Markdown内容为HTML
 * @param {string} content - Markdown格式的内容
 * @returns {string} - 渲染后的HTML内容
 */
export const renderMarkdown = (() => {
  const cache = new Map();
  
  // 配置marked选项，参考AnalysisResults.vue中的配置
  marked.setOptions({
    highlight: function(code, lang) {
      const languageDisplay = lang ? lang : '代码';
      const langClass = lang ? ` ${lang}` : '';
      
      try {
        const highlightedCode = lang && hljs.getLanguage(lang) ? 
          hljs.highlight(code, { language: lang }).value : 
          hljs.highlightAuto(code).value;
        
        return `<div class="code-block">
                  <div class="code-block-header">
                    <span class="code-language">${languageDisplay}</span>
                    <button type="button" class="copy-code-button" onclick="window.copyCodeToClipboard(this)">复制</button>
                  </div>
                  <pre><code class="hljs${langClass}">${highlightedCode}</code></pre>
                </div>`;
      } catch (err) {
        console.warn('代码高亮出错:', err);
        return `<pre><code>${code}</code></pre>`;
      }
    },
    breaks: true,      // 识别回车符作为换行
    gfm: true,         // 启用GitHub风格Markdown
    headerIds: true,   // 为标题生成ID
    mangle: false,     // 不转义内联HTML
    smartLists: true,  // 使用更智能的列表行为
    smartypants: true  // 使用更智能的标点符号
  });
  
  // 为文档添加全局复制代码功能
  if (typeof window !== 'undefined' && !window.copyCodeToClipboard) {
    window.copyCodeToClipboard = function(button) {
      try {
        const codeBlock = button.parentNode.nextElementSibling?.querySelector('code');
        if (!codeBlock) return;
        
        const code = codeBlock.textContent || '';
        
        navigator.clipboard.writeText(code).then(() => {
          const originalText = button.textContent;
          button.textContent = "已复制!";
          button.classList.add("copied");
          
          setTimeout(() => {
            button.textContent = originalText;
            button.classList.remove("copied");
          }, 2000);
        }).catch(err => {
          console.error('复制失败:', err);
        });
      } catch (e) {
        console.error('复制代码时出错:', e);
      }
    };
  }
  
  return (content) => {
    try {
      if (!content || typeof content !== 'string') return '';
      
      // 检查缓存
      if (cache.has(content)) {
        return cache.get(content);
      }
      
      try {
        // 首先进行预处理以确保Markdown格式正确
        const processedContent = preprocessContent(content);
        
        // 使用marked库渲染Markdown
        let html = marked(processedContent);
        
        // 使用DOMPurify清理HTML以防XSS攻击
        html = DOMPurify.sanitize(html);
        
        // 为表格添加响应式包装器
        html = html.replace(/<table>/g, '<div class="table-responsive"><table class="md-table">');
        html = html.replace(/<\/table>/g, '</table></div>');
        
        // 为所有链接添加target="_blank"和rel="noopener"属性
        html = html.replace(/<a(.*?)>/g, '<a$1 target="_blank" rel="noopener">');
        
        // 限制缓存大小
        if (cache.size > 100) {
          const firstKey = cache.keys().next().value;
          cache.delete(firstKey);
        }
        
        cache.set(content, html);
        return html;
      } catch (e) {
        console.error('渲染Markdown出错:', e);
        return `<div class="markdown-error">${content}</div>`;
      }
    } catch (outerError) {
      console.error('处理Markdown渲染出错:', outerError);
      return String(content || '');
    }
  };
})();

/**
 * 处理流式消息内容
 * @param {string} content - 流式消息内容
 * @returns {Object} - 包含处理后的思考HTML和可见HTML的对象
 */
export const handleStreamingContent = (content) => {
  try {
    if (!content) return { thinkingHtml: '', visibleHtml: '' };
    
    // 使用parseThinkingContent获取思考和可见内容
    const parsed = parseThinkingContent(content);
    
    // 仅在内容存在时才进行渲染
    const thinkingHtml = parsed.thinking ? renderMarkdown(parsed.thinking) : '';
    const visibleHtml = parsed.visible ? renderMarkdown(parsed.visible) : '';
    
    return { thinkingHtml, visibleHtml };
  } catch (error) {
    console.error('处理流式内容出错:', error);
    // 发生错误时返回简单格式化内容
    return { 
      thinkingHtml: '', 
      visibleHtml: content ? `<div class="error-content">${content}</div>` : ''
    };
  }
};

/**
 * 格式化时间戳
 * @param {string} timestamp - ISO格式的时间戳
 * @returns {string} - 格式化后的时间字符串
 */
export const formatTimestamp = (timestamp) => {
  if (!timestamp) return '';
  try {
    const date = new Date(timestamp);
    if (isNaN(date.getTime())) return '';
    
    const now = new Date();
    const isToday = date.toDateString() === now.toDateString();
    
    if (isToday) {
      return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } else {
      return date.toLocaleDateString([], { month: 'short', day: 'numeric' }) + ' ' + 
             date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    }
  } catch (e) {
    console.error('格式化时间戳出错:', e);
    return '';
  }
};

/**
 * 创建一个节流函数
 * @param {Function} fn - 要节流的函数
 * @param {number} delay - 延迟时间(毫秒)
 * @returns {Function} - 节流后的函数
 */
export const throttle = (fn, delay) => {
  let lastCall = 0;
  return function(...args) {
    const now = new Date().getTime();
    if (now - lastCall >= delay) {
      lastCall = now;
      fn.apply(this, args);
    }
  };
}; 