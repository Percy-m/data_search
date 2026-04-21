<template>
  <el-card class="dashboard-card">
    <div class="header-section">
      <h2>统一数据分析控制台</h2>
      <p class="subtitle">支持标准数据明细查询、多表 JOIN、聚合分析。点击结果中的<strong>数值指标</strong>即可自动下钻查看底层明细数据。</p>
    </div>

    <!-- SQL 输入区 -->
    <div class="query-box">
      <el-input
        v-model="rawSql"
        type="textarea"
        :rows="6"
        placeholder="请输入 SQL 语句 (例如: SELECT country, city, count(*) as order_count, sum(revenue) as total_rev FROM bi_demo.orders GROUP BY country, city)"
        class="sql-input"
      />
      <div class="action-bar">
        <el-button type="primary" size="large" @click="executeMainQuery" :loading="loading">
          执行查询
        </el-button>
        <el-button @click="resetSql" size="large">重置</el-button>
      </div>
    </div>

    <!-- 主查询结果表 -->
    <div class="result-box" v-if="columns.length > 0">
      <el-table 
        :data="tableData" 
        border 
        stripe 
        style="width: 100%" 
        v-loading="loading"
        @cell-click="handleCellClick"
      >
        <el-table-column v-for="col in columns" :key="col" :prop="col" :label="col">
          <template #default="scope">
            <!-- 只有被精确解析为聚合指标的列，才可以点击下钻 -->
            <span 
              v-if="metricColumns.has(col)" 
              class="clickable-metric"
              title="点击查看此聚合结果的底层明细数据"
            >
              {{ scope.row[col] }}
            </span>
            <span v-else>{{ scope.row[col] }}</span>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <!-- 数据明细下钻弹窗 -->
    <el-dialog
      v-model="detailVisible"
      title="指标底层明细数据"
      width="85%"
      destroy-on-close
    >
      <div class="detail-context">
        <el-tag v-for="(val, key) in currentContext.filters" :key="key" style="margin-right: 10px; margin-bottom: 10px;" type="success">
          {{ key }}: {{ val }}
        </el-tag>
      </div>
      
      <el-table :data="detailData" border stripe height="400" v-loading="detailLoading">
        <el-table-column v-for="col in detailColumns" :key="col" :prop="col" :label="col" show-overflow-tooltip />
      </el-table>
      
      <div class="pagination-box">
        <el-pagination
          background
          layout="total, prev, pager, next"
          :total="detailTotal"
          :page-size="detailPageSize"
          :current-page="detailPage"
          @current-change="handlePageChange"
        />
      </div>
    </el-dialog>

  </el-card>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'

const API_BASE = 'http://127.0.0.1:8000/api/v1/data'

// 解析 SQL 中 SELECT 子句，提取出按逗号分隔的表达式（忽略括号内的逗号）
const splitSelectClause = (clause) => {
  const parts = []
  let current = ''
  let parenDepth = 0
  for (let i = 0; i < clause.length; i++) {
    const char = clause[i]
    if (char === '(') parenDepth++
    else if (char === ')') parenDepth--
    else if (char === ',' && parenDepth === 0) {
      parts.push(current.trim())
      current = ''
      continue
    }
    current += char
  }
  if (current) parts.push(current.trim())
  return parts
}

// === 主查询状态 ===
const rawSql = ref('SELECT country, count(*) as order_count, sum(revenue) as total_rev \nFROM bi_demo.orders \nGROUP BY country')
const loading = ref(false)
const tableData = ref([])
const columns = ref([])
const metricColumns = ref(new Set()) // 存储被判定为聚合指标的列名

// === 明细弹窗状态 ===
const detailVisible = ref(false)
const detailLoading = ref(false)
const detailData = ref([])
const detailColumns = ref([])
const detailTotal = ref(0)
const detailPage = ref(1)
const detailPageSize = ref(10)

// 存储当前点击的上下文（用于分页）
const currentContext = ref({
  fromClause: '',
  whereClause: '',
  filters: {}
})

// === 执行主查询 ===
const executeMainQuery = async () => {
  if (!rawSql.value.trim()) {
    ElMessage.warning('请输入 SQL 语句')
    return
  }
  loading.value = true
  try {
    const res = await axios.post(`${API_BASE}/query/raw`, { sql: rawSql.value })
    columns.value = res.data.columns
    tableData.value = res.data.data
    
    // 解析哪些列是聚合指标列，只有这些列允许下钻
    metricColumns.value = new Set()
    const sqlMatch = rawSql.value.match(/SELECT\s+([\s\S]+?)\s+FROM/i)
    const selectClause = sqlMatch ? sqlMatch[1] : ''
    const expressions = splitSelectClause(selectClause)
    
    columns.value.forEach(col => {
      // 1. 如果列名本身就是函数形式，例如 count()
      if (/^(count|sum|avg|max|min)\b/i.test(col)) {
        metricColumns.value.add(col)
        return
      }
      // 2. 检查 SQL 选择的表达式中，是否为聚合函数的别名
      if (selectClause) {
        const escapedCol = col.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
        const regex = new RegExp(`\\b(count|sum|avg|max|min)\\b\\s*\\([\\s\\S]*\\)\\s+(?:AS\\s+)?[\`"']?${escapedCol}[\`"']?$`, 'i')
        for (const expr of expressions) {
          if (regex.test(expr)) {
            metricColumns.value.add(col)
            break
          }
        }
      }
    })
    
    ElMessage.success('查询成功')
  } catch (error) {
    ElMessage.error('SQL执行失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    loading.value = false
  }
}

const resetSql = () => {
  rawSql.value = 'SELECT * FROM bi_demo.orders LIMIT 10'
}

// === 处理单元格点击 (下钻明细) ===
const handleCellClick = (row, column, cell, event) => {
  const colName = column.property
  
  // 仅对被判定为指标的列响应点击下钻
  if (!metricColumns.value.has(colName)) return

  // 构造 WHERE 条件字典 (将同行中的维度作为过滤条件)
  const filtersMap = {}
  
  for (const key in row) {
    // 只要是被判定为指标的列，就全部跳过，不作为 WHERE 过滤条件
    if (metricColumns.value.has(key)) continue
    
    const val = row[key]
    if (val === null || val === undefined) continue
    
    filtersMap[key] = val
  }

  // 保存上下文
  currentContext.value = {
    filters: filtersMap
  }

  // 重置分页并打开弹窗
  detailPage.value = 1
  detailVisible.value = true
  
  // 加载明细数据
  loadDetailData()
}

// === 加载分页明细数据 ===
const loadDetailData = async (page = 1) => {
  detailPage.value = page
  detailLoading.value = true
  
  const { filters } = currentContext.value
  const offset = (detailPage.value - 1) * detailPageSize.value
  
  try {
    const res = await axios.post(`${API_BASE}/drill-through`, {
      raw_sql: rawSql.value.trim(),
      filters: filters,
      limit: detailPageSize.value,
      offset: offset
    })
    
    detailTotal.value = res.data.total
    detailColumns.value = res.data.columns
    detailData.value = res.data.data
    
  } catch (error) {
    ElMessage.error('明细数据加载失败: ' + (error.response?.data?.detail || error.message))
  } finally {
    detailLoading.value = false
  }
}

const handlePageChange = (page) => {
  loadDetailData(page)
}

onMounted(() => {
  // 初始加载一次默认数据
  executeMainQuery()
})
</script>

<style scoped>
.dashboard-card {
  min-height: 85vh;
}
.header-section {
  margin-bottom: 20px;
}
.header-section h2 {
  margin: 0 0 10px 0;
  color: #303133;
}
.subtitle {
  color: #606266;
  font-size: 14px;
  margin: 0;
}
.query-box {
  background-color: #f8f9fa;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 25px;
  border: 1px solid #ebeef5;
}
.sql-input {
  font-family: 'Courier New', Courier, monospace;
}
.action-bar {
  margin-top: 15px;
  display: flex;
  gap: 10px;
}
.result-box {
  margin-top: 20px;
}
.clickable-metric {
  color: #409EFF;
  font-weight: bold;
  cursor: pointer;
  text-decoration: underline;
  transition: all 0.2s;
}
.clickable-metric:hover {
  color: #66b1ff;
}
.detail-context {
  margin-bottom: 15px;
  background-color: #f4f4f5;
  padding: 10px;
  border-radius: 4px;
}
.pagination-box {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}
</style>
