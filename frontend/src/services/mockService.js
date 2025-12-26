// Contains mock functions potentially used for testing or development

export async function _mockStreamResponse(payload, options) {
    const { onMessage, signal } = options;
    const lastUserMessage = payload.messages.findLast(m => m.role === 'user')?.content || "";
    
    const mockResponse = `您好！我是一个模拟的AI助手。\n\n您说: "${lastUserMessage}"\n\n这是一个<think>思考过程示例，支持Markdown格式：\n- 首先分析用户问题\n- 然后组织答案\n- 最后形成响应</think>模拟的流式响应，仅用于测试前端功能。您可以看到这段文字是逐字显示的，就像真实的AI在回复一样。

我支持**Markdown**格式，例如：
- 列表项1
- 列表项2

\`\`\`js
// 代码示例
function hello() {
  console.log("Hello world!");
}
\`\`\``;

    const isAborted = () => signal && signal.aborted;
    
    for (let i = 0; i < mockResponse.length; i += 3) {
      if (isAborted()) break;
      const nextChunk = mockResponse.slice(i, i + 3);
      const chunk = { choices: [{ delta: { content: nextChunk } }] };
      onMessage(JSON.stringify(chunk));
      await new Promise(resolve => setTimeout(resolve, 50));
    }
    
    if (!isAborted()) {
      await new Promise(resolve => setTimeout(resolve, 500));
      onMessage('[DONE]');
    }
  } 