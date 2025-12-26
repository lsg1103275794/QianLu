<template>
  <div class="api-manager">
    <el-card class="feature-card">
      <template #header>
        <div class="gm-card-header">
          <div class="left-section">
            <h2 class="feature-title">{{ addEmoji('API 管理', 'menu', 'api-manager') }}</h2>
          </div>
        </div>
      </template>

      <el-container class="manager-container">
        <!-- 左侧导航 -->
        <el-aside width="220px" class="sidebar">
          <div class="sidebar-header">
            <h3 class="sidebar-title">API 配置</h3>
            <el-button 
              type="primary" 
              :icon="Plus" 
              circle 
              size="small" 
              @click="openAddApiDialog" 
              title="添加新的API提供商"
              class="add-api-button"
            />
          </div>
          <el-menu
            :default-active="selectedSection"
            class="config-menu"
            @select="handleSectionSelect"
          >
            <el-menu-item index="global">通用设置</el-menu-item>
            <el-sub-menu index="providers">
              <template #title><span>API 提供商</span></template>
              <div v-if="loadingProviders" class="loading-providers">
                <el-skeleton :rows="3" animated />
              </div>
              <el-menu-item 
                v-else
                v-for="provider in providerList" 
                :key="provider.name" 
                :index="provider.name"
              >
                {{ getEmoji('provider', provider.name, '🔌') }} {{ provider.display_name || provider.name }}
              </el-menu-item>
              <el-menu-item v-if="!loadingProviders && providerList.length === 0" index="no-providers" disabled>
                未找到提供商
              </el-menu-item>
            </el-sub-menu>
            <div class="add-provider-button-container">
               <el-button 
                 type="success" 
                 :icon="Plus" 
                 @click="openAddApiDialog" 
                 plain 
                 class="add-provider-btn"
                >
                 添加提供商
               </el-button>
            </div>
          </el-menu>
        </el-aside>

        <!-- 右侧内容区 -->
        <el-main class="content-area">
          <div v-if="loadingSettings || loadingProviders" class="loading-settings">
             <el-skeleton :rows="8" animated />
          </div>
          <div v-else>
              <!-- Determine if anything is configurable for the save button later -->
              <h3 v-if="selectedSection === 'global'">通用设置</h3>
              <h3 v-else-if="selectedProviderData">{{ selectedProviderData.display_name || selectedSection }} 配置</h3>
              <h3 v-else-if="selectedSection !== 'global' && !selectedProviderData">未找到提供商 {{ selectedSection }}</h3>

              <!-- Display Area -->
              <!-- Case 1: Global Settings Selected -->
              <template v-if="selectedSection === 'global'">
                  <ConfigForm
                     v-if="currentSchemaItems.length > 0"
                     :schema-items="currentSchemaItems"
                     :current-values="currentSettings"
                     @update:values="handleFormUpdate"
                  />
                  <el-empty v-else-if="configSchema && configSchema.global_settings !== undefined" description="暂无全局配置项" /> <!-- Check schema exists before empty -->
                  <el-alert v-else title="无法加载全局设置定义" type="warning" :closable="false"></el-alert>
              </template>

              <!-- Case 2: Provider Selected -->
              <template v-else-if="selectedSection !== 'global'">
                  <template v-if="selectedProviderData"> 
                      <ConfigForm
                         v-if="currentSchemaItems.length > 0"
                         :schema-items="currentSchemaItems"
                         :current-values="currentSettings"
                         @update:values="handleFormUpdate"
                      />
                      <!-- Show warning only if NO config items AND cannot determine default params (they are null) -->
                      <el-alert v-if="currentSchemaItems.length === 0 && defaultTemperature === null && defaultMaxTokens === null && configSchema?.provider_settings?.[selectedSection] === undefined " 
                                :title="`无法加载或暂无 ${selectedProviderData.display_name || selectedSection} 的配置定义`" type="warning" :closable="false"></el-alert>
                  </template>
                   <el-alert v-else :title="`未找到提供商 ${selectedSection} 的配置数据`" type="info" :closable="false"></el-alert> <!-- Show if provider data missing -->
              </template>

              <!-- Case 3: Initial State (No Selection Yet or invalid state) -->
              <el-empty v-else description="请在左侧选择一个配置项" />

              <!-- Save Button - Show if global has items OR if provider section is selected AND has data -->
               <div class="save-button-container" v-if="(selectedSection === 'global' && currentSchemaItems.length > 0) || (selectedSection !== 'global' && selectedProviderData)">
                  <el-button type="primary" @click="saveSettings" :loading="isSaving" :disabled="!isDirty">保存更改</el-button>
                  <span v-if="!isDirty" class="no-changes-hint">（无更改）</span>
               </div>
          </div>
        </el-main>
      </el-container>
    </el-card>

    <!-- 添加对话框 -->
    <AddNewApiDialog ref="addApiDialogRef" @success="handleAddApiSuccess" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue';
import { ElContainer, ElAside, ElMain, ElMenu, ElMenuItem, ElSubMenu, ElSkeleton, ElEmpty, ElButton, ElMessage, ElAlert } from 'element-plus';
import { Plus } from '@element-plus/icons-vue';
// 导入API服务
import api from '../../services/api'; 
// --- 导入 ConfigForm 组件 --- 
import ConfigForm from '../common/ConfigForm.vue'; 
// --- 导入 getEmoji 和 addEmoji --- 
import { getEmoji, addEmoji } from '../../assets/emojiMap'; // 修正路径
// --- 导入 AddNewApiDialog --- 
import AddNewApiDialog from '../dialogs/AddNewApiDialog.vue';
import { getProvidersMeta } from '../../services/settingsService';

// --- 状态变量 --- 
const loadingProviders = ref(true);
const loadingSettings = ref(false);
const allProviderSettings = ref({}); // 存储从 /api/settings/providers 获取的所有数据
const providerList = ref([]); // 仅用于侧边栏显示 { name: string, display_name: string }
const selectedSection = ref('global'); // 当前选中的部分 ('global' 或 provider name)
const configSchema = ref(null); // 存储从 API 获取的 Schema
const currentSettings = ref({}); // 当前选中部分的配置值 (.env 格式)
const formValues = ref({}); // 只存储 ConfigForm 的值
const globalSettings = ref({}); 
const isSaving = ref(false); 
const initialValues = ref({}); // 只存储 ConfigForm 的初始值
const addApiDialogRef = ref(null); // 添加对对话框组件的引用
const providersMeta = ref([]);

// --- 新增：默认高级参数的状态变量 ---
const defaultTemperature = ref(null);
const defaultMaxTokens = ref(null);
const initialDefaultTemperature = ref(null); // 用于 dirty 检查
const initialDefaultMaxTokens = ref(null); // 用于 dirty 检查

// --- 计算属性 --- 

// 获取当前选中部分的 Schema 定义
const currentSchemaItems = computed(() => {
  if (!configSchema.value) return [];
  let items = [];
  if (selectedSection.value === 'global') {
    items = configSchema.value.global_settings || [];
  } else if (configSchema.value.provider_settings && configSchema.value.provider_settings[selectedSection.value]) {
    const providerSchema = configSchema.value.provider_settings[selectedSection.value];
    items = providerSchema.config_items || [];
  }
  // 去重：同一 env_var 只保留第一个
  const seen = new Set();
  return items.filter(item => {
    if (seen.has(item.env_var)) return false;
    seen.add(item.env_var);
    return true;
  });
});

// 获取当前选中提供商的完整数据
const selectedProviderData = computed(() => {
  if (selectedSection.value === 'global' || !allProviderSettings.value) {
    return null;
  }
  return allProviderSettings.value[selectedSection.value] || null;
});

// 判断配置是否有修改 (dirty)
const isDirty = computed(() => {
  const formDirty = JSON.stringify(initialValues.value) !== JSON.stringify(formValues.value);
  let defaultsDirty = false;
  if (selectedSection.value !== 'global') {
    // 注意：比较时处理 null/undefined 和数字/字符串类型
    const tempChanged = String(initialDefaultTemperature.value ?? '') !== String(defaultTemperature.value ?? '');
    const tokensChanged = String(initialDefaultMaxTokens.value ?? '') !== String(defaultMaxTokens.value ?? '');
    defaultsDirty = tempChanged || tokensChanged;
  }
  // console.log(`isDirty check: formDirty=${formDirty}, defaultsDirty=${defaultsDirty}`);
  return formDirty || defaultsDirty;
});

// --- 新增：UI State Persistence --- 
// const UI_STATE_KEY = 'api-manager';

// Remove unused function loadUiState
// const loadUiState = async () => { ... };

// Remove unused function saveCurrentUiState
// const saveCurrentUiState = async () => { ... };

// --- End UI State Persistence ---

// --- 方法 --- 

// 加载 Schema 定义
const loadConfigSchema = async () => {
  try {
    const response = await api.getSettingsSchema(); // 假设 api.js 里有这个方法
    configSchema.value = response.data;
    console.log('>>> DEBUG: Loaded Config Schema:', JSON.stringify(configSchema.value, null, 2)); // 添加日志
  } catch (error) {
    console.error("加载配置 Schema 失败:", error);
    ElMessage.error('加载配置定义失败');
  }
};

// 加载所有提供商及其配置 (.env 值)
const loadProviderSettings = async () => {
  loadingProviders.value = true;
  loadingSettings.value = true; // 同时开始加载设置
  try {
    // 注意：现在 /api/settings/providers 返回的是所有提供商的 .env 设置
    const response = await api.getProviderSettings(); 
    allProviderSettings.value = response.data || {};
    console.log('>>> DEBUG: Loaded Provider Settings:', JSON.stringify(allProviderSettings.value, null, 2)); // 添加日志
    
    // 更新侧边栏列表
    providerList.value = Object.entries(allProviderSettings.value).map(([name, config]) => ({
      name: name,
      display_name: config.display_name || name // 使用返回的 display_name
    }));
    providerList.value.sort((a, b) => (a.display_name || a.name).localeCompare(b.display_name || b.name)); // 按名称排序

    // --- Add Log --- 
    console.log('>>> DEBUG: Final providerList for sidebar:', JSON.parse(JSON.stringify(providerList.value)));
    // --- End Log ---

    // 加载全局设置 (例如默认提供商)
    // 注意：全局设置也可能包含在 allProviderSettings['global'] 或单独的 API 端点
    // 这里我们假设 `/api/settings/global` 仍然有效，用于获取如 default_provider
    try {
        const globalResponse = await api.getGlobalSettings();
        globalSettings.value = globalResponse.data || {};
        // 如果需要将全局设置也显示在右侧
        if (selectedSection.value === 'global') {
            // currentSettings 需要是 .env 变量的格式
            currentSettings.value = { 
                DEFAULT_PROVIDER: globalSettings.value.default_provider
                // ... 其他可能的全局 .env 变量
             };
        }
    } catch (globalError) {
        console.error("获取全局设置失败:", globalError);
        // 如果需要，给 currentSettings 设置空对象
        if (selectedSection.value === 'global') {
            currentSettings.value = {};
        }
    }
    
    // 如果初始选中的是某个提供商，加载其设置
    if (selectedSection.value !== 'global' && allProviderSettings.value[selectedSection.value]) {
         currentSettings.value = { ...allProviderSettings.value[selectedSection.value] };
    }

    // 更新当前显示的设置
    updateCurrentSettingsAndForm(selectedSection.value);

  } catch (error) {
    console.error("加载提供商配置失败:", error);
    allProviderSettings.value = {};
    providerList.value = [];
    currentSettings.value = {};
    formValues.value = {}; 
    initialValues.value = {};
    defaultTemperature.value = null;
    defaultMaxTokens.value = null;
    initialDefaultTemperature.value = null;
    initialDefaultMaxTokens.value = null;
    // 可以添加错误提示
  } finally {
    loadingProviders.value = false;
    loadingSettings.value = false;
    // 确保 formValues 在加载后被正确初始化
    if (Object.keys(currentSettings.value).length > 0) {
         formValues.value = { ...currentSettings.value };
         initialValues.value = { ...currentSettings.value }; // 初始化 dirty 检查基线
    }
  }
};

// 并行加载 Schema、Provider Settings、Providers Meta
const loadAllProviderData = async () => {
  loadingSettings.value = true;
  try {
    await Promise.all([
      loadConfigSchema(),
      loadProviderSettings(),
      (async () => {
        const metaResp = await getProvidersMeta();
        providersMeta.value = metaResp.data || [];
      })()
    ]);
  } catch (error) {
    console.error('加载元数据失败:', error);
  } finally {
    loadingSettings.value = false;
  }
};

// 更新右侧显示的设置和表单值
const updateCurrentSettingsAndForm = (section) => {
    let newCurrentSettings = {};
    let temp = null;
    let tokens = null;

    if (section === 'global') {
        // 全局设置目前只处理 DEFAULT_PROVIDER
        newCurrentSettings = { 
            DEFAULT_PROVIDER: globalSettings.value.default_provider 
            // 如果将来 schema 定义了全局的默认参数，也在这里加载
        };
    } else if (allProviderSettings.value[section]) {
        // 提供商设置
        const providerConfig = { ...allProviderSettings.value[section] };
        console.log(`>>> DEBUG: Raw providerConfig for [${section}]:`, JSON.stringify(providerConfig, null, 2)); // 添加日志
        
        // 提取默认参数（假设它们也存储在 .env 中并返回了）
        // 使用我们约定的键名，并转换为数字 (如果存在)
        if ('DEFAULT_TEMPERATURE' in providerConfig) {
            const rawTemp = providerConfig['DEFAULT_TEMPERATURE'];
            temp = (rawTemp !== null && rawTemp !== '') ? Number(rawTemp) : null;
            if (isNaN(temp)) temp = null; // 处理无效数字
             delete providerConfig['DEFAULT_TEMPERATURE']; // 从主配置中移除，避免传入 ConfigForm
        }
        if ('DEFAULT_MAX_TOKENS' in providerConfig) {
            const rawTokens = providerConfig['DEFAULT_MAX_TOKENS'];
            tokens = (rawTokens !== null && rawTokens !== '') ? Number(rawTokens) : null;
             if (isNaN(tokens)) tokens = null; // 处理无效数字
             delete providerConfig['DEFAULT_MAX_TOKENS']; // 从主配置中移除
        }

        // 移除 display_name，因为它不是一个真正的 env 变量
        delete providerConfig.display_name; 

        // 补全缺失参数：用 providersMeta 的 env_prefix 拼接标准参数名
        const meta = providersMeta.value.find(m => m.standard_name === section);
        if (meta && meta.env_prefix) {
          const standardKeys = ['API_KEY','ENDPOINT','DEFAULT_MODEL','TEMPERATURE','MAX_TOKENS','TOP_P','REQUEST_TIMEOUT'];
          for (const key of standardKeys) {
            const envKey = `${meta.env_prefix}${key}`;
            if (!(envKey in providerConfig)) {
              providerConfig[envKey] = key === 'REQUEST_TIMEOUT' ? 60 : '';
            }
          }
        }

        newCurrentSettings = providerConfig;
        console.log(`>>> DEBUG: Processed newCurrentSettings for [${section}]:`, JSON.stringify(newCurrentSettings, null, 2)); // 添加日志

    } else {
        newCurrentSettings = {}; // 未找到或未选择提供商
    }

    // 更新状态
    currentSettings.value = newCurrentSettings;
    formValues.value = { ...newCurrentSettings }; // ConfigForm 的值
    initialValues.value = { ...newCurrentSettings }; // ConfigForm 的初始值
    
    defaultTemperature.value = temp;
    defaultMaxTokens.value = tokens;
    initialDefaultTemperature.value = temp; // 设置初始值用于 dirty 检查
    initialDefaultMaxTokens.value = tokens; // 设置初始值用于 dirty 检查

    loadingSettings.value = false;
};

// 处理侧边栏选择
const handleSectionSelect = (index) => {
  if (index === 'no-providers') return; // Ignore disabled item
  selectedSection.value = index;
  // 使用 localStorage 简单记录，防止刷新丢失 (UI State 会覆盖)
  localStorage.setItem('apiManagerSelectedSection', index);
  updateCurrentSettingsAndForm(index); // 更新右侧显示
};

// 处理 ConfigForm 更新的值
const handleFormUpdate = (updatedValues) => {
  formValues.value = updatedValues;
  // console.log('ApiManager: Form values updated', formValues.value);
};

// 保存设置
const saveSettings = async () => {
  isSaving.value = true;
  // 基础设置来自 ConfigForm (假定其键已经是正确的 ENV_VAR 名称)
  const baseSettings = { ...formValues.value }; 

  // 高级参数（默认温度和 Token）
  const defaultParams = {};
  const providerName = selectedSection.value;
  const envPrefix = providerName.toUpperCase(); 

  if (providerName !== 'global') {
      // 构建带前缀的默认参数键
      const tempKey = `${envPrefix}_DEFAULT_TEMPERATURE`;
      const tokensKey = `${envPrefix}_DEFAULT_MAX_TOKENS`;
      
      if (defaultTemperature.value !== null && defaultTemperature.value !== undefined) {
          defaultParams[tempKey] = String(defaultTemperature.value); // 确保是字符串
      }
      if (defaultMaxTokens.value !== null && defaultMaxTokens.value !== undefined) {
          defaultParams[tokensKey] = String(defaultMaxTokens.value); // 确保是字符串
      }
  }
  
  // --- FIX: 直接合并 baseSettings 和 defaultParams --- 
  // 假设 baseSettings 的键已经是正确的 ENV_VAR 名称 (来自 ConfigForm)
  const envVarsToSave = { ...baseSettings, ...defaultParams };
  
  // 移除可能存在的 display_name (以防万一)
  if (envVarsToSave.display_name) {
      delete envVarsToSave.display_name;
  }

  // 检查并转换布尔值 (来自 ConfigForm 的 Checkbox 可能已经是 boolean)
  const providerSchema = configSchema.value?.provider_settings?.[providerName]?.config_items || [];
  providerSchema.forEach(item => {
       if (item.type === 'boolean' && item.env_var in envVarsToSave) {
            envVarsToSave[item.env_var] = String(!!envVarsToSave[item.env_var]);
       } else if (item.type === 'boolean' && !(item.env_var in envVarsToSave)) {
            envVarsToSave[item.env_var] = 'false'; 
       }
  });
  
  // --- FIX: Don't save API Key if it wasn't changed (still masked value) --- 
  for (const key in envVarsToSave) {
      if (key.includes('_API_KEY')) {
          const currentValue = envVarsToSave[key];
          const initialValue = initialValues.value[key]; 
          
          if (currentValue === initialValue) {
              console.log(`API Key field '${key}' was not modified. Removing from save payload.`);
              delete envVarsToSave[key];
          } else {
               console.log(`API Key field '${key}' was modified. Including in save payload.`);
          }
      }
  }
  // ----------------------------------------------------------------------

  console.log('准备保存的环境变量 (过滤后):', envVarsToSave);

  if (Object.keys(envVarsToSave).length === 0) {
       ElMessage.info('没有检测到需要保存的配置项。');
       isSaving.value = false;
       return;
  }

  try {
    await api.saveSettings(envVarsToSave); // 发送包含正确 ENV_VAR 键的字典
    
    ElMessage.success('配置已成功保存！');
    await loadAllProviderData(); // 重新加载以更新状态和重置 dirty
  } catch (error) {
    console.error('保存配置失败:', error);
    const errorMsg = error.response?.data?.detail || error.message || '保存失败，请检查后端日志';
    ElMessage.error(errorMsg);
  } finally {
    isSaving.value = false;
  }
};

// 打开添加API对话框
const openAddApiDialog = () => {
  if (addApiDialogRef.value) {
    addApiDialogRef.value.openDialog();
  }
};

// 处理添加成功事件
const handleAddApiSuccess = async (newData) => {
  console.log('New API added:', newData);
  // 重新加载提供商列表和配置以包含新的提供商
  await loadAllProviderData();
  // 可选：自动选中新添加的提供商
  if (newData?.name) {
      // 等待 DOM 更新后设置选中
      // nextTick(() => {
      //    selectedSection.value = newData.name;
      //    updateCurrentSettingsAndForm(newData.name);
      // });
      // 简单起见，先只刷新列表
  }
};

// --- 生命周期钩子 --- 
onMounted(async () => {
  // 恢复上次选择 (现在由 loadUiState 处理，但保留 localStorage 作为快速回退)
  selectedSection.value = localStorage.getItem('apiManagerSelectedSection') || 'global';
  
  // 并行加载 Schema 和 Provider Settings
  await loadAllProviderData();
  
  // 1. provider/model 选择时写入 localStorage
  watch(selectedSection, (newProvider, oldProvider) => {
    if (newProvider && newProvider !== 'global') {
      localStorage.setItem('api_manager_last_provider', newProvider);
      // 切换 provider 时清除 model 缓存
      localStorage.removeItem(`api_manager_last_model_${oldProvider}`);
    }
  });
  watch(() => formValues.value.model, (newModel) => {
    if (selectedSection.value && selectedSection.value !== 'global' && newModel) {
      localStorage.setItem(`api_manager_last_model_${selectedSection.value}`, newModel);
    }
  });

  // 2. 页面加载时自动恢复 provider/model
  const lastProvider = localStorage.getItem('api_manager_last_provider');
  if (lastProvider && providerList.value.some(p => p.name === lastProvider)) {
    selectedSection.value = lastProvider;
    const lastModel = localStorage.getItem(`api_manager_last_model_${lastProvider}`);
    if (lastModel) {
      formValues.value.model = lastModel;
  }
    updateCurrentSettingsAndForm(lastProvider);
  }
});

onUnmounted(() => {
  // 页面离开时保存当前 UI 状态
  // saveCurrentUiState();
});

// 3. provider/model 选择框旁加刷新按钮，点击清除缓存并强制拉取
const refreshProvider = async () => {
  localStorage.removeItem('api_manager_last_provider');
  selectedSection.value = 'global';
  await loadAllProviderData();
};
const refreshModel = async () => {
  if (selectedSection.value && selectedSection.value !== 'global') {
    localStorage.removeItem(`api_manager_last_model_${selectedSection.value}`);
    formValues.value.model = '';
    await updateCurrentSettingsAndForm(selectedSection.value);
  }
};

// eslint-disable-next-line no-unused-vars
void refreshProvider;
// eslint-disable-next-line no-unused-vars
void refreshModel;

</script>

<style lang="scss" scoped>
.api-manager {
  margin: 0 auto;
  padding: 20px;
}

.feature-card {
  margin-bottom: 20px;
}

.gm-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;

  .left-section {
    display: flex;
    align-items: center;
    gap: 12px;

    h2 {
      margin: 0;
      font-size: 18px;
      font-weight: 600;
    }
  }
}

.manager-container {
  border: none;
  border-radius: 0;
  overflow: visible;
  background-color: transparent;
}

.sidebar {
  border-right: 1px solid var(--el-border-color-light);
  background-color: var(--el-bg-color);
  padding-top: 0;
  padding-bottom: 15px;
  padding-left: 0;
  padding-right: 0;

  .sidebar-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 10px 20px;
    border-bottom: 1px solid var(--el-border-color-lighter);
    margin-bottom: 10px;
  }

  .sidebar-title {
    font-size: 1.1rem;
    font-weight: 600;
    margin: 0;
    color: var(--el-text-color-primary);
  }

  .config-menu {
    border-right: none;
    height: calc(100% - 60px);
    overflow-y: auto;
  }
  
  .loading-providers {
    padding: 10px 20px;
  }
}

.content-area {
  padding: 15px 25px;

  h3 {
    margin-top: 0;
    margin-bottom: 25px;
    color: var(--el-text-color-primary);
    border-bottom: 1px solid var(--el-border-color-lighter);
    padding-bottom: 10px;
  }
  
  pre {
    background-color: var(--el-fill-color-lighter);
    padding: 15px;
    border-radius: 4px;
    font-size: 0.85em;
    color: var(--el-text-color-secondary);
    max-height: 400px;
    overflow: auto;
  }
}

.loading-settings {
  padding: 20px;
}

.advanced-defaults-section {
  margin-top: 30px;
}

.el-divider--horizontal {
  margin: 25px 0;
}

.el-form-item {
  margin-bottom: 22px; 
}

.item-description {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
  line-height: 1.4;
}

.save-button-container {
  margin-top: 30px;
  padding-top: 20px;
  border-top: 1px solid var(--el-border-color-lighter);
  text-align: right;
}

.no-changes-hint {
  margin-left: 10px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.add-provider-button-container {
  padding: 15px 20px;
  border-top: 1px solid var(--el-menu-border-color);
  
  .add-provider-btn {
    width: 100%;
  }
}

/* 深色模式适配 */
:deep(.dark) {
  .item-description {
    color: var(--dark-text-secondary);
  }
  
  .no-changes-hint {
    color: var(--dark-text-secondary);
  }
  
  .gm-card-header {
    border-bottom-color: var(--el-border-color-darker);
  }
  
  .sidebar-header {
    border-bottom-color: var(--el-border-color-darker);
  }
  
  .sidebar {
    border-right-color: var(--el-border-color-darker);
  }
  
  .content-area h3 {
    border-bottom-color: var(--el-border-color-darker);
  }
  
  .save-button-container {
    border-top-color: var(--el-border-color-darker);
  }
}
</style> 