import { apiClient } from './apiClient';

// streamChat uses the fetch API directly, not axios
export async function streamChat(data, options = {}) {
  const onError = options.onError || (() => {});
  const onMessage = options.onMessage || (() => {});
  const onFatalError = options.onFatalError || (() => {});
  const onFinish = options.onFinish || (() => {});
  
  let finalTokenStats = null;
  const { signal } = options;
  
  // Function to try parsing the final stats block
  const tryParseFinalStats = (text) => {
    let cleanText = text; // Start with the input text
    // Ensure any leading "data: " prefix is removed *inside* this function
    if (typeof cleanText === 'string' && cleanText.startsWith('data: ')) {
        cleanText = cleanText.slice(6).trim();
    }
    
    try {
      // Attempt to parse the potentially cleaned text
      const jsonData = JSON.parse(cleanText);
      if (jsonData.done === true && 
          typeof jsonData.prompt_eval_count === 'number' && 
          typeof jsonData.eval_count === 'number') {
        // console.log("Successfully parsed stats object:", jsonData); // Debug log
        return {
          prompt: jsonData.prompt_eval_count,
          completion: jsonData.eval_count,
          total: jsonData.prompt_eval_count + jsonData.eval_count,
          total_duration: jsonData.total_duration,
          load_duration: jsonData.load_duration,
          prompt_eval_duration: jsonData.prompt_eval_duration,
          eval_duration: jsonData.eval_duration
        };
      }
    } catch (e) {
      // Log the original input text for debugging if parse fails
      console.error(`Failed to parse JSON for stats: ${e}. Original Text: ${text.substring(0, 500)}`); 
    }
    return null;
  };

  // Simplified processLine: focuses on content extraction and simple done signals
  function processLine(lineContent) {
    let eventDataToProcess = lineContent;
    let isSSEPrefixed = false;

    if (lineContent.startsWith('data: data: ')) {
        eventDataToProcess = lineContent.slice(11).trim(); // Remove "data: data: "
        isSSEPrefixed = true; // It's also SSE prefixed
    } else if (lineContent.startsWith('data: ')) {
      eventDataToProcess = lineContent.slice(6);
      isSSEPrefixed = true;
    }

    // Handle explicit [DONE] signal for SSE (single or double prefix)
    if (isSSEPrefixed && eventDataToProcess === '[DONE]') {
      console.log(`收到结束标记: ${lineContent}`); // Log the original marker
      onMessage('[DONE]');
      return { doneSignal: true };
      }
      
      try {
      const jsonData = JSON.parse(eventDataToProcess);
        
      // Check for Ollama final stats block
      if (jsonData.done === true && 
          typeof jsonData.prompt_eval_count === 'number' && 
          typeof jsonData.eval_count === 'number') {
          console.log("Detected final stats block line.");
          // Return the parsed stats object
          return { 
              stats: {
                  prompt: jsonData.prompt_eval_count,
                  completion: jsonData.eval_count,
                  total: jsonData.prompt_eval_count + jsonData.eval_count,
                  total_duration: jsonData.total_duration,
                  load_duration: jsonData.load_duration,
                  prompt_eval_duration: jsonData.prompt_eval_duration,
                  eval_duration: jsonData.eval_duration
              } 
          };
      }

      // Extract content (OpenAI delta or Ollama message)
      let content = null;
      if (jsonData?.choices?.[0]?.delta?.content) {
        content = jsonData.choices[0].delta.content;
      } else if (jsonData?.message?.content) {
        content = jsonData.message.content;
      } else if (jsonData?.response) {
        content = jsonData.response;
        }
        
      // If content exists, send the original line/eventData that contained it
      if (content !== null && content !== '') { 
        onMessage(lineContent); // Send the raw line/event data containing the content
        return { success: true };
      }
      
      // If it's JSON but has no recognizable content or is Ollama done without stats yet
      if (jsonData.done === true) {
        console.log("Detected done:true without stats, likely end signal.")
        return { potentialEndSignal: true };
        }
      
      // console.log("Filtered JSON without actionable content:", jsonData);
      return { filtered: true }; // JSON but no content extracted or not stats

        } catch (e) {
      // Not JSON. Treat as plain text if not empty or timestamp-like.
      if (eventDataToProcess.trim() && !/^\s*\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\s*$/.test(eventDataToProcess)) {
        onMessage(lineContent); // Send the original line
            return { success: true };
          }
      // console.log("Filtered non-JSON or timestamp-like data:", eventDataToProcess);
        return { filtered: true };
      }
  }
  
  try {
    if (!data.provider || !data.model) { throw new Error('Provider and model are required'); }
    if (!data.messages || !Array.isArray(data.messages) || data.messages.length === 0) { throw new Error('Messages are invalid or empty'); }
    console.log("Starting stream chat request (DIRECT TO BACKEND):", { provider: data.provider, model: data.model });
    const requestOptions = { signal, headers: { 'Content-Type': 'application/json', 'Accept': 'text/event-stream' } };
    const requestData = { ...data, stream: true };
    console.log("Stream request payload:", JSON.stringify(requestData, null, 2));
    const response = await fetch('http://localhost:8000/api/chat/', { method: 'POST', headers: requestOptions.headers, body: JSON.stringify(requestData), signal });
    if (!response.ok) {
      let errText = response.statusText;
        try { const errorBody = await response.json(); errText = errorBody.detail || errorBody.message || errText; } catch { /* Ignore */ }
        throw new Error(`API Request Failed: ${response.status} - ${errText}`);
    }
    console.log("Stream connection established (Direct), receiving data...");
    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';
    let chunkCount = 0;

    try {
      // eslint-disable-next-line no-constant-condition
      while (true) {
        const { done, value } = await reader.read();
        if (done) {
          console.log("Stream reader marked done. Processing any remaining buffer content.");
          // Process remaining buffer content before finishing
          if (buffer.trim()) { // If there's anything left in the buffer
            console.log("Remaining buffer content:", buffer.trim());
            const result = processLine(buffer.trim());
            // Potentially, this last piece could be the stats block
            if (result && result.stats) {
              finalTokenStats = result.stats;
              console.log("Stats processed from remaining buffer and assigned:", finalTokenStats);
            } else if (result && result.success && !result.doneSignal) {
              // If it was regular content, it would have been sent to onMessage by processLine
              // but ensure no partial content is missed if it wasn't a stats block.
              // Note: processLine already calls onMessage for content.
              console.log("Processed regular content from remaining buffer.");
            } else {
              console.log("Remaining buffer content did not result in stats or regular message processing:", result);
            }
          } else {
            console.log("Buffer is empty or whitespace upon stream completion.");
          }
          onFinish(finalTokenStats); // Pass stats when stream is naturally done
          break; // Exit the while(true) loop
        }

        chunkCount++;
        const chunk = decoder.decode(value, { stream: true });
        // console.log(`Received chunk ${chunkCount}, length: ${chunk.length}`);
        buffer += chunk;

        let newlineIndex;
        while ((newlineIndex = buffer.indexOf('\n')) !== -1) {
          const line = buffer.slice(0, newlineIndex).trim();
          buffer = buffer.slice(newlineIndex + 1); // Consume the line from buffer

          if (!line) continue; // Skip empty lines

          // Process line for content or simple done signals
          const result = processLine(line);
          
          // Check if processLine returned stats and store them
          if (result && result.stats) {
              finalTokenStats = result.stats;
              console.log("Captured token stats from processLine result:", finalTokenStats);
              // Since stats indicate the end, we can skip further processing for this line?
              // Or potentially break the inner loop if confident?
              // For now, just capture and let outer loop handle termination.
          }
          
          // No special handling needed for other result signals here anymore,
          // stats are captured within processLine if found.
          // if (result && result.doneSignal) {
          //   // Optional: could break loop earlier if needed, but reader.done handles finish
          // }
        }
      }
    } catch (innerError) {
      console.error('Error during stream processing loop:', innerError);
      onError(innerError);
      // Ensure onFinish is called even if an error occurs within the loop,
      // though finalTokenStats might be null or incomplete.
      onFinish(finalTokenStats); 
    }

    // Final processing after loop ends (either by break or error)
    console.log(`Stream loop finished. Total chunks: ${chunkCount}.`);

    // Attempt to parse remaining buffer content for stats, just in case it wasn't a clean line break
    // This is now less likely to be needed if the stats block ends with \n, but keep as fallback.
    if (!finalTokenStats && buffer.trim()) { 
        const bufferToParseForStats = buffer.trim().startsWith('data: ') ? buffer.trim().slice(6) : buffer.trim();
        console.log("(Fallback) Attempting to parse final stats from remaining buffer:", bufferToParseForStats); 
        const stats = tryParseFinalStats(bufferToParseForStats);
        if (stats) {
            finalTokenStats = stats;
            console.log("Captured token stats from final buffer parse:", finalTokenStats);
        }
    }
    
    return { success: true };

  } catch (error) {
    if (error.name === 'AbortError') {
      console.log("Stream request aborted by user.");
      onFinish(finalTokenStats); // Pass any captured stats on abort
      return { aborted: true };
    }
    console.error("Stream chat request failed (Direct):", error);
    onFatalError(error); // Report fatal error
    onFinish(finalTokenStats); // Pass any captured stats on fatal error
    return { error: error.message };
  }
}

export function getChatLogs() {
  return apiClient.get('/api/chat-logs')
    .catch(error => {
      if (error.response && error.response.status === 404) {
        return apiClient.get('/chat-logs');
      }
      throw error;
    });
}

// 新增：保存聊天记录函数
export function saveChatLog(chatLog) {
  console.log(`Saving chat log, provider: ${chatLog.provider}, model: ${chatLog.model}, messages: ${chatLog.messages.length}`);
  
  return apiClient.post('/api/chat-logs', chatLog)
    .catch(error => {
      if (error.response && error.response.status === 404) {
        // 尝试不带/api前缀
        return apiClient.post('/chat-logs', chatLog);
      }
      console.error('保存聊天记录失败:', error);
      throw error;
    });
}

// getChatLogDetail needs careful handling for non-JSON responses
export async function getChatLogDetail(chatId) {
  console.log(`Getting chat log detail for ID: ${chatId}`);
  try {
    const response = await apiClient.get(`/api/chat-logs/${chatId}`);
    console.log(`Successfully got chat log ${chatId}, data:`, response.data);
    
    // Standard JSON format check
    if (response.data && response.data.messages) {
      return response; 
    }
    
    // Handle plain text response - attempt parsing
    if (typeof response.data === 'string') {
      console.log(`Chat log ${chatId} is string format, attempting parse.`);
      try {
        const parsedData = JSON.parse(response.data);
         // Check if parsed data has the expected structure
        if (parsedData && parsedData.messages) { 
            console.log("Successfully parsed string response into JSON.")
            return { data: parsedData }; 
        } else {
             console.warn(`Parsed string for ${chatId} lacks expected structure. Treating as text.`);
             // Fallthrough to text parsing logic
        }
      } catch (e) {
        console.warn(`Chat log ${chatId} not valid JSON, parsing as text record.`);
        // Fallthrough to text parsing logic
      }
      
      // Text parsing logic (kept from original)
      const lines = response.data.split('\n');
      let provider = 'unknown', model = 'unknown', userMessages = [], assistantContent = '';
      let parsingAssistant = false;
      for (const line of lines) {
        if (line.startsWith('Provider:')) provider = line.substring(9).trim();
        else if (line.startsWith('Model:')) model = line.substring(6).trim();
        else if (line.startsWith('[USER]')) {
          parsingAssistant = false;
          userMessages.push({ role: 'user', content: '' });
        } else if (line.startsWith('--- Assistant Response ---')) parsingAssistant = true;
        else if (parsingAssistant) assistantContent += line + '\n';
        else if (userMessages.length > 0) userMessages[userMessages.length - 1].content += line + '\n';
      }
      userMessages.forEach(msg => msg.content = msg.content.trim());
      assistantContent = assistantContent.trim();
      const messages = [...userMessages, { role: 'assistant', content: assistantContent }];
      return { data: { id: chatId, provider, model, messages } };
    }
    
    // If data is not messages structure or string, return original but log warning
    console.warn(`Chat log ${chatId} has unexpected format:`, response.data);
    return response;
    
  } catch (error) {
    if (error.response && error.response.status === 404) {
      // Try fallback path if needed, though less likely for specific ID
      return apiClient.get(`/chat-logs/${chatId}`); 
    }
    console.error(`Failed to get chat log detail for ${chatId}:`, error);
    throw error;
  }
} 