<template>
  <div class="api-diagnostics">
    <div class="header">
      <h2>API 诊断</h2>
      <el-button 
        type="primary" 
        circle 
        @click="refreshProviders"
        :loading="loading"
      >
        <el-icon><Refresh /></el-icon>
      </el-button>
    </div>

    <p>API诊断功能正在维护中，将很快恢复。</p>
  </div>
</template>

<script>
import { ref } from 'vue';
import { Refresh } from '@element-plus/icons-vue';

export default {
  name: 'ApiDiagnostics',
  components: {
    Refresh
  },
  props: {
    refreshInterval: {
      type: Number,
      default: 0
    },
    autoLoadOnMount: {
      type: Boolean,
      default: true
    }
  },
  setup(props, { emit }) {
    const loading = ref(false);
    
    const refreshProviders = async () => {
      loading.value = true;
      // 模拟加载
      setTimeout(() => {
        loading.value = false;
      }, 1000);
    };
    
    return {
      loading,
      refreshProviders
    };
  }
};
</script>

<style lang="scss" scoped>
.api-diagnostics {
  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
    
    h2 {
      margin: 0;
      font-size: 20px;
      font-weight: 500;
    }
  }
}
</style> 