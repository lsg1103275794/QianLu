<template>
  <div class="loading-overlay" v-if="isLoading">
    <div class="skeleton-container">
      <div class="skeleton-sidebar">
        <div class="skeleton-logo"></div>
        <div class="skeleton-menu-item"></div>
        <div class="skeleton-menu-item"></div>
        <div class="skeleton-menu-item"></div>
        <div class="skeleton-menu-item"></div>
      </div>
      <div class="skeleton-content">
        <div class="skeleton-header"></div>
        <div class="skeleton-card"></div>
        <div class="skeleton-card"></div>
        
        <!-- 添加步骤指示器 -->
        <div class="processing-steps">
          <div class="step-indicator">
            <div class="step-counter">{{ currentStep }}/{{ totalSteps }}</div>
            <div class="step-progress-bar">
              <div class="step-progress-fill" :style="{ width: `${(currentStep/totalSteps)*100}%` }"></div>
            </div>
          </div>
          <div class="step-description">{{ currentStepDescription }}</div>
        </div>
      </div>
    </div>
  </div>

  <el-container class="app-container" v-else>
    <el-aside width="220px" class="sidebar">
      <div class="logo-container">
        <!-- <img src="./assets/logo.png" alt="App Logo" class="logo-img"/> --> 
        <span>千  虑</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        class="el-menu-vertical"
        @select="handleSelect"
        :background-color="'transparent'"
        :text-color="isDarkMode ? '#e6e6e6' : '#e6e6e6'"
        :active-text-color="isDarkMode ? '#fe2c55' : '#fe2c55'"
        router 
      >
        <el-menu-item index="/text-analysis">
          <el-icon><Files /></el-icon>
          <span>{{ addEmoji('文本分析', 'menu', 'text-analysis') }}</span>
        </el-menu-item>
        
        <!-- 移动 文笔分析 到这里 -->
        <el-menu-item index="/writing-style-analysis">
          <el-icon><Edit /></el-icon>
          <span>{{ addEmoji('文笔分析', 'menu', 'writing-style-analysis') }}</span>
        </el-menu-item>

        <el-menu-item index="/style-transfer">
          <el-icon><MagicStick /></el-icon>
          <span>{{ addEmoji('风格迁移', 'menu', 'style-transfer') }}</span>
        </el-menu-item>
        
        <!-- 移动 Excel分析 到这里 -->
        <!-- <el-menu-item index="/excel-analysis">
          <el-icon><Document /></el-icon>
          <span>{{ addEmoji('Excel分析', 'menu', 'excel-analysis') }}</span>
        </el-menu-item> -->

        <el-menu-item index="/settings-manager">
          <el-icon><Platform /></el-icon>
          <span>{{ addEmoji('API 管理', 'menu', 'api-manager') }}</span>
        </el-menu-item>
        <el-menu-item index="/model-test">
          <el-icon><Platform /></el-icon>
          <span>{{ addEmoji('模型测试', 'menu', 'model-test') }}</span>
        </el-menu-item>
        <el-menu-item index="/data-terminal"> 
          <el-icon><DataLine /></el-icon>
          <span>{{ addEmoji('数据终端', 'menu', 'data-terminal') }}</span>
        </el-menu-item>
        <el-menu-item index="/report-generator">
          <el-icon><DataAnalysis /></el-icon>
          <span>{{ addEmoji('智能研报', 'menu', 'report-generator') }}</span>
        </el-menu-item>
      </el-menu>
    </el-aside>
    
    <el-container>
      <el-header height="50px" class="header">
         <!-- Header content can be minimal if using sidebar for primary nav -->
         <div class="header-title">{{ currentRouteTitle }}</div> 
         <div class="header-right">
           <LanguageSwitcher />
           <el-switch
              v-model="isDarkMode"
              @change="toggleDarkMode"
              inline-prompt
              :active-icon="Moon"
              :inactive-icon="Sunny"
              style="margin-left: 15px;"
            />
         </div>
      </el-header>
      
      <el-main>
        <!-- Temporarily simplified router-view -->
        <router-view /> 
        <!-- End of simplified section -->

        <!-- 
        <router-view v-slot="{ Component }">
          <transition 
            name="fade" 
            mode="out-in"
            @before-enter="beforeEnter"
            @enter="enter"
            @leave="leave"
            @after-leave="afterLeave"
          >
            <component 
              :is="Component" 
              :key="$route.fullPath"
              v-if="!componentLoading"
            />
          </transition>
          <div v-if="componentLoading" class="loading-container">
            <el-icon class="is-loading"><Loading /></el-icon>
            <span>加载中...</span>
          </div>
        </router-view>
        -->
      </el-main>
    </el-container>
  </el-container>

</template>

<script setup>
import { computed, ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
// 移除未使用的 Connection 图标导入
import { Files, MagicStick, Platform, Moon, Sunny, /* Loading, */ Edit, DataLine, DataAnalysis } from '@element-plus/icons-vue'
import { getEmoji, addEmoji } from './assets/emojiMap'
import LanguageSwitcher from './components/common/LanguageSwitcher.vue'
import gsap from 'gsap'

const route = useRoute()
const router = useRouter()
const isDarkMode = ref(localStorage.getItem('darkMode') === 'true')
const activeMenu = computed(() => route.path)

const currentRouteTitle = computed(() => {
  // Match route path to get a user-friendly title with emoji
  let title = '';
  let emoji = '';
  
  switch(route.path) {
    case '/text-analysis':
      title = '文本分析';
      emoji = getEmoji('menu', 'text-analysis');
      break;
    case '/excel-analysis':
      title = 'Excel数据分析';
      emoji = getEmoji('menu', 'excel-analysis');
      break;
    case '/style-transfer':
      title = '风格迁移';
      emoji = getEmoji('menu', 'style-transfer');
      break;
    case '/writing-style-analysis':
      title = '文笔分析';
      emoji = getEmoji('menu', 'writing-style-analysis');
      break;
    case '/settings-manager':
      title = 'API 管理';
      emoji = getEmoji('menu', 'api-manager');
      break;
    case '/model-test':
      title = '模型测试';
      emoji = getEmoji('menu', 'model-test');
      break;
    case '/data-terminal': // Tambahkan case untuk Data Terminal
      title = '数据终端';
      emoji = getEmoji('menu', 'data-terminal');
      break;
    case '/report-generator': // Tambahkan case untuk Report Generator
      title = '智能研报';
      emoji = getEmoji('menu', 'report-generator');
      break;  
    default:
      title = '千  虑';
      emoji = '🎨';
  }
  
  return emoji ? `${emoji} ${title}` : title;
});

const toggleDarkMode = () => {
  const htmlEl = document.documentElement;
  const bodyEl = document.body;
  const appEl = document.querySelector('.app-container');
  
  if (isDarkMode.value) {
    htmlEl.classList.add('dark');
    bodyEl.style.backgroundColor = 'var(--dark-bg-primary)';
    bodyEl.style.background = 'var(--dark-bg-primary)';
    if (appEl) appEl.style.background = 'var(--dark-bg-primary)';
    bodyEl.style.color = 'var(--dark-text-primary)';
  } else {
    htmlEl.classList.remove('dark');
    bodyEl.style.backgroundColor = 'var(--light-bg-primary)';
    bodyEl.style.background = 'var(--light-bg-gradient)';
    if (appEl) appEl.style.background = 'var(--light-bg-gradient)';
    bodyEl.style.color = 'var(--light-text-primary)';
  }
  
  // 保存用户偏好
  localStorage.setItem('darkMode', isDarkMode.value);
};

// 添加骨架屏相关状态
const isLoading = ref(true);

// 添加步骤相关状态
const totalSteps = ref(3);
const currentStep = ref(1);
const currentStepDescription = ref('正在初始化应用...');
const processingSteps = [
  '正在初始化应用...',
  '正在加载资源...',
  '准备就绪...'
];

// 修改onMounted，添加加载动画
onMounted(() => {
  toggleDarkMode();
  
  document.body.style.backgroundColor = isDarkMode.value ? 
    'var(--dark-bg-primary)' : 'var(--light-bg-primary)';
  
  currentStep.value = 1;
  currentStepDescription.value = processingSteps[0];
  
  const animate = () => {
    if (currentStep.value < totalSteps.value) {
      currentStep.value++;
      currentStepDescription.value = processingSteps[currentStep.value - 1];
      // 使用setTimeout代替requestAnimationFrame嵌套，减少渲染负担
      setTimeout(animate, 300);
    } else {
      isLoading.value = false;
      
      // 简化初始动画效果
      gsap.from('.sidebar', {
        duration: 0.15,
        x: -20,
        opacity: 0,
        ease: 'power2.out'
      });
      
      gsap.from('.header', {
        duration: 0.15,
        y: -15,
        opacity: 0,
        ease: 'power2.out'
      });
      
      gsap.from('.el-main', {
        duration: 0.2,
        opacity: 0,
        ease: 'power1.out'
      });
      
      // 使用nextTick延迟非关键操作
      setTimeout(() => {
        document.querySelectorAll('.el-button').forEach(btn => {
          btn.classList.add('ripple-btn');
        });
        // 使用passive选项优化事件监听
        window.addEventListener('mousemove', handleMouseMove, { passive: true });
      }, 500);
    }
  };
  
  // 直接调用animate，不需要requestAnimationFrame
  animate();
  
  return () => {
    window.removeEventListener('mousemove', handleMouseMove);
  };
});

// 3. 添加视差效果处理函数
const handleMouseMove = (e) => {
  const cards = document.querySelectorAll('.el-card');
  const moveX = (e.clientX - window.innerWidth / 2) / 200; // 减小移动幅度
  const moveY = (e.clientY - window.innerHeight / 2) / 200; // 减小移动幅度
  
  // 使用requestAnimationFrame优化性能
  requestAnimationFrame(() => {
    cards.forEach((card) => {
      // 简化视差效果，移除旋转效果
      gsap.to(card, {
        x: moveX,
        y: moveY,
        // 移除旋转效果，减少渲染负担
        // rotateX: moveY * 0.1,
        // rotateY: -moveX * 0.1,
        duration: 0.8, // 减少动画时间
        ease: 'power1.out'
      });
    });
    
    // 移除菜单项的视差效果，减少不必要的渲染
    // const menuItems = document.querySelectorAll('.el-menu-item');
    // menuItems.forEach((item) => {
    //   gsap.to(item, {
    //     x: moveX * 0.1,
    //     duration: 1.5,
    //     ease: 'power1.out'
    //   });
    // });
  });
};

const handleSelect = (key) => {
  // 确保菜单项的选中状态与路由路径一致
  if (key && key !== route.path) {
    // 仅当选中项与当前路径不同时才进行导航
    router.push(key);
  }
}


</script>

<style lang="scss">
/* 保留 App.vue 特定的布局和组件样式 */
.app-container {
  height: 100vh;
  /* background: var(--light-bg-gradient); */ /* 背景已在 global.scss 的 html, body 中设置 */

  .sidebar {
    background: linear-gradient(135deg,#000000,#434343) !important; /* 渐变背景 */
    transition: width 0.3s ease;
    overflow-x: hidden;
    box-shadow: 0 0 20px rgba(0, 0, 0, 0.3); /* 添加阴影效果 */
    border-right: 1px solid rgba(255, 255, 255, 0.05); /* 添加微妙边框 */
    position: relative;
    z-index: 10;

    .logo-container {
      padding: 18px 15px; /* 增加垂直内边距 */
      display: flex;
      align-items: center;
      justify-content: center; /* 居中显示 */
      background-color: rgba(0, 0, 0, 0.3) !important;
      margin-bottom: 15px; /* 增加底部间距 */
      position: relative;
      overflow: hidden;
      
      /* 添加光效背景 */
      &:before {
        content: '';
        position: absolute;
        top: 0;
        left: -100%;
        width: 50%;
        height: 100%;
        background: linear-gradient(
          to right,
          rgba(255, 255, 255, 0),
          rgba(255, 255, 255, 0.1),
          rgba(255, 255, 255, 0)
        );
        transform: skewX(-25deg);
        animation: shimmer 5s infinite;
      }
      
      /* 光效动画 */
      @keyframes shimmer {
        0% { left: -100%; }
        100% { left: 200%; }
      }

      span {
        color: #fff;
        font-weight: 700;
        font-size: 24px;
        letter-spacing: 2px;
        text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5);
        font-family: '华文行楷', '楷体', 'STKaiti', serif;
        color: #ffffff;
        position: relative;
        
        /* 添加毛笔墨迹效果 */
        &:after {
          content: '';
          position: absolute;
          bottom: -2px;
          left: 0;
          width: 100%;
          height: 1px;
          background: linear-gradient(to right, 
            rgba(255,255,255,0), 
            rgba(255,255,255,0.5), 
            rgba(255,255,255,0));
        }
      }
    }

    .el-menu {
      border-right: none;
      height: calc(100% - 70px); /* 调整高度 */
      background-color: transparent !important;
      padding-top: 10px; /* 顶部内边距 */

      .el-menu-item {
        height: 54px; /* 增加高度 */
        line-height: 54px;
        margin: 4px 10px; /* 添加间距 */
        border-radius: 8px; /* 圆角 */
        font-weight: 600;
        font-size: 15px;
        letter-spacing: 0.5px;
        background-color: transparent !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); /* 平滑过渡 */
        position: relative;
        overflow: hidden;
        padding: 0 18px;
        
        /* 创建悬浮时的发光效果 */
        &:before {
          content: '';
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          background: rgba(255, 255, 255, 0.03);
          border-radius: 8px;
          transform: scale(0.8);
          opacity: 0;
          transition: all 0.3s ease;
        }
        
        /* 左侧指示条 */
        &:after {
          content: '';
          position: absolute;
          left: 0;
          top: 50%;
          height: 0;
          width: 4px;
          background: #fe2c55;
          transform: translateY(-50%);
          transition: height 0.3s ease;
          border-radius: 0 2px 2px 0;
        }
        
        /* 图标和文本 */
        i {
          color: #e6e6e6 !important;
          font-size: 18px;
          margin-right: 10px;
          transition: all 0.3s ease;
        }
        
        span {
          font-size: 15px;
          transition: all 0.3s ease;
          text-shadow: 0 0.5px 0.5px rgba(0, 0, 0, 0.2);
        }
        
        /* 悬停效果 */
        &:hover {
          background-color: rgba(255, 255, 255, 0.08) !important;
          
          &:before {
            transform: scale(1);
            opacity: 1;
          }
          
          i, span {
            transform: translateX(2px);
          }
        }
        
        /* 选中状态增强 */
        &.is-active {
          background-color: rgba(255, 255, 255, 0.12) !important;
          font-weight: 700;
          
          /* 选中时左侧指示条显示 */
          &:after {
            height: 60%;
            animation: breath 2s infinite alternate ease-in-out;
          }
          
          /* 指示条呼吸动画 */
          @keyframes breath {
            from { opacity: 0.7; box-shadow: 0 0 2px rgba(254, 44, 85, 0.3); }
            to { opacity: 1; box-shadow: 0 0 8px rgba(254, 44, 85, 0.7); }
          }
          
          i {
            color: #fe2c55 !important;
            transform: scale(1.1) translateX(2px);
            animation: iconPulse 2s infinite alternate ease-in-out;
          }
          
          @keyframes iconPulse {
            from { text-shadow: 0 0 2px rgba(254, 44, 85, 0.3); }
            to { text-shadow: 0 0 8px rgba(254, 44, 85, 0.7); }
          }
          
          span {
            color: #ffffff !important;
            letter-spacing: 0.7px;
            text-shadow: 0 0.5px 1px rgba(0, 0, 0, 0.3);
          }
        }
      }
    }
  }
  
  .header {
    /* background-color: var(--light-bg-secondary); */ /* 使用全局变量或由深色模式覆盖 */
    box-shadow: 0 1px 4px var(--light-shadow);
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 20px;
    height: 50px; 
    border-bottom: 1px solid var(--light-border-color);
    /* 深色模式由 .dark 规则覆盖 */
    
    .header-title {
        font-size: 18px;
        /* color: var(--light-text-primary); */ /* 使用全局变量或由深色模式覆盖 */
        font-weight: 600;
        letter-spacing: 0.5px;
        text-shadow: 0 0.5px 0.5px rgba(0, 0, 0, 0.1);
    }
    .header-right {
        display: flex;
        align-items: center;
    }
  }
  
  .el-main {
    padding: 20px;
    position: relative; 
    overflow-y: auto; 
    /* color: var(--light-text-primary); */ /* 使用全局变量或由深色模式覆盖 */
    /* background-color: var(--light-bg-primary); */ /* 使用全局变量或由深色模式覆盖 */
  }
}

/* 深色模式下 App 容器和 Header 的特定样式 */
html.dark {
  .app-container {
    /* background-color: var(--dark-bg-primary); */ /* 全局已设置 */
    
    .header {
      background-color: var(--dark-bg-tertiary);
      box-shadow: 0 1px 4px rgba(0, 0, 0, 0.2);
      border-color: var(--dark-border-color);
      
      // Removed empty .header-title ruleset
    }
    
    // Removed empty .el-main ruleset
  }
}

/* 保留页面过渡动画 */
.page-transition-enter-active,
.page-transition-leave-active {
  transition: opacity 0.4s cubic-bezier(0.4, 0, 0.2, 1), transform 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}
.page-transition-enter-from {
  opacity: 0;
  transform: translateY(10px) scale(0.98);
}
.page-transition-leave-to {
  opacity: 0;
  transform: translateY(-10px) scale(0.98);
}

/* 保留骨架屏样式 */
.loading-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background-color: var(--light-bg-primary);
  z-index: 9999;
  display: flex;
  justify-content: center;
  align-items: center;
}

html.dark .loading-overlay {
  background-color: var(--dark-bg-primary);
}

.skeleton-container {
  display: flex;
  width: 100%;
  height: 100%;
}

.skeleton-sidebar {
  width: 220px;
  background-color: rgba(0, 0, 0, 0.8);
  padding: 20px;
}

.skeleton-logo {
  height: 40px;
  background-color: rgba(255, 255, 255, 0.1);
  margin-bottom: 30px;
  border-radius: 4px;
}

.skeleton-menu-item {
  height: 50px;
  background-color: rgba(255, 255, 255, 0.05);
  margin-bottom: 10px;
  border-radius: 4px;
}

.skeleton-content {
  flex-grow: 1;
  padding: 20px;
}

.skeleton-header {
  height: 50px;
  background-color: var(--light-bg-secondary);
  margin-bottom: 20px;
  border-radius: 4px;
}

.skeleton-card {
  height: 200px;
  background-color: rgba(255, 255, 255, 0.7);
  margin-bottom: 20px;
  border-radius: 12px;
}

html.dark .skeleton-header {
  background-color: var(--dark-bg-tertiary);
}

html.dark .skeleton-card {
  background-color: rgba(10, 10, 10, 0.7);
}

/* 添加波纹效果 */
.ripple-btn {
  position: relative;
  overflow: hidden;
}

.ripple {
  position: absolute;
  border-radius: 50%;
  background-color: rgba(255, 255, 255, 0.3);
  transform: scale(0);
  animation: ripple-effect 0.6s linear;
}

@keyframes ripple-effect {
  to {
    transform: scale(4);
    opacity: 0;
  }
}

/* 组件加载指示器样式 */
.component-loading {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background: rgba(255, 255, 255, 0.8);
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  z-index: 100;
  backdrop-filter: blur(5px);
  animation: fadeIn 0.3s ease-out;
}

html.dark .component-loading {
  background: rgba(30, 30, 30, 0.8);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
}

.component-loading-spinner {
  font-size: 24px;
  margin-bottom: 10px;
  color: var(--light-accent-primary);
}

html.dark .component-loading-spinner {
  color: var(--dark-accent-primary);
}

@keyframes fadeIn {
  from { opacity: 0; transform: translate(-50%, -60%); }
  to { opacity: 1; transform: translate(-50%, -50%); }
}

/* 步骤指示器样式 - HAPUS karena sudah ada di global.scss */
/* 
.processing-steps {
  position: absolute;
  bottom: 40px;
  left: 50%;
  transform: translateX(-50%);
  width: 80%;
  max-width: 600px;
  background: rgba(255, 255, 255, 0.9);
  padding: 15px 20px;
  border-radius: 10px;
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
  backdrop-filter: blur(5px);
  animation: fadeIn 0.5s ease-out;
  
  .step-indicator {
    display: flex;
    align-items: center;
    margin-bottom: 10px;
    
    .step-counter {
      font-size: 14px;
      font-weight: 600;
      color: var(--light-accent-primary);
      margin-right: 15px;
      min-width: 40px;
    }
    
    .step-progress-bar {
      flex: 1;
      height: 6px;
      background: rgba(0, 0, 0, 0.1);
      border-radius: 3px;
      overflow: hidden;
      
      .step-progress-fill {
        height: 100%;
        background: linear-gradient(90deg, var(--light-accent-primary), var(--light-accent-secondary));
        border-radius: 3px;
        transition: width 0.4s ease-out;
      }
    }
  }
  
  .step-description {
    font-size: 16px;
    font-weight: 500;
    color: var(--light-text-primary);
    text-align: center;
    margin-top: 5px;
    min-height: 24px;
  }
}

html.dark .processing-steps {
  background: rgba(20, 20, 20, 0.8);
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
  
  .step-indicator {
    .step-counter {
      color: var(--dark-accent-primary);
    }
    
    .step-progress-bar {
      background: rgba(255, 255, 255, 0.1);
      
      .step-progress-fill {
        background: linear-gradient(90deg, var(--dark-accent-primary), var(--dark-accent-secondary));
      }
    }
  }
  
  .step-description {
    color: var(--dark-text-primary);
  }
}
*/ 

</style>
