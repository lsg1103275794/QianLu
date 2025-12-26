<template>
  <el-drawer
    v-model="isVisible"
    :title="`${providerName} 配置`"
    size="500px"
    direction="rtl"
    :before-close="closeDrawer"
  >
    <div class="drawer-content">
      <div v-if="!configItems || configItems.length === 0" class="drawer-loading">
        <el-skeleton :rows="5" animated />
      </div>
      <div v-else class="config-form">
        <el-form label-position="top">
          <el-form-item
            v-for="(item, index) in configItems"
            :key="index"
            :label="item.title"
            :required="item.required"
          >
            <template v-if="item.type === 'text'">
              <el-input
                v-model="configValues[item.key]"
                :placeholder="item.description"
                :type="isPasswordField(item.key) ? 'password' : 'text'"
                :show-password="isPasswordField(item.key)"
              ></el-input>
            </template>
            <template v-else-if="item.type === 'select'">
              <el-select
                v-model="configValues[item.key]"
                :placeholder="item.description"
                style="width: 100%"
              >
                <el-option
                  v-for="opt in item.options"
                  :key="opt.value"
                  :label="opt.label"
                  :value="opt.value"
                ></el-option>
              </el-select>
            </template>
            <template v-else-if="item.type === 'number'">
              <el-input-number
                v-model="configValues[item.key]"
                :min="item.min || 0"
                :max="item.max || 9999"
                style="width: 100%"
              ></el-input-number>
            </template>
            <template v-else-if="item.type === 'boolean'">
              <el-switch v-model="configValues[item.key]"></el-switch>
            </template>
            <div class="item-description" v-if="item.description">
              {{ item.description }}
            </div>
          </el-form-item>
        </el-form>
      </div>
    </div>

    <!-- 抽屉底部按钮 -->
    <FixedDrawerButtons>
      <el-button @click="closeDrawer">取消</el-button>
      <el-button type="primary" @click="saveConfig" :loading="isSaving">保存</el-button>
    </FixedDrawerButtons>
  </el-drawer>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import FixedDrawerButtons from '../common/FixedDrawerButtons.vue';

const props = defineProps({
  visible: {
    type: Boolean,
    default: false
  },
  providerName: {
    type: String,
    default: ''
  },
  configItems: {
    type: Array,
    default: () => []
  },
  initialValues: {
    type: Object,
    default: () => ({})
  },
  isSaving: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['update:visible', 'save', 'cancel']);

const configValues = ref({});

// 同步visible属性
const isVisible = computed({
  get: () => props.visible,
  set: (value) => emit('update:visible', value)
});

// 监听initialValues变化，初始化配置值
watch(() => props.initialValues, (values) => {
  if (values) {
    configValues.value = { ...values };
  }
}, { immediate: true, deep: true });

// 判断是否为密码字段
const isPasswordField = (key) => {
  return key.includes('KEY') || key.includes('SECRET') || key.includes('TOKEN');
};

// 关闭抽屉
const closeDrawer = () => {
  emit('update:visible', false);
  emit('cancel');
};

// 保存配置
const saveConfig = () => {
  emit('save', configValues.value);
};
</script>

<style lang="scss" scoped>
.drawer-content {
  padding: 0 16px;
}

.drawer-loading {
  padding: 20px 0;
}

.config-form {
  padding: 16px 0;
}

.item-description {
  font-size: 12px;
  color: #909399;
  margin-top: 4px;
}
</style> 