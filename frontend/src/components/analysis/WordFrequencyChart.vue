<template>
  <div class="word-frequency-chart">
    <div v-if="!hasWordFrequencyData" class="empty-data">
      <el-empty description="无词频数据可显示" :image-size="80">
        <template #description>
          <p>未能获取有效的词频数据，请检查文本内容或重新分析。</p>
        </template>
      </el-empty>
    </div>
    
    <template v-else>
      <div class="summary-section">
        <div class="stats-overview">
          <div class="stat-item">
            <div class="stat-value">{{ wordFrequencyStats.totalWords }}</div>
            <div class="stat-label">总词数</div>
          </div>
          <div class="stat-item">
            <div class="stat-value">{{ wordFrequencyStats.uniqueWords }}</div>
            <div class="stat-label">不重复词数</div>
          </div>
          <div class="stat-item">
            <div class="stat-value">{{ wordFrequencyStats.lexicalDiversity.toFixed(2) }}</div>
            <div class="stat-label">词汇丰富度</div>
          </div>
        </div>
      </div>
      
      <div class="chart-container">
        <h3>词频分布（TOP20）</h3>
        <div ref="horizontalChartRef" class="chart"></div>
      </div>
      <div class="chart-container">
        <h3>词频趋势（TOP10）</h3>
        <div ref="verticalChartRef" class="chart"></div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  wordFrequency: {
    type: [Object, Array],
    required: true
  }
})

const horizontalChartRef = ref(null)
const verticalChartRef = ref(null)
let horizontalChart = null
let verticalChart = null

// 汇总词频统计数据
const wordFrequencyStats = computed(() => {
  const wordFreqData = extractWordFrequencyData();
  // eslint-disable-next-line no-unused-vars
  const totalWords = wordFreqData.reduce((sum, [_, count]) => sum + count, 0);
  const uniqueWords = wordFreqData.length;
  const lexicalDiversity = uniqueWords > 0 ? (uniqueWords / totalWords) * 100 : 0;
  
  return {
    totalWords,
    uniqueWords,
    lexicalDiversity
  };
});

// 检查是否有有效的词频数据
const hasWordFrequencyData = computed(() => {
  if (!props.wordFrequency) return false;
  
  try {
    // 处理不同格式的词频数据
    const wordFreqData = extractWordFrequencyData();
    return wordFreqData.length > 0;
  } catch (error) {
    console.error('检查词频数据时出错:', error);
    return false;
  }
})

// 从不同格式的数据中提取词频信息
const extractWordFrequencyData = () => {
  try {
    const wordFreq = props.wordFrequency;
    
    console.log("处理词频数据:", wordFreq);
    
    if (!wordFreq) {
      console.warn("词频数据为空");
      return [];
    }
    
    // 情况1: topWords属性 - 本地分析服务的标准格式
    if (Array.isArray(wordFreq.topWords) && wordFreq.topWords.length > 0) {
      console.log("使用topWords数组格式");
      return wordFreq.topWords;
    }
    
    // 情况2: 直接是对象格式的词频 {word: frequency, ...}
    if (typeof wordFreq === 'object' && !Array.isArray(wordFreq) && 
        Object.keys(wordFreq).length > 0 &&
        typeof Object.values(wordFreq)[0] === 'number') {
      console.log("使用对象格式");
      return Object.entries(wordFreq);
    }
    
    // 情况3: 包含频率字段的对象 {frequencies: {word: frequency, ...}}
    if (wordFreq.frequencies && typeof wordFreq.frequencies === 'object') {
      console.log("使用frequencies对象格式");
      return Object.entries(wordFreq.frequencies);
    }
    
    // 情况4: 数组格式 [{word: '词', frequency: 频率}, ...]
    if (Array.isArray(wordFreq) && wordFreq.length > 0) {
      if (wordFreq[0].word && (wordFreq[0].frequency || wordFreq[0].count || wordFreq[0].value)) {
        console.log("使用对象数组格式");
        return wordFreq.map(item => [
          item.word, 
          item.frequency || item.count || item.value || 0
        ]);
      }
    }
    
    // 情况5: 包含词频结果数组的对象 {results: [{word: '词', frequency: 频率}, ...]}
    if (wordFreq.results && Array.isArray(wordFreq.results) && wordFreq.results.length > 0) {
      console.log("使用results数组格式");
      return wordFreq.results.map(item => [
        item.word || item.term || item.text || '',
        item.frequency || item.count || item.value || 0
      ]);
    }
    
    // 情况6: 独立的words和frequencies数组 {words: ['词1', '词2'], frequencies: [频率1, 频率2]}
    if (Array.isArray(wordFreq.words) && Array.isArray(wordFreq.frequencies) && 
        wordFreq.words.length > 0 && wordFreq.words.length === wordFreq.frequencies.length) {
      console.log("使用words/frequencies分离数组格式");
      return wordFreq.words.map((word, index) => [word, wordFreq.frequencies[index]]);
    }
    
    // 情况7: 词云数据格式 {wordCloudData: [{name: '词', value: 频率}, ...]}
    if (wordFreq.wordCloudData && Array.isArray(wordFreq.wordCloudData) && wordFreq.wordCloudData.length > 0) {
      console.log("使用wordCloudData数组格式");
      return wordFreq.wordCloudData.map(item => [item.name, item.value]);
    }
    
    // 情况8: 直接二维数组格式 [[词, 频率], ...]
    if (Array.isArray(wordFreq) && wordFreq.length > 0 && Array.isArray(wordFreq[0]) && wordFreq[0].length === 2) {
      console.log("使用二维数组格式");
      return wordFreq;
    }
    
    // 后备：如果以上都不匹配，尝试递归遍历对象寻找合适的数据
    for (const [key, value] of Object.entries(wordFreq)) {
      // 检查是否是词频数据对象
      if (typeof value === 'object' && !Array.isArray(value) && 
          Object.keys(value).length > 0 &&
          typeof Object.values(value)[0] === 'number') {
        console.log(`找到内嵌对象格式 (${key})`);
        return Object.entries(value);
      }
      
      // 如果是数组，检查是否是词频数组
      if (Array.isArray(value) && value.length > 0) {
        // 检查是否是[word, freq]格式的数组
        if (Array.isArray(value[0]) && value[0].length === 2) {
          console.log(`找到内嵌二维数组格式 (${key})`);
          return value;
        }
        
        // 检查是否是对象数组格式
        if (typeof value[0] === 'object' && (value[0].word || value[0].name) && 
            (value[0].frequency || value[0].count || value[0].value)) {
          console.log(`找到内嵌对象数组格式 (${key})`);
          return value.map(item => [
            item.word || item.name || item.term || '', 
            item.frequency || item.count || item.value || 0
          ]);
        }
      }
    }
    
    console.warn("无法识别的词频数据格式:", wordFreq);
    return [];
  } catch (error) {
    console.error('处理词频数据时出错:', error);
    return [];
  }
}

const initHorizontalChart = () => {
  if (!horizontalChartRef.value) return;
  
  const wordFreqData = extractWordFrequencyData();
  if (wordFreqData.length === 0) return;

  // 如果图表已存在，先销毁
  if (horizontalChart) {
    horizontalChart.dispose();
  }

  horizontalChart = echarts.init(horizontalChartRef.value);
  const data = wordFreqData
    .sort((a, b) => b[1] - a[1])
    .slice(0, 20);

  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      },
      formatter: function(params) {
        const data = params[0];
        return `${data.name}: ${data.value}`;
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '3%',
      containLabel: true
    },
    xAxis: {
      type: 'value',
      name: '出现次数'
    },
    yAxis: {
      type: 'category',
      data: data.map(item => item[0]),
      axisLabel: {
        interval: 0,
        formatter: function(value) {
          if (value.length > 12) {
            return value.substring(0, 12) + '...';
          }
          return value;
        }
      }
    },
    series: [
      {
        type: 'bar',
        data: data.map((item, index) => ({
          value: item[1],
          itemStyle: {
            color: `hsl(${210 + index * 7}, 70%, 50%)`
          }
        })),
        label: {
          show: true,
          position: 'right',
          formatter: '{c}'
        }
      }
    ],
    animationDuration: 1000,
    animationEasing: 'cubicOut'
  };

  horizontalChart.setOption(option);
}

const initVerticalChart = () => {
  if (!verticalChartRef.value) return;
  
  const wordFreqData = extractWordFrequencyData();
  if (wordFreqData.length === 0) return;

  // 如果图表已存在，先销毁
  if (verticalChart) {
    verticalChart.dispose();
  }

  verticalChart = echarts.init(verticalChartRef.value);
  const data = wordFreqData
    .sort((a, b) => b[1] - a[1])
    .slice(0, 10);

  const option = {
    tooltip: {
      trigger: 'axis',
      axisPointer: {
        type: 'shadow'
      },
      formatter: function(params) {
        const data = params[0];
        return `${data.name}: ${data.value}`;
      }
    },
    grid: {
      left: '3%',
      right: '4%',
      bottom: '20%',  // 增加底部空间，避免标签拥挤
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: data.map(item => item[0]),
      axisLabel: {
        interval: 0,
        rotate: 45,
        formatter: function(value) {
          if (value.length > 10) {
            return value.substring(0, 10) + '...';
          }
          return value;
        }
      }
    },
    yAxis: {
      type: 'value',
      name: '出现次数'
    },
    series: [
      {
        type: 'bar',
        data: data.map((item, index) => ({
          value: item[1],
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: `hsl(${200 + index * 15}, 90%, 60%)` },
              { offset: 1, color: `hsl(${200 + index * 15}, 90%, 40%)` }
            ])
          }
        })),
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowColor: 'rgba(0,0,0,0.3)'
          }
        },
        showBackground: true,
        backgroundStyle: {
          color: 'rgba(180, 180, 180, 0.1)'
        }
      }
    ],
    animationDuration: 1000,
    animationDelay: function (idx) {
      return idx * 100;
    }
  };

  verticalChart.setOption(option);
}

const initCharts = () => {
  requestAnimationFrame(() => {
    try {
      if (hasWordFrequencyData.value) {
        initHorizontalChart();
        initVerticalChart();
      }
    } catch (error) {
      console.error('初始化词频图表时出错:', error);
    }
  });
}

watch(() => props.wordFrequency, () => {
  if (document.visibilityState === 'visible') {
    initCharts();
  }
}, { deep: true });

// 监听窗口尺寸变化，重绘图表
const handleResize = () => {
  horizontalChart?.resize();
  verticalChart?.resize();
};

onMounted(() => {
  setTimeout(initCharts, 100); // 增加延迟，确保DOM已经渲染
  window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
  window.removeEventListener('resize', handleResize);
  horizontalChart?.dispose();
  verticalChart?.dispose();
});
</script>

<style scoped>
.word-frequency-chart {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.summary-section {
  background: var(--el-bg-color);
  border-radius: 8px;
  padding: 15px;
}

.stats-overview {
  display: flex;
  justify-content: space-around;
  flex-wrap: wrap;
  gap: 10px;
}

.stat-item {
  text-align: center;
  padding: 10px;
  min-width: 100px;
}

.stat-value {
  font-size: 22px;
  font-weight: bold;
  color: var(--el-color-primary);
  margin-bottom: 5px;
}

.stat-label {
  font-size: 14px;
  color: var(--el-text-color-secondary);
}

.chart-container {
  background: var(--el-bg-color);
  border-radius: 8px;
  padding: 15px;
}

h3 {
  margin: 0 0 15px;
  font-size: 16px;
  color: var(--el-text-color-primary);
  text-align: center;
  position: relative;
}

h3:after {
  content: '';
  position: absolute;
  bottom: -5px;
  left: 50%;
  transform: translateX(-50%);
  width: 40px;
  height: 3px;
  background: var(--el-color-primary-light-5);
  border-radius: 2px;
}

.chart {
  width: 100%;
  height: 360px;
}

.empty-data {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 300px;
  background: var(--el-bg-color);
  border-radius: 8px;
  padding: 20px;
}

@media (min-width: 768px) {
  .word-frequency-chart {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
    gap: 20px;
  }
  
  .summary-section {
    grid-column: 1 / -1;
  }
}
</style> 