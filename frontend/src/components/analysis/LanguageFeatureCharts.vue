<template>
  <div class="language-feature-charts">
    <!-- 可视化图表部分 -->
    <div class="charts-section">
      <!-- 数据概览部分 -->
      <div class="summary-section">
        <div class="stats-overview">
          <div class="stat-item">
            <div class="stat-value">{{ getNounRatio() }}%</div>
            <div class="stat-label">名词占比</div>
          </div>
          <div class="stat-item">
            <div class="stat-value">{{ getVerbRatio() }}%</div>
            <div class="stat-label">动词占比</div>
          </div>
          <div class="stat-item">
            <div class="stat-value">{{ getAdjRatio() }}%</div>
            <div class="stat-label">形容词占比</div>
          </div>
          <div class="stat-item">
            <div class="stat-value">{{ getAdvRatio() }}%</div>
            <div class="stat-label">副词占比</div>
          </div>
          <div class="stat-item">
            <div class="stat-value">{{ getComplexWordRatio() }}</div>
            <div class="stat-label">词汇复杂度</div>
          </div>
        </div>
      </div>

      <!-- 只保留词性分布图表 -->
      <div class="chart-container full-width">
        <h3>词性分布</h3>
        <div ref="posChartRef" class="chart"></div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  languageFeatures: {
    type: Object,
    required: true
  }
})

// 词性映射表（英文缩写 -> 中文名称）
const posMapping = {
  'n': '名词',
  'v': '动词',
  'a': '形容词',
  'adv': '副词',
  'd': '限定词',
  'p': '介词',
  'r': '代词',
  'c': '连词',
  'q': '量词',
  'i': '感叹词',
  'w': '标点符号',
  'u': '助词',
  'm': '数词',
  'f': '方位词',
  'x': '外来词',
  't': '时间词',
  's': '处所词',
  'nl': '名词性惯用语',
  'nr': '人名',
  'ns': '地名',
  'nt': '机构名',
  'nw': '作品名',
  'vg': '动词性惯用语',
  'vd': '副动词',
  'vn': '名动词',
  'vq': '准动词',
  'vi': '不及物动词',
  'vt': '及物动词'
}

// 图表引用
const posChartRef = ref(null)
let posChart = null

// 获取词性统计数据
const getNounRatio = () => {
  if (!props.languageFeatures || !props.languageFeatures.noun_ratio) return 0
  return parseFloat(props.languageFeatures.noun_ratio).toFixed(1)
}

const getVerbRatio = () => {
  if (!props.languageFeatures || !props.languageFeatures.verb_ratio) return 0
  return parseFloat(props.languageFeatures.verb_ratio).toFixed(1)
}

const getAdjRatio = () => {
  if (!props.languageFeatures || !props.languageFeatures.adj_ratio) return 0
  return parseFloat(props.languageFeatures.adj_ratio).toFixed(1)
}

const getAdvRatio = () => {
  if (!props.languageFeatures || !props.languageFeatures.adv_ratio) return 0
  return parseFloat(props.languageFeatures.adv_ratio).toFixed(1)
}

const getComplexWordRatio = () => {
  if (!props.languageFeatures || !props.languageFeatures.complex_word_ratio) return 0
  return parseFloat(props.languageFeatures.complex_word_ratio).toFixed(2)
}

// 获取中文词性名称
const getPosChinese = (posTag) => {
  return posMapping[posTag] || posTag
}

// 检测当前是否为深色模式
const isDarkMode = () => {
  return document.documentElement.classList.contains('dark') || 
         document.body.classList.contains('dark') ||
         window.matchMedia('(prefers-color-scheme: dark)').matches
}

const initPosChart = () => {
  if (!posChartRef.value || !props.languageFeatures.pos_distribution) return

  // 销毁旧的图表实例，确保DOM干净
  if (posChart) {
    posChart.dispose()
  }

  posChart = echarts.init(posChartRef.value)
  const data = Object.entries(props.languageFeatures.pos_distribution)
    .map(([name, value]) => ({ name: getPosChinese(name), value }))
    .sort((a, b) => b.value - a.value)

  // 定义颜色数组，确保每个词性都有固定的颜色
  const colors = [
    '#5470c6', '#91cc75', '#fac858', '#ee6666',
    '#73c0de', '#3ba272', '#fc8452', '#9a60b4',
    '#ea7ccc', '#44cef6', '#9ac0cd', '#b15bff'
  ]

  // 深色模式下的文本颜色
  const textColor = isDarkMode() ? '#eee' : '#333'
  const borderColor = isDarkMode() ? 'rgba(255, 255, 255, 0.2)' : 'rgba(0, 0, 0, 0.1)'

  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      formatter: '{b}: {c} ({d}%)',
      borderRadius: 8,
      padding: [8, 12],
      textStyle: {
        fontSize: 13
      },
      backgroundColor: isDarkMode() ? 'rgba(50, 50, 50, 0.9)' : 'rgba(255, 255, 255, 0.9)',
      borderColor: isDarkMode() ? '#555' : '#ddd'
    },
    legend: {
      type: 'scroll',
      orient: 'vertical',
      right: 5,
      top: 15,
      bottom: 15,
      textStyle: {
        fontSize: 12,
        color: textColor
      },
      pageIconSize: 12,
      pageTextStyle: {
        fontSize: 12,
        color: textColor
      },
      itemWidth: 14,
      itemHeight: 14,
      itemGap: 8
    },
    series: [
      {
        type: 'pie',
        radius: '75%', 
        center: ['40%', '50%'],
        avoidLabelOverlap: true,
        itemStyle: {
          borderRadius: 4,
          borderWidth: 2,
          borderColor: borderColor
        },
        label: {
          show: true,
          formatter: (params) => {
            // 只给占比较大的词性添加标签
            if (params.percent > 3) {
              return `${params.name}: ${params.percent}%`
            } else {
              return ''
            }
          },
          fontSize: 12,
          position: 'outside',
          color: textColor,
          fontWeight: 'normal',
          textBorderWidth: 0,
          alignTo: 'labelLine',
          distanceToLabelLine: 5
        },
        labelLine: {
          length: 15,
          length2: 10,
          maxSurfaceAngle: 80,
          lineStyle: {
            width: 1
          }
        },
        emphasis: {
          label: {
            show: true,
            fontSize: 14,
            fontWeight: 'bold'
          },
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.5)'
          }
        },
        data: data,
        // 添加动画效果
        animationType: 'scale',
        animationEasing: 'elasticOut',
        animationDelay: function () {
          return Math.random() * 200;
        }
      }
    ],
    color: colors
  }

  posChart.setOption(option)
}

const initCharts = () => {
  requestAnimationFrame(() => {
    try {
      initPosChart()
    } catch (error) {
      console.error('Error initializing charts:', error)
    }
  })
}

watch(() => props.languageFeatures, () => {
  if (document.visibilityState === 'visible') {
    initCharts()
  }
}, { deep: true })

// 监听配色方案变化
const setupColorSchemeListener = () => {
  const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
  
  const handleColorSchemeChange = () => {
    initPosChart()
  }
  
  mediaQuery.addEventListener('change', handleColorSchemeChange)
  return () => mediaQuery.removeEventListener('change', handleColorSchemeChange)
}

onMounted(() => {
  setTimeout(initCharts, 0)
  window.addEventListener('resize', initCharts)
  const removeColorSchemeListener = setupColorSchemeListener()
  
  // 添加到卸载逻辑
  onUnmounted(() => {
    window.removeEventListener('resize', initCharts)
    removeColorSchemeListener()
    posChart?.dispose()
  })
})
</script>

<style scoped>
.language-feature-charts {
  display: flex;
  flex-direction: column;
  gap: 15px;
  width: 100%;
}

.charts-section {
  display: grid;
  grid-template-columns: 1fr;
  gap: 15px;
}

.summary-section {
  grid-column: 1 / -1;
  background: var(--el-bg-color);
  border-radius: 10px;
  padding: 20px 15px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
  margin-bottom: 5px;
}

.stats-overview {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 12px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 12px 15px;
  border-radius: 8px;
  background-color: var(--el-fill-color-darker);
  min-width: 130px;
  flex: 1;
  text-align: center;
  transition: all 0.3s ease;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
}

.stat-item:hover {
  transform: translateY(-3px);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.12);
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: var(--el-color-primary);
  margin-bottom: 6px;
  line-height: 1.2;
}

.stat-label {
  font-size: 14px;
  color: var(--el-text-color-regular);
  font-weight: 500;
}

.chart-container {
  background: var(--el-bg-color);
  border-radius: 10px;
  padding: 18px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
  transition: transform 0.3s, box-shadow 0.3s;
  height: 100%;
  display: flex;
  flex-direction: column;
}

.full-width {
  grid-column: 1 / -1;
}

.chart-container:hover {
  box-shadow: 0 4px 20px 0 rgba(0, 0, 0, 0.1);
  transform: translateY(-3px);
}

h3 {
  margin: 0 0 15px;
  font-size: 16px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  padding-bottom: 10px;
  border-bottom: 1px solid var(--el-border-color-light);
  position: relative;
}

h3:after {
  content: '';
  position: absolute;
  left: 0;
  bottom: -1px;
  width: 50px;
  height: 3px;
  background-color: var(--el-color-primary);
  border-radius: 2px;
}

.chart {
  width: 100%;
  height: 320px;
  flex-grow: 1;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .chart {
    height: 280px;
  }
  
  .chart-container {
    padding: 15px;
  }
  
  .stat-item {
    min-width: 100px;
    padding: 10px 8px;
  }
  
  .stat-value {
    font-size: 22px;
  }
  
  .stat-label {
    font-size: 12px;
  }
}

@media (max-width: 500px) {
  .stats-overview {
    justify-content: center;
  }
  
  .stat-item {
    min-width: 80px;
    padding: 8px 6px;
    flex-basis: calc(50% - 6px);
  }
  
  .stat-value {
    font-size: 20px;
  }
}
</style> 