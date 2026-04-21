<template>
  <el-card class="dashboard-card">
    <el-tabs v-model="activeTab">
      
      <!-- Tab 1: 普通数据查询 -->
      <el-tab-pane label="基础明细查询" name="basic">
        <div class="query-form">
          <el-form :inline="true">
            <el-form-item label="表名">
              <el-input v-model="basicQuery.table" placeholder="如: bi_demo.orders" />
            </el-form-item>
            <el-form-item label="维度 (逗号分隔)">
              <el-input v-model="basicQuery.dimensions" placeholder="如: country, city" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="executeBasicQuery" :loading="loading">查询</el-button>
            </el-form-item>
          </el-form>
        </div>
        <el-table :data="basicData" border stripe style="width: 100%; margin-top: 20px;" v-loading="loading">
          <el-table-column v-for="col in basicColumns" :key="col" :prop="col" :label="col" />
        </el-table>
      </el-tab-pane>

      <!-- Tab 2: 多表负载SQL查询 -->
      <el-tab-pane label="自定义SQL分析" name="sql">
        <div class="query-form">
          <el-input
            v-model="rawSql"
            type="textarea"
            :rows="4"
            placeholder="输入复杂SQL语句 (支持多表 JOIN, GROUP BY 等)"
          />
          <div style="margin-top: 15px;">
            <el-button type="primary" @click="executeRawQuery" :loading="loading">执行SQL</el-button>
          </div>
        </div>
        <el-table :data="rawData" border stripe style="width: 100%; margin-top: 20px;" v-loading="loading">
          <el-table-column v-for="col in rawColumns" :key="col" :prop="col" :label="col" />
        </el-table>
      </el-tab-pane>

      <!-- Tab 3: 可视化数据下钻 -->
      <el-tab-pane label="可视化数据下钻" name="drill">
        <div class="drill-header">
          <el-breadcrumb separator="/">
            <el-breadcrumb-item>所有</el-breadcrumb-item>
            <el-breadcrumb-item v-for="(f, idx) in drillFilters" :key="idx">
              {{ f.value }}
            </el-breadcrumb-item>
          </el-breadcrumb>
          <div style="margin-top: 15px;">
            <el-button type="default" size="small" @click="goUp" :disabled="drillDepth === 0">
              返回上一级
            </el-button>
            <span style="margin-left: 15px; color: #666; font-size: 14px;">
              当前维度: {{ currentDrillDimension }}
            </span>
          </div>
        </div>
        
        <div ref="chartRef" class="echarts-container" v-loading="loading"></div>
      </el-tab-pane>

    </el-tabs>
  </el-card>
</template>

<script setup>
import { ref, onMounted, nextTick, watch } from 'vue'
import axios from 'axios'
import * as echarts from 'echarts'
import { ElMessage } from 'element-plus'

const API_BASE = 'http://127.0.0.1:8000/api/v1/data'
const activeTab = ref('basic')
const loading = ref(false)

// ==================== Tab 1: 基础查询 ====================
const basicQuery = ref({
  table: 'bi_demo.orders',
  dimensions: 'country, city, category, revenue'
})
const basicData = ref([])
const basicColumns = ref([])

const executeBasicQuery = async () => {
  loading.value = true
  try {
    const dims = basicQuery.value.dimensions.split(',').map(s => s.trim()).filter(Boolean)
    const payload = {
      table: basicQuery.value.table,
      dimensions: dims,
      metrics: [],
      filters: []
    }
    const res = await axios.post(`${API_BASE}/query`, payload)
    basicColumns.value = res.data.columns
    basicData.value = res.data.data
  } catch (error) {
    ElMessage.error('查询失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    loading.value = true
    setTimeout(() => { loading.value = false }, 200) // fake delay for better UX
  }
}

// ==================== Tab 2: 自定义SQL ====================
const rawSql = ref('SELECT o.country, count(*) as order_count, sum(o.revenue) as total_rev FROM bi_demo.orders o GROUP BY o.country')
const rawData = ref([])
const rawColumns = ref([])

const executeRawQuery = async () => {
  loading.value = true
  try {
    const res = await axios.post(`${API_BASE}/query/raw`, { sql: rawSql.value })
    rawColumns.value = res.data.columns
    rawData.value = res.data.data
  } catch (error) {
    ElMessage.error('SQL执行失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    loading.value = false
  }
}

// ==================== Tab 3: 数据下钻 ====================
const chartRef = ref(null)
let chartInstance = null

// 下钻路径配置
const drillPath = ['country', 'city', 'category']
const drillDepth = ref(0)
const drillFilters = ref([]) // 当前层级的过滤条件堆栈

const currentDrillDimension = ref(drillPath[0])

const baseDrillQuery = {
  table: 'bi_demo.orders',
  dimensions: [drillPath[0]],
  metrics: [
    { column: 'revenue', aggregation: 'sum', alias: 'total_revenue' }
  ],
  filters: []
}

const renderChart = (data, dimension) => {
  if (!chartInstance) {
    chartInstance = echarts.init(chartRef.value)
    // 绑定点击事件，触发下钻
    chartInstance.on('click', handleChartClick)
  }

  const xAxisData = data.map(item => item[dimension])
  const seriesData = data.map(item => item['total_revenue'])

  const option = {
    title: { text: `各${dimension}营收统计` },
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: xAxisData },
    yAxis: { type: 'value', name: '营收(元)' },
    series: [
      {
        data: seriesData,
        type: 'bar',
        barMaxWidth: 60,
        itemStyle: { color: '#409EFF' },
        label: { show: true, position: 'top' }
      }
    ]
  }
  chartInstance.setOption(option, true)
}

const loadDrillData = async () => {
  loading.value = true
  try {
    currentDrillDimension.value = drillPath[drillDepth.value]
    
    let res
    if (drillDepth.value === 0) {
      // 顶层直接查
      res = await axios.post(`${API_BASE}/query`, baseDrillQuery)
    } else {
      // 下钻查询
      const payload = {
        base_query: baseDrillQuery,
        drill_down_dimension: currentDrillDimension.value,
        current_level_filters: drillFilters.value
      }
      res = await axios.post(`${API_BASE}/drill-down`, payload)
    }
    
    nextTick(() => {
      renderChart(res.data.data, currentDrillDimension.value)
    })
  } catch (error) {
    ElMessage.error('下钻数据加载失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    loading.value = false
  }
}

const handleChartClick = (params) => {
  if (drillDepth.value >= drillPath.length - 1) {
    ElMessage.warning('已经到底层，无法继续下钻')
    return
  }
  
  // params.name 是点击的类目名称 (例如 "中国")
  const clickValue = params.name
  
  // 压入新的过滤条件
  drillFilters.value.push({
    column: currentDrillDimension.value,
    operator: '=',
    value: clickValue
  })
  
  drillDepth.value++
  loadDrillData()
}

const goUp = () => {
  if (drillDepth.value > 0) {
    drillFilters.value.pop()
    drillDepth.value--
    loadDrillData()
  }
}

// 监听 Tab 切换
watch(activeTab, (newVal) => {
  if (newVal === 'drill') {
    nextTick(() => {
      if (!chartInstance) {
        loadDrillData()
      } else {
        chartInstance.resize()
      }
    })
  }
})

onMounted(() => {
  // 默认加载 Tab1
  executeBasicQuery()
})
</script>

<style scoped>
.dashboard-card {
  min-height: 80vh;
}
.query-form {
  background-color: #fafafa;
  padding: 15px;
  border-radius: 4px;
  margin-bottom: 20px;
}
.echarts-container {
  width: 100%;
  height: 500px;
  margin-top: 20px;
}
.drill-header {
  padding: 10px 0;
  border-bottom: 1px solid #eee;
}
</style>
