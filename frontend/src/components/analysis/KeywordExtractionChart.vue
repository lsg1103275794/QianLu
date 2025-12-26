<template>
  <div class="keyword-extraction-chart">
    <div v-if="!hasKeywordData" class="empty-data">
      <el-empty description="无关键词数据" :image-size="80">
        <template #description>
          <p>未能获取有效的关键词数据，请检查文本内容或重新分析。</p>
        </template>
      </el-empty>
    </div>
    
    <template v-else>
      <!-- 控制面板 -->
      <div class="control-panel">
        <div class="view-switcher">
          <el-radio-group v-model="viewMode" size="small">
            <el-radio-button :value="'chart'">柱状图</el-radio-button>
            <el-radio-button :value="'cloud'">词云图</el-radio-button>
          </el-radio-group>
        </div>
        
        <div class="filter-control">
          <span class="filter-label">显示数量:</span>
          <el-slider 
            v-model="keywordLimit" 
            :min="5" 
            :max="20" 
            :step="1"
            :show-tooltip="true"
            size="small"
            style="width: 150px; margin: 0 12px;"
          />
          <span class="current-value">{{ keywordLimit }}个</span>
        </div>
      </div>
      
      <!-- TF-IDF关键词 -->
      <div class="chart-container">
        <h3>TF-IDF关键词提取</h3>
        <div v-if="viewMode === 'chart'" ref="tfidfChartRef" class="chart"></div>
        <div v-else ref="tfidfCloudRef" class="chart"></div>
      </div>
      
      <!-- TextRank关键词 -->
      <div class="chart-container">
        <h3>TextRank关键词提取</h3>
        <div v-if="viewMode === 'chart'" ref="textrankChartRef" class="chart"></div>
        <div v-else ref="textrankCloudRef" class="chart"></div>
      </div>
      
      <!-- 关键词对比表 -->
      <div class="chart-container keyword-table-container">
        <h3>关键词对比分析</h3>
        <div class="keyword-table-wrapper">
          <table class="keyword-table">
            <thead>
              <tr>
                <th>排名</th>
                <th>TF-IDF关键词</th>
                <th>权重得分</th>
                <th>TextRank关键词</th>
                <th>权重得分</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(_, index) in displayedKeywords" :key="index">
                <td class="rank-cell">{{ index + 1 }}</td>
                <td class="keyword-cell" :class="{ 'highlight': index < 3 }">{{ tfidfKeywords[index]?.[0] || '-' }}</td>
                <td>{{ formatWeight(tfidfKeywords[index]?.[1]) }}</td>
                <td class="keyword-cell" :class="{ 'highlight': index < 3 }">{{ textrankKeywords[index]?.[0] || '-' }}</td>
                <td>{{ formatWeight(textrankKeywords[index]?.[1]) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      
      <!-- 关键词分析解读 -->
      <div class="chart-container info-container">
        <h3>关键词分析解读</h3>
        <div class="info-content">
          <div class="info-section">
            <h4>TF-IDF算法</h4>
            <p>TF-IDF（词频-逆文档频率）算法根据词语在文档中的频率以及在语料库中的稀有程度来评估词语的重要性，适合找出最能代表文档主题的关键词。</p>
          </div>
          <div class="info-section">
            <h4>TextRank算法</h4>
            <p>TextRank算法基于图模型，通过分析词语之间的共现关系来确定关键词，更注重词语的语义关联，提供更符合人类认知的结果。</p>
          </div>
          <div class="info-section">
            <h4>算法比较</h4>
            <p>两种算法各有优势：TF-IDF计算简单高效，适合处理大规模文本；TextRank更关注词语语义关联，在特定场景下表现更好。</p>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import * as echarts from 'echarts'
import 'echarts-wordcloud'

const props = defineProps({
  keyword_extraction: {
    type: Object,
    required: true
  }
})

// 图表引用
const tfidfChartRef = ref(null)
const textrankChartRef = ref(null)
const tfidfCloudRef = ref(null)
const textrankCloudRef = ref(null)

// 图表实例
let tfidfChart = null
let textrankChart = null
let tfidfCloudChart = null
let textrankCloudChart = null

// 视图模式：chart（柱状图）或cloud（词云图）
const viewMode = ref('chart')

// 关键词数量限制
const keywordLimit = ref(15)

// 提取关键词数据
const tfidfKeywords = computed(() => {
  return props.keyword_extraction?.tfidf_keywords || []
})

const textrankKeywords = computed(() => {
  return props.keyword_extraction?.textrank_keywords || []
})

// 检查是否有关键词数据
const hasKeywordData = computed(() => {
  return tfidfKeywords.value.length > 0 || textrankKeywords.value.length > 0
})

// 显示的关键词数量（用于表格显示）
const displayedKeywords = computed(() => {
  return Array.from({ length: Math.min(keywordLimit.value, Math.max(tfidfKeywords.value.length, textrankKeywords.value.length)) })
})

// 规范化权重值，使其更易读
const normalizeWeights = (keywords) => {
  if (!keywords || keywords.length === 0) return []
  
  // 找出最大权重值
  const maxWeight = Math.max(...keywords.map(item => item[1]))
  
  // 如果最大权重太小，进行放大处理
  if (maxWeight < 0.01) {
    const scaleFactor = 0.01 / maxWeight
    return keywords.map(([word, weight]) => [word, weight * scaleFactor])
  }
  
  return keywords
}

// 格式化权重值显示
const formatWeight = (weight) => {
  if (weight === undefined || weight === null) return '-'
  
  // 根据权重大小决定显示的小数位数
  if (weight < 0.001) return weight.toExponential(2)
  if (weight < 0.01) return weight.toFixed(4)
  if (weight < 0.1) return weight.toFixed(3)
  if (weight < 1) return weight.toFixed(2)
  return weight.toFixed(1)
}

// 初始化TF-IDF柱状图
const initTfidfChart = () => {
  if (!tfidfChartRef.value || !tfidfKeywords.value.length) return

  if (tfidfChart) {
    tfidfChart.dispose()
  }
  
  tfidfChart = echarts.init(tfidfChartRef.value)
  const normalizedKeywords = normalizeWeights(tfidfKeywords.value)
  // 反转数据顺序，使最重要的关键词显示在顶部
  const data = normalizedKeywords.slice(0, keywordLimit.value)
    .map(([word, weight]) => ({
      name: word,
      value: weight
    }))
    .reverse()

  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      },
      formatter: function(params) {
        const param = params[0]
        return `${param.name}<br/>权重: ${formatWeight(param.value)}`
      }
    },
    grid: {
      left: '18%',
      right: '8%',
      top: '3%',
      bottom: '3%',
      containLabel: true
    },
    yAxis: {
      type: 'category',
      data: data.map(item => item.name),
      axisTick: { alignWithLabel: true },
      axisLabel: {
        interval: 0,
        fontSize: 12,
        margin: 16,
        formatter: function(value) {
          // 不需要省略词语，因为现在是水平显示的
          return value;
        }
      }
    },
    xAxis: {
      type: 'value',
      name: '权重',
      nameTextStyle: {
        padding: [0, 0, 0, 0]
      }
    },
    series: [
      {
        name: 'TF-IDF',
        type: 'bar',
        barWidth: '60%',
        data: data.map((item, index) => ({
          value: item.value,
          itemStyle: {
            color: new echarts.graphic.LinearGradient(1, 0, 0, 0, [
              { offset: 0, color: index < 3 ? '#2e6de8' : '#5b8ff9' },
              { offset: 1, color: index < 3 ? '#2753b0' : '#3a73dd' }
            ])
          }
        })),
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0,0,0,0.3)'
          }
        },
        label: {
          show: true,
          position: 'right',
          formatter: function(params) {
            return formatWeight(params.value);
          },
          fontSize: 11
        }
      }
    ]
  }

  tfidfChart.setOption(option)
}

// 初始化TextRank柱状图
const initTextrankChart = () => {
  if (!textrankChartRef.value || !textrankKeywords.value.length) return

  if (textrankChart) {
    textrankChart.dispose()
  }
  
  textrankChart = echarts.init(textrankChartRef.value)
  const normalizedKeywords = normalizeWeights(textrankKeywords.value)
  // 反转数据顺序，使最重要的关键词显示在顶部
  const data = normalizedKeywords.slice(0, keywordLimit.value)
    .map(([word, weight]) => ({
      name: word,
      value: weight
    }))
    .reverse()

  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      },
      formatter: function(params) {
        const param = params[0]
        return `${param.name}<br/>权重: ${formatWeight(param.value)}`
      }
    },
    grid: {
      left: '18%',
      right: '8%',
      top: '3%',
      bottom: '3%',
      containLabel: true
    },
    yAxis: {
      type: 'category',
      data: data.map(item => item.name),
      axisTick: { alignWithLabel: true },
      axisLabel: {
        interval: 0,
        fontSize: 12,
        margin: 16,
        formatter: function(value) {
          // 不需要省略词语，因为现在是水平显示的
          return value;
        }
      }
    },
    xAxis: {
      type: 'value',
      name: '权重',
      nameTextStyle: {
        padding: [0, 0, 0, 0]
      }
    },
    series: [
      {
        name: 'TextRank',
        type: 'bar',
        barWidth: '60%',
        data: data.map((item, index) => ({
          value: item.value,
          itemStyle: {
            color: new echarts.graphic.LinearGradient(1, 0, 0, 0, [
              { offset: 0, color: index < 3 ? '#14b474' : '#40c088' },
              { offset: 1, color: index < 3 ? '#0c8054' : '#239369' }
            ])
          }
        })),
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0,0,0,0.3)'
          }
        },
        label: {
          show: true,
          position: 'right',
          formatter: function(params) {
            return formatWeight(params.value);
          },
          fontSize: 11
        }
      }
    ]
  }

  textrankChart.setOption(option)
}

// 初始化TF-IDF词云图
const initTfidfCloudChart = () => {
  if (!tfidfCloudRef.value || !tfidfKeywords.value.length) {
    console.log('跳过TF-IDF词云初始化：DOM元素或数据不存在')
    return
  }

  try {
    if (tfidfCloudChart) {
      tfidfCloudChart.dispose()
    }
    
    console.log('初始化TF-IDF词云图 DOM元素:', tfidfCloudRef.value)
    console.log('数据:', tfidfKeywords.value.slice(0, 5))
    
    tfidfCloudChart = echarts.init(tfidfCloudRef.value)
    const normalizedKeywords = normalizeWeights(tfidfKeywords.value)
    
    // 确保权重值被适当放大，以避免太小而不可见
    const data = normalizedKeywords.slice(0, keywordLimit.value * 2).map(([word, weight]) => {
      // 确保权重值适合词云显示
      const scaledWeight = Math.max(weight * 1000, 10)
      return {
        name: word,
        value: scaledWeight,
        textStyle: {
          fontWeight: weight > normalizedKeywords[3]?.[1] ? 'bold' : 'normal',
          shadowBlur: 5,
          shadowColor: 'rgba(0, 0, 0, 0.3)'
        }
      }
    })
    
    console.log('处理后的词云数据:', data.slice(0, 5))

    const option = {
      tooltip: {
        show: true,
        formatter: function(params) {
          return `${params.name}<br/>权重: ${formatWeight(params.value / 1000)}`
        }
      },
      series: [{
        type: 'wordCloud',
        shape: 'circle',
        left: 'center',
        top: 'center',
        width: '90%',
        height: '90%',
        right: null,
        bottom: null,
        sizeRange: [14, 50],
        rotationRange: [-30, 30],
        rotationStep: 15,
        gridSize: 15,
        drawOutOfBound: false,
        layoutAnimation: true,
        textStyle: {
          fontFamily: 'sans-serif',
          fontWeight: 'bold',
          color: function() {
            // 蓝色系渐变色
            return 'rgb(' + 
              Math.round(50 + Math.random() * 50) + ',' + 
              Math.round(90 + Math.random() * 60) + ',' + 
              Math.round(180 + Math.random() * 75) + ')';
          }
        },
        emphasis: {
          textStyle: {
            shadowBlur: 15,
            shadowColor: '#333'
          }
        },
        data: data
      }],
      animation: true,
      animationDuration: 1000,
      animationEasing: 'cubicOut'
    }

    tfidfCloudChart.setOption(option)
    console.log('TF-IDF词云图配置已应用')
  } catch (error) {
    console.error('初始化TF-IDF词云图失败:', error)
  }
}

// 初始化TextRank词云图
const initTextrankCloudChart = () => {
  if (!textrankCloudRef.value || !textrankKeywords.value.length) {
    console.log('跳过TextRank词云初始化：DOM元素或数据不存在')
    return
  }

  try {
    if (textrankCloudChart) {
      textrankCloudChart.dispose()
    }
    
    console.log('初始化TextRank词云图 DOM元素:', textrankCloudRef.value)
    console.log('数据:', textrankKeywords.value.slice(0, 5))
    
    textrankCloudChart = echarts.init(textrankCloudRef.value)
    const normalizedKeywords = normalizeWeights(textrankKeywords.value)
    
    // 确保权重值被适当放大，以避免太小而不可见
    const data = normalizedKeywords.slice(0, keywordLimit.value * 2).map(([word, weight]) => {
      // 确保权重值适合词云显示
      const scaledWeight = Math.max(weight * 1000, 10)
      return {
        name: word,
        value: scaledWeight,
        textStyle: {
          fontWeight: weight > normalizedKeywords[3]?.[1] ? 'bold' : 'normal',
          shadowBlur: 5,
          shadowColor: 'rgba(0, 0, 0, 0.3)'
        }
      }
    })
    
    console.log('处理后的词云数据:', data.slice(0, 5))

    const option = {
      tooltip: {
        show: true,
        formatter: function(params) {
          return `${params.name}<br/>权重: ${formatWeight(params.value / 1000)}`
        }
      },
      series: [{
        type: 'wordCloud',
        shape: 'circle',
        left: 'center',
        top: 'center',
        width: '90%',
        height: '90%',
        right: null,
        bottom: null,
        sizeRange: [14, 50],
        rotationRange: [-30, 30],
        rotationStep: 15,
        gridSize: 15,
        drawOutOfBound: false,
        layoutAnimation: true,
        textStyle: {
          fontFamily: 'sans-serif',
          fontWeight: 'bold',
          color: function() {
            // 绿色系渐变色
            return 'rgb(' + 
              Math.round(30 + Math.random() * 60) + ',' + 
              Math.round(140 + Math.random() * 70) + ',' + 
              Math.round(50 + Math.random() * 80) + ')';
          }
        },
        emphasis: {
          textStyle: {
            shadowBlur: 15,
            shadowColor: '#333'
          }
        },
        data: data
      }],
      animation: true,
      animationDuration: 1000,
      animationEasing: 'cubicOut'
    }

    textrankCloudChart.setOption(option)
    console.log('TextRank词云图配置已应用')
  } catch (error) {
    console.error('初始化TextRank词云图失败:', error)
  }
}

// 初始化所有图表
const initCharts = () => {
  requestAnimationFrame(() => {
    try {
      if (viewMode.value === 'chart') {
        initTfidfChart()
        initTextrankChart()
      } else {
        // 使用setTimeout给DOM足够的准备时间
        setTimeout(() => {
          initTfidfCloudChart()
          initTextrankCloudChart()
        }, 100)
      }
    } catch (error) {
      console.error('Error initializing charts:', error)
    }
  })
}

// 监听视图模式变化
watch(viewMode, () => {
  // 增加延迟以确保视图更新后再初始化图表
  setTimeout(initCharts, 200)
})

// 监听关键词数量变化
watch(keywordLimit, () => {
  initCharts()
})

// 监听关键词数据变化
watch(() => props.keyword_extraction, () => {
  if (document.visibilityState === 'visible') {
    initCharts()
  }
}, { deep: true })

// 组件挂载时初始化图表
onMounted(() => {
  setTimeout(initCharts, 0)
  window.addEventListener('resize', initCharts)
})

// 组件卸载时清理图表实例
onUnmounted(() => {
  window.removeEventListener('resize', initCharts)
  tfidfChart?.dispose()
  textrankChart?.dispose()
  tfidfCloudChart?.dispose()
  textrankCloudChart?.dispose()
})
</script>

<style scoped>
.keyword-extraction-chart {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
}

.empty-data {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 200px;
  background: var(--el-bg-color);
  border-radius: 8px;
  padding: 20px;
  grid-column: 1 / -1;
}

.control-panel {
  grid-column: 1 / -1;
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  background: var(--el-bg-color);
  border-radius: 8px;
  padding: 15px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
  margin-bottom: 5px;
}

.filter-control {
  display: flex;
  align-items: center;
}

.filter-label {
  font-size: 14px;
  color: var(--el-text-color-secondary);
}

.current-value {
  font-size: 14px;
  color: var(--el-text-color-primary);
  min-width: 36px;
}

.chart-container {
  background: var(--el-bg-color);
  border-radius: 8px;
  padding: 15px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.05);
  transition: transform 0.3s, box-shadow 0.3s;
}

.chart-container:hover {
  box-shadow: 0 4px 16px 0 rgba(0, 0, 0, 0.1);
  transform: translateY(-3px);
}

.keyword-table-container, .info-container {
  grid-column: 1 / -1;
}

h3 {
  margin: 0 0 15px;
  font-size: 16px;
  color: var(--el-text-color-primary);
  padding-bottom: 8px;
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

h4 {
  margin: 0 0 8px;
  font-size: 14px;
  color: var(--el-text-color-primary);
}

.chart {
  width: 100%;
  height: 350px;
}

.keyword-table-wrapper {
  overflow-x: auto;
  margin-top: 10px;
}

.keyword-table {
  width: 100%;
  border-collapse: collapse;
  border-spacing: 0;
  text-align: left;
}

.keyword-table th,
.keyword-table td {
  padding: 10px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.keyword-table th {
  background-color: var(--el-fill-color-light);
  font-weight: 500;
  position: sticky;
  top: 0;
  z-index: 1;
}

.keyword-table tbody tr:hover {
  background-color: var(--el-fill-color);
}

.keyword-table tbody tr:nth-child(odd) {
  background-color: var(--el-fill-color-lighter);
}

.keyword-cell.highlight {
  color: var(--el-color-primary);
  font-weight: bold;
}

.rank-cell {
  text-align: center;
  font-weight: bold;
}

.info-content {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 15px;
}

.info-section {
  background-color: var(--el-fill-color-lighter);
  border-radius: 6px;
  padding: 12px;
}

.info-section p {
  margin: 0;
  font-size: 14px;
  line-height: 1.5;
  color: var(--el-text-color-regular);
}

@media (max-width: 768px) {
  .keyword-table th,
  .keyword-table td {
    padding: 8px 4px;
    font-size: 12px;
  }
  
  .chart {
    height: 280px;
  }
  
  .info-content {
    grid-template-columns: 1fr;
  }
  
  .control-panel {
    flex-direction: column;
    gap: 10px;
    align-items: flex-start;
  }
  
  .filter-control {
    width: 100%;
  }
}

/* 处理深色模式 */
@media (prefers-color-scheme: dark) {
  .info-section {
    background-color: var(--el-bg-color-overlay);
  }
}
</style> 