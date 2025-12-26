<!-- DataVisualization.vue -->
<template>
  <div class="data-visualization">
    <!-- 情感分析图表 -->
    <div v-if="showSentimentChart" class="chart-container">
      <h3>情感分析</h3>
      <div ref="sentimentChart" class="chart"></div>
    </div>

    <!-- 可读性分析图表 -->
    <div v-if="showReadabilityChart" class="chart-container">
      <h3>可读性分析</h3>
      <div ref="readabilityChart" class="chart"></div>
    </div>

    <!-- 词频分析图表 -->
    <div v-if="showWordFreqChart" class="chart-container">
      <h3>词频分析</h3>
      <div ref="wordFreqChart" class="chart"></div>
    </div>

    <!-- 句子结构分析图表 -->
    <div v-if="showSentenceChart" class="chart-container">
      <h3>句子结构分析</h3>
      <div ref="sentenceChart" class="chart"></div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts/core'
import { 
  TitleComponent,
  TooltipComponent,
  LegendComponent
} from 'echarts/components'
import {
  PieChart,
  BarChart,
  RadarChart
} from 'echarts/charts'
import { CanvasRenderer } from 'echarts/renderers'

// 注册必需的组件
echarts.use([
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  PieChart,
  BarChart,
  RadarChart,
  CanvasRenderer
])

export default {
  name: 'DataVisualization',
  props: {
    analysisData: {
      type: Object,
      required: true
    }
  },
  setup(props) {
    // 图表引用
    const sentimentChart = ref(null)
    const readabilityChart = ref(null)
    const wordFreqChart = ref(null)
    const sentenceChart = ref(null)

    // 图表实例
    let sentimentChartInstance = null
    let readabilityChartInstance = null
    let wordFreqChartInstance = null
    let sentenceChartInstance = null

    // 控制图表显示
    const showSentimentChart = ref(false)
    const showReadabilityChart = ref(false)
    const showWordFreqChart = ref(false)
    const showSentenceChart = ref(false)

    // 初始化图表
    const initCharts = () => {
      if (sentimentChart.value) {
        sentimentChartInstance = echarts.init(sentimentChart.value)
      }
      if (readabilityChart.value) {
        readabilityChartInstance = echarts.init(readabilityChart.value)
      }
      if (wordFreqChart.value) {
        wordFreqChartInstance = echarts.init(wordFreqChart.value)
      }
      if (sentenceChart.value) {
        sentenceChartInstance = echarts.init(sentenceChart.value)
      }
    }

    // 更新图表数据
    const updateCharts = () => {
      const data = props.analysisData

      // 更新情感分析图表
      if (data.sentiment && sentimentChartInstance) {
        showSentimentChart.value = true
        const sentimentOption = {
          title: {
            text: '情感分布'
          },
          tooltip: {
            trigger: 'item',
            formatter: '{b}: {c} ({d}%)'
          },
          series: [{
            type: 'pie',
            radius: '70%',
            data: [
              { value: data.sentiment.positive || 0, name: '积极' },
              { value: data.sentiment.neutral || 0, name: '中性' },
              { value: data.sentiment.negative || 0, name: '消极' }
            ],
            emphasis: {
              itemStyle: {
                shadowBlur: 10,
                shadowOffsetX: 0,
                shadowColor: 'rgba(0, 0, 0, 0.5)'
              }
            }
          }]
        }
        sentimentChartInstance.setOption(sentimentOption)
      }

      // 更新可读性分析图表
      if (data.readability && readabilityChartInstance) {
        showReadabilityChart.value = true
        const readabilityOption = {
          title: {
            text: '可读性指标'
          },
          tooltip: {
            trigger: 'axis'
          },
          radar: {
            indicator: [
              { name: '句子长度', max: 100 },
              { name: '词汇复杂度', max: 100 },
              { name: '语法复杂度', max: 100 },
              { name: '连贯性', max: 100 },
              { name: '清晰度', max: 100 }
            ]
          },
          series: [{
            type: 'radar',
            data: [{
              value: [
                data.readability.sentence_length || 0,
                data.readability.vocabulary_complexity || 0,
                data.readability.grammar_complexity || 0,
                data.readability.coherence || 0,
                data.readability.clarity || 0
              ],
              name: '可读性分析'
            }]
          }]
        }
        readabilityChartInstance.setOption(readabilityOption)
      }

      // 更新词频分析图表
      if (data.word_freq && wordFreqChartInstance) {
        showWordFreqChart.value = true
        const wordFreqData = Object.entries(data.word_freq)
          .sort((a, b) => b[1] - a[1])
          .slice(0, 10)
        
        const wordFreqOption = {
          title: {
            text: '高频词汇'
          },
          tooltip: {
            trigger: 'axis',
            axisPointer: {
              type: 'shadow'
            }
          },
          xAxis: {
            type: 'category',
            data: wordFreqData.map(item => item[0]),
            axisLabel: {
              interval: 0,
              rotate: 45
            }
          },
          yAxis: {
            type: 'value'
          },
          series: [{
            data: wordFreqData.map(item => item[1]),
            type: 'bar'
          }]
        }
        wordFreqChartInstance.setOption(wordFreqOption)
      }

      // 更新句子结构分析图表
      if (data.sentence_structure && sentenceChartInstance) {
        showSentenceChart.value = true
        const sentenceTypes = Object.entries(data.sentence_structure)
          .filter(([key]) => key !== 'error')
        
        const sentenceOption = {
          title: {
            text: '句子类型分布'
          },
          tooltip: {
            trigger: 'item',
            formatter: '{b}: {c} ({d}%)'
          },
          series: [{
            type: 'pie',
            radius: '70%',
            data: sentenceTypes.map(([type, count]) => ({
              name: type,
              value: count
            })),
            emphasis: {
              itemStyle: {
                shadowBlur: 10,
                shadowOffsetX: 0,
                shadowColor: 'rgba(0, 0, 0, 0.5)'
              }
            }
          }]
        }
        sentenceChartInstance.setOption(sentenceOption)
      }
    }

    // 监听窗口大小变化
    const handleResize = () => {
      sentimentChartInstance?.resize()
      readabilityChartInstance?.resize()
      wordFreqChartInstance?.resize()
      sentenceChartInstance?.resize()
    }

    // 监听数据变化
    watch(() => props.analysisData, () => {
      updateCharts()
    }, { deep: true })

    onMounted(() => {
      initCharts()
      updateCharts()
      window.addEventListener('resize', handleResize)
    })

    onUnmounted(() => {
      sentimentChartInstance?.dispose()
      readabilityChartInstance?.dispose()
      wordFreqChartInstance?.dispose()
      sentenceChartInstance?.dispose()
      window.removeEventListener('resize', handleResize)
    })

    return {
      sentimentChart,
      readabilityChart,
      wordFreqChart,
      sentenceChart,
      showSentimentChart,
      showReadabilityChart,
      showWordFreqChart,
      showSentenceChart
    }
  }
}
</script>

<style scoped>
.data-visualization {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 20px;
  padding: 20px;
}

.chart-container {
  background: #fff;
  border-radius: 8px;
  padding: 15px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.chart-container h3 {
  margin: 0 0 15px 0;
  color: #333;
  font-size: 16px;
  font-weight: 500;
}

.chart {
  width: 100%;
  height: 300px;
}
</style> 