<template>
  <div class="config-form-container">
    <el-form label-position="top" class="dynamic-config-form">
      <el-form-item 
        v-for="item in schemaItems" 
        :key="item.env_var" 
        :label="item.label || item.env_var"
        :required="item.required"
      >
        <!-- 文本输入 -->
        <template v-if="item.type === 'text'">
          <el-input 
            v-model="localValues[item.env_var]"
            :placeholder="item.description || `请输入 ${item.label}`"
            @input="(value) => handleInput(item.env_var, value)"
          />
        </template>

        <!-- 密码输入 -->
        <template v-else-if="item.type === 'password'">
          <el-input 
            v-model="localValues[item.env_var]"
            type="password"
            show-password
            :placeholder="item.description || `请输入 ${item.label}`"
            @input="(value) => handleInput(item.env_var, value)"
          />
        </template>

        <!-- 数字输入 -->
        <template v-else-if="item.type === 'number'">
          <el-input-number 
            v-model="localValues[item.env_var]"
            :min="item.min_value ?? -Infinity"
            :max="item.max_value ?? Infinity"
            :step="item.step_value || 1"
            controls-position="right"
            style="width: 100%;"
            :placeholder="item.description || `请输入 ${item.label}`"
            @change="handleInput"
          />
        </template>

        <!-- 布尔值开关 -->
        <template v-else-if="item.type === 'boolean'">
          <el-switch 
             v-model="localValues[item.env_var]" 
             @change="(value) => handleInput(item.env_var, value)"
          />
        </template>
        
        <!-- 下拉选择框 -->
        <template v-else-if="item.type === 'select'">
          <el-select 
            v-model="localValues[item.env_var]"
            :placeholder="item.description || `请选择 ${item.label}`"
            style="width: 100%;"
            clearable
            @change="(value) => handleSelectChange(item.env_var, value)"
          >
            <el-option
              v-for="option in item.options"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
          <el-button icon="Refresh" @click="refreshSelectOptions(item.env_var)" circle size="small" class="select-refresh-btn" />
        </template>

        <!-- 未知类型 -->
        <template v-else>
            <el-tag type="danger">未知配置类型: {{ item.type }}</el-tag>
        </template>

        <!-- 描述信息 -->
        <div v-if="item.description && item.type !== 'boolean'" class="item-description">
            {{ item.description }}
        </div>
      </el-form-item>
      
      <el-form-item v-if="!schemaItems || schemaItems.length === 0">
           <el-alert title="没有可配置项" type="info" :closable="false"></el-alert>
      </el-form-item>
    </el-form>
  </div>
</template>

<script setup>
import { ref, watch, defineProps, defineEmits, onMounted } from 'vue';
import { ElForm, ElFormItem, ElInput, ElInputNumber, ElSwitch, ElSelect, ElOption, ElTag, ElAlert } from 'element-plus';

const props = defineProps({
  schemaItems: { // 配置项的 Schema 定义数组
    type: Array,
    required: true,
    default: () => []
  },
  currentValues: { // 当前配置值对象 (键: env_var, 值: 配置值)
    type: Object,
    required: true,
    default: () => ({})
  }
});

const emit = defineEmits(['update:values']); // 定义事件，用于通知父组件值的变化

// 创建一个本地的响应式对象来存储表单值，避免直接修改 props
const localValues = ref({});

// 监听 props.currentValues 的变化，同步到 localValues
watch(() => props.currentValues, (newValues) => {
    // 创建一个新对象，而不是直接引用，确保响应性
    const initialValues = {};
    // 从 schema 初始化所有可能的键，以确保所有表单项都有绑定
    props.schemaItems.forEach(item => {
        // 如果 newValues 里有值，用它；否则尝试用 schema 的默认值；最后用 null
        initialValues[item.env_var] = newValues?.[item.env_var] ?? item.default ?? null;
        // 特殊处理布尔值，确保是 true/false 而不是字符串 'true'/'false' 或 null
        if (item.type === 'boolean') {
             initialValues[item.env_var] = String(initialValues[item.env_var]).toLowerCase() === 'true';
        }
         // 特殊处理数字，确保是 number 类型
        if (item.type === 'number' && initialValues[item.env_var] !== null) {
            const num = Number(initialValues[item.env_var]);
            if (!isNaN(num)) {
                initialValues[item.env_var] = num;
            }
        }
    });
    localValues.value = initialValues;
    // console.log('ConfigForm: 初始化 localValues', localValues.value);
}, { immediate: true, deep: true });

// 处理输入变化，并触发事件通知父组件
const handleInput = () => {
  // 更新本地值 (v-model 已经做了)
  // console.log(`ConfigForm: 输入改变`);
  
  // 触发事件，将所有当前表单值传递给父组件
  // 父组件可以根据这个来判断哪些值变"脏"(dirty)
  emit('update:values', { ...localValues.value }); 
};

const handleSelectChange = (field, value) => {
  localStorage.setItem(`select_memory_${field}`, value);
  emit('update:values', { ...localValues });
};

const refreshSelectOptions = (field) => {
  localStorage.removeItem(`select_memory_${field}`);
  // emit 父组件刷新逻辑（如需）
};

onMounted(() => {
  props.schemaItems.forEach(item => {
    if (item.type === 'select') {
      const cached = localStorage.getItem(`select_memory_${item.env_var}`);
      if (cached && item.options.some(opt => opt.value === cached)) {
        localValues[item.env_var] = cached;
      }
    }
  });
});
</script>

<style lang="scss" scoped>
// ... styles ...
</style>