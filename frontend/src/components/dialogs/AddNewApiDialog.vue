<template>
  <el-dialog
    v-model="dialogVisible"
    title="添加新的API提供商"
    width="600px"
    :close-on-click-modal="false"
    @close="resetForm"
    append-to-body
  >
    <!-- 添加 API 指南 -->
    <el-alert 
      title="API 添加指南" 
      type="info" 
      :closable="false" 
      show-icon
      style="margin-bottom: 20px;"
    >
      <p>在这里添加和配置您想要使用的 AI 模型服务提供商。</p>
      <ul>
        <li><b>支持的类型:</b> 对于系统已知的提供商（如 Ollama, Deepseek, Google Gemini, Zhipu AI, Groq, Mistral, Together AI 等），通常只需要填写正确的 API 密钥 (API Key)。服务地址 (Endpoint URL) 大多有默认值，仅在需要时修改。</li>
        <li><b>兼容类型:</b> 您也可以尝试添加其他兼容 OpenAI API 协议的服务商，填入其 API 密钥和服务地址。能否成功调用取决于后端是否已支持该类型。</li>
        <li><b>获取凭证:</b> 请前往相应 AI 服务商的官方网站注册账户，获取有效的 API 密钥和对应的服务地址。</li>
        <li><b>保存配置:</b> 填写完成后，点击"确定"按钮保存配置到 .env 文件。</li>
      </ul>
    </el-alert>

    <el-form :model="newApiForm" label-width="140px" :rules="apiFormRules" ref="newApiFormRef">
      <template v-if="schema.fields && schema.fields.length">
        <template v-for="field in schema.fields" :key="field.name">
          <el-form-item :label="field.label" :prop="field.name">
            <el-input v-if="field.type === 'text'" v-model="newApiForm[field.name]" :placeholder="field.label" />
            <el-input v-else-if="field.type === 'password'" v-model="newApiForm[field.name]" :placeholder="field.label" show-password />
            <el-input-number v-else-if="field.type === 'number'" v-model="newApiForm[field.name]" :placeholder="field.label" :min="0" />
            <el-switch v-else-if="field.type === 'switch'" v-model="newApiForm[field.name]" />
            <el-slider v-else-if="field.type === 'slider'" v-model="newApiForm[field.name]" :min="field.min || 0" :max="field.max || 1" :step="field.step || 0.1" show-input />
          </el-form-item>
        </template>
      </template>
      <template v-else>
        <el-form-item label="提供商名称" prop="name">
          <el-input v-model="newApiForm.name" placeholder="英文字母和下划线，如 my_openai"></el-input>
          <div class="form-tip">用于内部标识，建议只使用英文、数字和下划线</div>
        </el-form-item>
        
        <el-form-item label="显示名称" prop="displayName">
          <el-input v-model="newApiForm.displayName" placeholder="用户界面显示的名称，如 我的OpenAI"></el-input>
          <div class="form-tip">在界面上显示的友好名称，可以使用中文</div>
        </el-form-item>
        
        <el-form-item label="API密钥" prop="apiKey">
          <el-input v-model="newApiForm.apiKey" type="password" show-password placeholder="API密钥或令牌"></el-input>
        </el-form-item>
        
        <el-form-item label="API服务地址" prop="endpoint">
          <el-input v-model="newApiForm.endpoint" placeholder="如: https://api.example.com/v1"></el-input>
          <div class="form-tip">API服务的基础URL，必须包含协议前缀(http://或https://)</div>
        </el-form-item>
        
        <el-form-item label="默认模型" prop="defaultModel">
          <el-input v-model="newApiForm.defaultModel" placeholder="如: gpt-3.5-turbo"></el-input>
          <div class="form-tip">默认使用的模型名称，应与API提供商支持的模型一致</div>
        </el-form-item>
        
        <el-divider>高级模型参数设置</el-divider>
        
        <el-form-item label="温度参数">
          <el-slider 
            v-model="newApiForm.temperature" 
            :min="0" 
            :max="1" 
            :step="0.1" 
            show-input
            class="temp-slider"
            :format-tooltip="value => `${value} (${value === 0 ? '最确定' : value === 1 ? '最随机' : value < 0.5 ? '偏确定' : '偏随机'})`"
          />
          <div class="form-tip">控制模型输出的随机性和创造性，值越低(0-0.3)回答越确定、精准，值越高(0.7-1.0)回答越多样、创造性。常用值: 0.7</div>
        </el-form-item>
        
        <el-form-item label="最大输出长度">
          <el-input-number 
            v-model="newApiForm.maxTokens" 
            :min="10" 
            :max="8000" 
            :step="10"
            class="token-input"
          />
          <div class="form-tip">限制模型单次回复的最大标记(token)数量，中文约1-2字/token，英文约0.75词/token。常用值: 2048</div>
        </el-form-item>
        
        <el-divider>兼容性设置</el-divider>
        
        <el-form-item label="OpenAI兼容">
          <el-switch v-model="newApiForm.isOpenAICompatible" />
          <div class="form-tip">启用此选项表示该API使用与OpenAI兼容的请求和响应格式</div>
        </el-form-item>
        
        <el-form-item label="启用状态">
          <el-switch v-model="newApiForm.enabled" />
        </el-form-item>

        <el-form-item label="请求超时（秒）" prop="requestTimeout">
          <el-input-number v-model="newApiForm.requestTimeout" :min="1" :max="600" :step="1" placeholder="60" />
          <div class="form-tip">API 请求的超时时间（秒），建议 30~120，超大模型可适当加大</div>
        </el-form-item>
      </template>
    </el-form>
    
    <template #footer>
      <span class="dialog-footer">
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="submitNewApi" :loading="submitting">
          确认添加
        </el-button>
      </span>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, defineEmits, defineExpose, watch } from 'vue';
import { ElMessage } from 'element-plus';
import axios from 'axios';
import api from '../../services/api';

const emit = defineEmits(['success']);

const dialogVisible = ref(false);
const submitting = ref(false);
const newApiFormRef = ref(null);

const newApiForm = reactive({
  name: '',
  displayName: '',
  apiKey: '',
  endpoint: '',
  defaultModel: '',
  temperature: 0.7,
  maxTokens: 2048,
  requestTimeout: 60,
  enabled: true,
  isOpenAICompatible: true
});

const apiFormRules = {
  name: [
    { required: true, message: '请输入提供商名称', trigger: 'blur' },
    { pattern: /^[a-zA-Z0-9_]+$/, message: '只能包含英文、数字和下划线', trigger: 'blur' }
  ],
  displayName: [
    { required: true, message: '请输入显示名称', trigger: 'blur' }
  ],
  apiKey: [
    { required: true, message: '请输入API密钥', trigger: 'blur' }
  ],
  endpoint: [
    { required: true, message: '请输入API端点', trigger: 'blur' },
    { pattern: /^https?:\/\//, message: '端点必须以http://或https://开头', trigger: 'blur' }
  ],
  defaultModel: [
    { required: true, message: '请输入默认模型', trigger: 'blur' }
  ]
};

const schema = ref({ fields: [] });

// 动态获取schema
async function fetchSchema() {
  // 这里 type 可根据 isOpenAICompatible 切换，暂用 openai_compatible
  const type = newApiForm.isOpenAICompatible ? 'openai_compatible' : 'custom';
  try {
    const { data } = await axios.get(`/api/settings/provider-schema/${type}`);
    schema.value = data;
  } catch (e) {
    schema.value = { fields: [] };
    ElMessage.error('获取表单模板失败');
  }
}

watch(() => newApiForm.isOpenAICompatible, fetchSchema, { immediate: true });

const openDialog = () => {
  resetForm();
  dialogVisible.value = true;
  fetchSchema();
};

const resetForm = () => {
  if (newApiFormRef.value) {
    newApiFormRef.value.resetFields();
  }
  Object.assign(newApiForm, {
    name: '',
    displayName: '',
    apiKey: '',
    endpoint: '',
    defaultModel: '',
    temperature: 0.7,
    maxTokens: 2048,
    requestTimeout: 60,
    enabled: true,
    isOpenAICompatible: true
  });
};

const submitNewApi = () => {
  if (!newApiFormRef.value) return;
  newApiFormRef.value.validate(async (valid) => {
    if (!valid) return;
    submitting.value = true;
    try {
      // 构造 envVars
      const envVars = {
        [`${newApiForm.name.toUpperCase()}_API_KEY`]: String(newApiForm.apiKey ?? ''),
        [`${newApiForm.name.toUpperCase()}_ENDPOINT`]: String(newApiForm.endpoint ?? ''),
        [`${newApiForm.name.toUpperCase()}_DEFAULT_MODEL`]: String(newApiForm.defaultModel ?? ''),
        [`${newApiForm.name.toUpperCase()}_REQUEST_TIMEOUT`]: String(newApiForm.requestTimeout ?? ''),
        [`${newApiForm.name.toUpperCase()}_TEMPERATURE`]: String(newApiForm.temperature ?? ''),
        [`${newApiForm.name.toUpperCase()}_MAX_TOKENS`]: String(newApiForm.maxTokens ?? ''),
        [`${newApiForm.name.toUpperCase()}_TOP_P`]: "0.9"
      };
      const apiConfig = {
        name: newApiForm.name,
        display_name: newApiForm.displayName
      };
      const response = await api.addApiProvider({
        env: envVars,
        config: apiConfig,
        is_openai_compatible: newApiForm.isOpenAICompatible
      });
      if (response.data && response.data.status === 'success') {
        let successMsg = response.data.message || '新API提供商添加成功';
        if (response.data.auto_generated) {
          successMsg += '。已自动生成API处理器，支持流式输出功能。';
        } else if (newApiForm.isOpenAICompatible && !response.data.auto_generated) {
          successMsg += '。但API处理器自动生成失败，你可能需要手动创建处理器代码。';
        }
        ElMessage.success(successMsg);
        dialogVisible.value = false;
        emit('success', { name: newApiForm.name, envVars });
      } else {
        throw new Error(response.data?.message || '添加失败');
      }
    } catch (error) {
      ElMessage.error(error.message || '添加API提供商失败');
    } finally {
      submitting.value = false;
    }
  });
};

defineExpose({ openDialog });

</script>

<style lang="scss" scoped>
.form-tip {
  color: #a9c0e3;
  font-size: 0.85em;
  margin-top: 5px;
  line-height: 1.4;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
}

.temp-slider {
  .el-slider__runway {
    background-color: #394154;
  }
  .el-slider__bar {
    background-color: #4989e9;
  }
  .el-slider__button {
    border-color: #4989e9;
  }
}

.token-input {
  .el-input-number__decrease,
  .el-input-number__increase {
    color: #4989e9;
    &:hover {
      color: #8dc5ff;
    }
  }
}
</style> 