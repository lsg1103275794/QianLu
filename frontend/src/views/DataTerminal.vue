<template>
  <div class="data-terminal">
    <el-card shadow="never" class="page-card">
      <template #header>
        <div class="card-header">
          <h2>{{ addEmoji('数据终端', 'menu', 'data-terminal') }} - 结果管理</h2>
          <el-button @click="fetchResults" :loading="loading" type="primary" plain>
            <el-icon><Refresh /></el-icon>
            刷新列表
          </el-button>
        </div>
      </template>

      <el-table 
        :data="resultsData"
        v-loading="loading"
        style="width: 100%"
        stripe
        border
        empty-text="暂无数据"
      >
        <el-table-column prop="name" label="名称" min-width="150">
          <template #default="scope">
            <span>{{ scope.row.name || '未命名' }}</span>
            <!-- Add Rename Button -->
            <el-button 
              type="primary"
              :icon="EditPen"
              size="small"
              circle 
              plain
              @click="openRenameDialog(scope.row)"
              class="rename-btn"
            />
          </template>
        </el-table-column>
        <el-table-column prop="type" label="类型" width="100">
          <template #default="scope">
            <el-tag :type="getResultTypeTag(scope.row.type)" size="small">
              {{ getResultTypeName(scope.row.type) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="timestamp" label="生成时间" width="180" sortable>
          <template #default="scope">
            {{ formatTimestamp(scope.row.timestamp) }}
          </template>
        </el-table-column>
        <el-table-column prop="source_info" label="来源信息" min-width="200" show-overflow-tooltip>
           <template #default="scope">
             {{ scope.row.source_info || '-' }}
           </template>
        </el-table-column>
        <el-table-column prop="model_info" label="模型信息" width="200" show-overflow-tooltip>
           <template #default="scope">
             {{ scope.row.model_info || '-' }}
           </template>
        </el-table-column>
        <el-table-column label="操作" width="280" fixed="right"> <!-- Increase width for Export button -->
          <template #default="scope">
            <el-button size="small" type="primary" plain @click="handleViewClick(scope.row)">
              <el-icon><View /></el-icon>查看
            </el-button>
            
            <!-- Export Dropdown Button -->
            <el-dropdown @command="(command) => handleExportClick(scope.row, command)" style="margin-left: 5px;">
              <el-button size="small" type="success" plain>
                <el-icon><Download /></el-icon>导出<el-icon class="el-icon--right"><arrow-down /></el-icon>
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="md">Markdown (.md)</el-dropdown-item>
                  <el-dropdown-item command="docx">Word (.docx)</el-dropdown-item>
                  <el-dropdown-item command="txt">Text (.txt)</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>

            <el-button size="small" type="danger" plain @click="handleDeleteClick(scope.row)" style="margin-left: 5px;">
              <el-icon><Delete /></el-icon>删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <!-- Add pagination later -->

    </el-card>

    <!-- Rename Dialog -->
    <el-dialog
      v-model="renameDialogVisible"
      title="重命名结果"
      width="400px"
      @close="resetRenameForm"
    >
      <el-form :model="renameForm" ref="renameFormRef">
        <el-form-item 
          label="新名称" 
          prop="newName" 
          :rules="[{ required: true, message: '请输入新名称', trigger: 'blur' }]"
        >
          <el-input 
            v-model="renameForm.newName" 
            placeholder="请输入新名称" 
            @keydown.enter.prevent="handleRenameConfirm" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="renameDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="handleRenameConfirm" :loading="renaming">确定</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- Combined View/Edit Result Dialog -->
    <el-dialog 
      v-model="viewEditDialogVisible" 
      :title="`${isEditing ? '编辑' : '查看'}结果: ${currentItem?.name || currentItem?.result_id}`" 
      width="70%"
      top="5vh"
      @close="handleViewEditDialogClose" > <!-- Reset state on close -->
      <div v-loading="isLoadingViewEdit" class="view-edit-dialog-content">
        
        <!-- Editing Mode -->
        <div v-if="isEditing">
          <el-input
            v-model="editedContent"
            type="textarea"
            :rows="15" 
            placeholder="编辑结果内容..."
          />
          <!-- Optionally show original JSON below textarea for reference -->
           <el-collapse style="margin-top: 15px;">
              <el-collapse-item title="原始 JSON 数据 (仅供参考)">
                <pre class="raw-json-preview">{{ 
                  JSON.stringify(currentItemData, null, 2) 
                }}</pre>
              </el-collapse-item>
            </el-collapse>
        </div>

        <!-- Viewing Mode -->
        <div v-else-if="currentItemData && !isLoadingViewEdit">
          <!-- Display main text content prominently -->
          <div v-if="currentItem?.type === 'text_analysis' || currentItem?.type === 'literature_analysis' || currentItem?.type === 'style_transfer'">
            <h4>结果文本:</h4>
            <pre class="result-text-preview">{{ 
              currentItemData.result || 
              currentItemData.content || 
              currentItemData.text || 
              currentItemData.analysis_result || 
              currentItemData.output || 
              currentItemData.output_text || 
              currentItemData.summary || 
              currentItemData.generated_text || 
              '无可用文本内容' 
            }}</pre>
            
            <!-- Show the full JSON in a collapsible section -->
            <el-collapse style="margin-top: 15px;">
              <el-collapse-item title="原始 JSON 数据">
                <pre class="raw-json-preview">{{ 
                  JSON.stringify(currentItemData, null, 2) 
                }}</pre>
              </el-collapse-item>
            </el-collapse>
          </div>
          <!-- Default: Show raw JSON string for other types -->
          <div v-else>
             <pre class="raw-json-preview">{{ 
               JSON.stringify(currentItemData, null, 2) 
             }}</pre>
          </div>
        </div>

        <!-- Loading/Error State -->
        <el-empty v-else-if="!isLoadingViewEdit" description="未能加载结果内容" />
      </div>
      
      <!-- Dialog Footer -->
      <template #footer>
        <span class="dialog-footer">
          <!-- Buttons for Viewing Mode -->
          <template v-if="!isEditing">
            <el-button @click="viewEditDialogVisible = false">关闭</el-button>
            <el-button type="primary" @click="switchToEditMode">编辑</el-button>
          </template>
          <!-- Buttons for Editing Mode -->
          <template v-else>
            <el-button @click="handleEditCancel">取消编辑</el-button>
            <el-button type="success" @click="handleEditSave" :loading="isSavingEdit">保存为新结果</el-button>
          </template>
        </span>
      </template>
    </el-dialog>

  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElTable, ElTableColumn, ElCard, ElButton, ElIcon, ElTag, ElMessage, ElMessageBox, ElDialog, ElForm, ElFormItem, ElInput, ElLoading, ElCollapse, ElCollapseItem, ElDropdown, ElDropdownMenu, ElDropdownItem } from 'element-plus'
import { Refresh, View, Delete, EditPen, Download, ArrowDown } from '@element-plus/icons-vue'
import { Document, Packer, Paragraph, TextRun } from 'docx'
import api from '../services/api' // Corrected path assuming views folder
import { addEmoji } from '../assets/emojiMap' // Corrected path

const resultsData = ref([])
const loading = ref(false)
const renameDialogVisible = ref(false)
const renaming = ref(false)
const renameFormRef = ref(null)
const currentRenameItem = ref(null)

const renameForm = reactive({
  newName: ''
})

const isExporting = ref(false)

// Fetch results data
const fetchResults = async () => {
  loading.value = true
  try {
    const response = await api.getResults() // Use the new API function
    resultsData.value = response.data || []
    ElMessage.success('结果列表已更新')
  } catch (error) {
    console.error("Failed to fetch results:", error)
    ElMessage.error('获取结果列表失败')
    resultsData.value = [] // Clear data on error
  } finally {
    loading.value = false
  }
}

// Format timestamp
const formatTimestamp = (timestamp) => {
  if (!timestamp) return '-'
  try {
    return new Date(timestamp).toLocaleString()
  } catch (e) {
    return timestamp // Return original if parsing fails
  }
}

// Map result type to name and tag type
const resultTypeMap = {
  // 新格式（后端直接保存的type值）
  'text': { name: '文本分析', tag: 'primary' },
  'literature': { name: '文学分析', tag: 'success' },
  'style': { name: '风格迁移', tag: 'warning' },
  'excel': { name: 'Excel分析', tag: 'info' },
  // 旧格式（向后兼容）
  'text_analysis': { name: '文本分析', tag: 'primary' },
  'literature_analysis': { name: '文学分析', tag: 'success' },
  'style_transfer': { name: '风格迁移', tag: 'warning' },
  'excel_analysis': { name: 'Excel分析', tag: 'info' },
  // 编辑后的类型
  'text_edited': { name: '文本分析(已编辑)', tag: 'primary' },
  'literature_edited': { name: '文学分析(已编辑)', tag: 'success' },
}

const getResultTypeName = (type) => {
  return resultTypeMap[type]?.name || type
}

const getResultTypeTag = (type) => {
  return resultTypeMap[type]?.tag || 'info'
}

// --- Rename Logic ---
const openRenameDialog = (row) => {
  currentRenameItem.value = row
  renameForm.newName = row.name || '' // Pre-fill with current name
  renameDialogVisible.value = true
}

const resetRenameForm = () => {
  renameForm.newName = ''
  currentRenameItem.value = null
  renameFormRef.value?.clearValidate()
}

const handleRenameConfirm = async () => {
  if (!currentRenameItem.value || !renameFormRef.value) return

  renameFormRef.value.validate(async (valid) => {
    if (valid) {
      renaming.value = true
      try {
        await api.renameResult(currentRenameItem.value.result_id, renameForm.newName)
        ElMessage.success('重命名成功')
        renameDialogVisible.value = false
        await fetchResults() // Refresh the list after renaming
      } catch (error) {
        console.error("Failed to rename result:", error)
        ElMessage.error(`重命名失败: ${error.response?.data?.detail || error.message}`)
      } finally {
        renaming.value = false
      }
    }
  })
}
// --------------------

// Fetch data when component mounts
onMounted(() => {
  fetchResults()
})

// --- State for Combined View/Edit Dialog --- 
const viewEditDialogVisible = ref(false);
const currentItem = ref(null); // Holds the row data (id, name, type etc.)
const currentItemData = ref(null); // Holds the full fetched JSON data
const isLoadingViewEdit = ref(false);
const isEditing = ref(false); // Controls view/edit mode
const editedContent = ref(''); // Holds the content while editing
const isSavingEdit = ref(false);
// -----------------------------------------

// --- Combined View/Edit Logic --- 
const handleViewClick = async (row) => {
  currentItem.value = row; 
  currentItemData.value = null; 
  isEditing.value = false; 
  editedContent.value = ''; 
  viewEditDialogVisible.value = true;
  isLoadingViewEdit.value = true;
  try {
    const response = await api.getResultDetails(row.result_id);
    currentItemData.value = response.data; 
    
    // 优化的文本提取逻辑
    let extractedText = '';
    if (currentItemData.value) {
        console.log("[ViewClick] Attempting to extract text from:", currentItemData.value);
        
        // 1. 优先检查深度嵌套路径（文笔分析/深度分析报告）
        if (currentItemData.value.result) {
            if (typeof currentItemData.value.result === 'string') {
                // 如果result本身就是字符串（文笔分析的情况）
                extractedText = currentItemData.value.result;
                console.log("[ViewClick] Found text in result (string)");
            } else if (typeof currentItemData.value.result === 'object') {
                // 如果result是对象（文本分析的情况）
                // 尝试提取深度分析报告
                if (typeof currentItemData.value.result.deep_analysis_report === 'string') {
                    extractedText = currentItemData.value.result.deep_analysis_report;
                    console.log("[ViewClick] Found text in result.deep_analysis_report");
                } else if (typeof currentItemData.value.result.analysis_report === 'string') {
                    extractedText = currentItemData.value.result.analysis_report;
                    console.log("[ViewClick] Found text in result.analysis_report");
                } else {
                    // 如果没有报告字段，尝试将整个result对象格式化为可读文本
                    try {
                        const resultObj = currentItemData.value.result;
                        const sections = [];
                        
                        // 提取各个分析维度的内容
                        if (resultObj.sentiment) {
                            sections.push(`## 情感分析\n${JSON.stringify(resultObj.sentiment, null, 2)}`);
                        }
                        if (resultObj.readability) {
                            sections.push(`## 可读性分析\n${JSON.stringify(resultObj.readability, null, 2)}`);
                        }
                        if (resultObj.text_stats) {
                            sections.push(`## 文本统计\n${JSON.stringify(resultObj.text_stats, null, 2)}`);
                        }
                        if (resultObj.word_frequency) {
                            sections.push(`## 词频分析\n${JSON.stringify(resultObj.word_frequency, null, 2)}`);
                        }
                        if (resultObj.sentence_pattern) {
                            sections.push(`## 句式分析\n${JSON.stringify(resultObj.sentence_pattern, null, 2)}`);
                        }
                        if (resultObj.keyword_extraction) {
                            sections.push(`## 关键词提取\n${JSON.stringify(resultObj.keyword_extraction, null, 2)}`);
                        }
                        if (resultObj.language_features) {
                            sections.push(`## 语言特征\n${JSON.stringify(resultObj.language_features, null, 2)}`);
                        }
                        
                        if (sections.length > 0) {
                            extractedText = sections.join('\n\n');
                            console.log("[ViewClick] Formatted result object into readable text");
                        } else {
                            // 如果没有识别的字段，直接JSON化
                            extractedText = JSON.stringify(resultObj, null, 2);
                            console.log("[ViewClick] Stringified entire result object");
                        }
                    } catch (e) {
                        console.error("[ViewClick] Error formatting result object:", e);
                        extractedText = JSON.stringify(currentItemData.value.result, null, 2);
                    }
                }
            }
        }
        
        // 2. 回退到顶层字段（如果上面没有提取到内容）
        if (!extractedText) {
            if (typeof currentItemData.value.content === 'string') { 
                extractedText = currentItemData.value.content; 
                console.log("[ViewClick] Found text in content"); 
            }
            else if (typeof currentItemData.value.text === 'string') { 
                extractedText = currentItemData.value.text; 
                console.log("[ViewClick] Found text in text"); 
            }
            else if (typeof currentItemData.value.analysis_result === 'string') { 
                extractedText = currentItemData.value.analysis_result; 
                console.log("[ViewClick] Found text in analysis_result"); 
            }
            else if (typeof currentItemData.value.output === 'string') { 
                extractedText = currentItemData.value.output; 
                console.log("[ViewClick] Found text in output"); 
            }
            else if (typeof currentItemData.value.output_text === 'string') { 
                extractedText = currentItemData.value.output_text; 
                console.log("[ViewClick] Found text in output_text"); 
            }
            else if (typeof currentItemData.value.summary === 'string') { 
                extractedText = currentItemData.value.summary; 
                console.log("[ViewClick] Found text in summary"); 
            }
            else if (typeof currentItemData.value.generated_text === 'string') { 
                extractedText = currentItemData.value.generated_text; 
                console.log("[ViewClick] Found text in generated_text"); 
            }
        }

        editedContent.value = extractedText;
        
        // 只有在完全无法提取时才显示警告
        if (!editedContent.value) {
            console.warn("[ViewClick] Could not automatically extract text content for editing.");
            ElMessage.warning("未能自动提取文本内容进行编辑，将显示完整JSON数据。");
            // 最后的回退：显示整个JSON
            try {
                editedContent.value = JSON.stringify(currentItemData.value, null, 2);
            } catch (e) {
                editedContent.value = '无法序列化数据';
            }
        }
    }
  } catch (error) {
     console.error("Failed to fetch result details:", error);
     ElMessage.error("加载结果详情失败: " + (error.response?.data?.detail || error.message));
     currentItemData.value = { error: "加载失败", details: error.message }; 
  } finally {
    isLoadingViewEdit.value = false;
  }
};

const switchToEditMode = () => {
  // 使用已经在handleViewClick中提取好的内容
  // 如果editedContent已经有内容，直接使用
  if (editedContent.value) {
    isEditing.value = true;
    return;
  }
  
  // 如果没有内容，尝试重新提取
  let textToEdit = '';
  if (currentItemData.value) {
      // 优先尝试从result字段提取
      if (currentItemData.value.result) {
          if (typeof currentItemData.value.result === 'string') {
              textToEdit = currentItemData.value.result;
          } else if (typeof currentItemData.value.result === 'object') {
              // 尝试提取报告字段
              textToEdit = currentItemData.value.result.deep_analysis_report || 
                          currentItemData.value.result.analysis_report || 
                          '';
              
              // 如果没有报告字段，格式化整个对象
              if (!textToEdit) {
                  try {
                      textToEdit = JSON.stringify(currentItemData.value.result, null, 2);
                  } catch (e) {
                      textToEdit = '无法序列化对象';
                  }
              }
          }
      }
      
      // 回退到其他字段
      if (!textToEdit) {
          textToEdit = currentItemData.value.content || 
                       currentItemData.value.text || 
                       currentItemData.value.analysis_result || 
                       currentItemData.value.output || 
                       currentItemData.value.output_text || 
                       currentItemData.value.summary || 
                       currentItemData.value.generated_text || 
                       (typeof currentItemData.value === 'string' ? currentItemData.value : '');
      }
      
      // 最后的回退：序列化整个对象
      if (!textToEdit && typeof currentItemData.value === 'object') {
          try {
              textToEdit = JSON.stringify(currentItemData.value, null, 2);
              ElMessage.info('未找到主要文本字段，将编辑整个JSON内容。');
          } catch (e) { 
              textToEdit = '无法序列化对象进行编辑'; 
          }
      }
  }
  
  editedContent.value = textToEdit; 
  isEditing.value = true;
};

const handleEditSave = async () => {
  if (!currentItem.value || editedContent.value === null || editedContent.value === undefined) {
    ElMessage.warning('没有当前项或编辑内容为空');
    return;
  }
  
  isSavingEdit.value = true;
  console.log(`[handleEditSave] Saving edited content from original ID ${currentItem.value.result_id} as new result.`);

  // Construct payload for the saveNewAnalysisResult function
  // Needs to match backend's SaveAnalysisPayload roughly
  const payload = {
    result: editedContent.value, // The edited content is the main result
    text_summary: editedContent.value.substring(0, 150) + (editedContent.value.length > 150 ? '...' : ''),
    timestamp: new Date().toISOString(),
    // Try to retain original type, provider, model, adding suffix to type
    analysis_type: (currentItem.value.type || 'unknown') + '_edited',
    provider: currentItemData.value?.provider || null, 
    model: currentItemData.value?.model || currentItem.value?.model_info?.split(' ')[1] || null, // Try to extract model
    original_text: editedContent.value, // For the new record, this edited text is the 'original'
    source_info: `Edited from: ${currentItem.value.result_id} - ${currentItem.value.name || '未命名'}` // Add lineage info
  };

  console.log("[handleEditSave] Payload for saveNewAnalysisResult:", payload);

  try {
    // Call the function that POSTs to create a new record
    const response = await api.saveNewAnalysisResult(payload);
    
    console.log("[handleEditSave] Save New Result Response:", response);

    if (response && response.data && response.data.id) {
      ElMessage.success(`编辑后的内容已保存为新结果 (ID: ${response.data.id})`);
      viewEditDialogVisible.value = false; // Close the dialog
      await fetchResults(); // Refresh the table data
    } else {
      console.error("[handleEditSave] Save response did not contain a new result ID:", response);
      ElMessage.error('保存成功，但未能获取新结果ID。');
       // Keep dialog open? Or close? Decide based on UX preference.
       // viewEditDialogVisible.value = false;
    }
  } catch (error) {
    console.error("[handleEditSave] Failed to save edited content as new result:", error);
    ElMessage.error(`保存新结果失败: ${error.response?.data?.detail || error.message || '请检查后端服务。'}`);
    // Keep dialog open and editable on error
  } finally {
    isSavingEdit.value = false;
  }
};

const handleEditCancel = () => {
  isEditing.value = false;
  editedContent.value = ''; // Clear edited content
};

const handleViewEditDialogClose = () => {
  // Reset state when dialog is closed completely
  isEditing.value = false;
  currentItem.value = null;
  currentItemData.value = null;
  editedContent.value = '';
}
// --------------------------

// --- Delete Logic ---
const handleDeleteClick = async (row) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除结果 "${row.name || row.result_id}" 吗？此操作无法撤销。`,
      '确认删除',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
      }
    );
    
    // User confirmed deletion
    const loadingInstance = ElLoading.service({
      lock: true,
      text: '正在删除...',
      background: 'rgba(0, 0, 0, 0.7)',
    });
    
    try {
      await api.deleteResult(row.result_id);
      ElMessage.success('结果删除成功！');
      fetchResults(); // Refresh the list
    } catch (error) { 
      console.error("Failed to delete result:", error);
      ElMessage.error("删除失败: " + (error.response?.data?.detail || error.message));
    } finally {
      loadingInstance.close();
    }

  } catch (cancel) {
    // User clicked cancel or closed the dialog
    ElMessage.info('已取消删除');
  }
};
// -------------------

// --- Helper function to trigger file download --- 
const triggerDownload = (blob, filename) => {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.style.display = 'none';
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
};

// --- Export Logic --- 
const handleExportClick = async (row, format) => {
  isExporting.value = true;
  const loadingInstance = ElLoading.service({ text: `正在准备导出 ${format.toUpperCase()} 文件...` });
  
  try {
    // 1. Fetch full data
    const response = await api.getResultDetails(row.result_id);
    const data = response.data;
    if (!data) {
      throw new Error("未能获取结果数据");
    }

    // 2. Extract main text content (using the robust logic)
    let textContent = '';
    if (data.result) {
        if (typeof data.result.analysis_report === 'string') { textContent = data.result.analysis_report; }
        else if (typeof data.result.deep_analysis_report === 'string') { textContent = data.result.deep_analysis_report; }
    }
    if (!textContent) {
        if (typeof data.result === 'string') { textContent = data.result; }
        else if (typeof data.content === 'string') { textContent = data.content; }
        else if (typeof data.text === 'string') { textContent = data.text; }
        else if (typeof data.analysis_result === 'string') { textContent = data.analysis_result; }
        else if (typeof data.output === 'string') { textContent = data.output; }
        else if (typeof data.output_text === 'string') { textContent = data.output_text; }
        else if (typeof data.summary === 'string') { textContent = data.summary; }
        else if (typeof data.generated_text === 'string') { textContent = data.generated_text; }
    }

    if (!textContent) {
      ElMessage.warning("未能找到可导出的主要文本内容。");
      loadingInstance.close(); // Ensure loading closes
      isExporting.value = false;
      return; 
    }

    // 3. Generate file based on format
    const filenameBase = row.name || row.result_id;

    if (format === 'md') {
      const blob = new Blob([textContent], { type: 'text/markdown;charset=utf-8' });
      triggerDownload(blob, `${filenameBase}.md`);
    } else if (format === 'docx') {
      try {
        const doc = new Document({
          sections: [{
            properties: {}, // Default properties
            children: [
              // Split text into paragraphs based on newlines for better formatting
              ...textContent.split('\n').map(line => 
                new Paragraph({ children: [new TextRun(line)] })
              )
            ],
          }],
        });
        const blob = await Packer.toBlob(doc);
        triggerDownload(blob, `${filenameBase}.docx`);
      } catch (docxError) {
         console.error("Error generating DOCX:", docxError);
         ElMessage.error("生成 DOCX 文件失败，请确保已安装 'docx' 库并查看控制台。" + docxError);
      }
    } else if (format === 'txt') { // Handle TXT export
      const blob = new Blob([textContent], { type: 'text/plain;charset=utf-8' });
      triggerDownload(blob, `${filenameBase}.txt`);
    }

    ElMessage.success(`已开始下载 ${format.toUpperCase()} 文件`);

  } catch (error) {
    console.error("导出文件时出错:", error);
    ElMessage.error(`导出失败: ${error.message}`);
  } finally {
    isExporting.value = false;
    loadingInstance.close();
  }
};
// -------------------

</script>

<style lang="scss" scoped>
.data-terminal {
  padding: 15px;
}

.page-card {
  border: none;
  box-shadow: var(--el-box-shadow-light);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;

  h2 {
    margin: 0;
    font-size: 1.2em;
    font-weight: 600;
  }
}

/* Add margin to buttons inside table cell */
.el-table .cell .el-button {
  margin-right: 5px; 
}

/* Ensure table header is visible in dark mode */
:deep(.el-table__header-wrapper) {
  th {
    background-color: var(--el-fill-color-light); 
  }
}

:deep(.dark .el-table__header-wrapper) {
 th {
    background-color: var(--el-fill-color-lighter); 
  }
}

.rename-btn {
  margin-left: 8px; // Add some space
  // Make it subtle until hovered
  opacity: 0.5;
  transition: opacity 0.2s ease-in-out;
  
  &:hover {
    opacity: 1;
  }
}

/* Add styles for the raw JSON preview pre tag */
.raw-json-preview {
  white-space: pre-wrap;   /* Preserve whitespace, but wrap lines */
  word-break: break-all;    /* Break long words/strings if needed */
  background-color: var(--el-fill-color-lighter); /* Optional: slight background */
  padding: 10px;
  border-radius: 4px;
  max-height: 70vh;        /* Limit height and add scroll if needed */
  overflow-y: auto;
  font-family: monospace;   /* Use monospace font for code-like view */
}

/* Class for the text preview inside view dialog */
.result-text-preview {
  white-space: pre-wrap;   /* Preserve whitespace, wrap lines */
  word-break: break-word;   /* Break words nicely */
  background-color: var(--el-fill-color-lightest);
  padding: 10px;
  border-radius: 4px;
  max-height: 35vh;        /* Limit height */
  overflow-y: auto;
  font-family: sans-serif; /* Use regular font for text */
  line-height: 1.6;
}

.view-edit-dialog-content {
  max-height: 75vh; /* Adjust overall dialog content height */
  overflow-y: auto;
}

/* Ensure dropdown button aligns nicely */
.el-dropdown {
  vertical-align: middle; /* Align with other buttons */
}

</style> 