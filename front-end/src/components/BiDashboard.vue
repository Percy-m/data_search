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
            <!-- 如果是数字，我们认为它是指标，可以点击查看明细 -->
            <span 
              v-if="typeof scope.row[col] === 'number'" 
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

// === 主查询状态 ===
const rawSql = ref('SELECT country, count(*) as order_count, sum(revenue) as total_rev \nFROM bi_demo.orders \nGROUP BY country')
const loading = ref(false)
const tableData = ref([])
const columns = ref([])

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
  const cellValue = row[colName]
  
  // 仅对数字类型的列响应点击
  if (typeof cellValue !== 'number') return

  // 1. 提取原始 SQL 中的 FROM 子句 (支持简单的正则提取)
  const sql = rawSql.value.trim()
  const fromMatch = sql.match(/FROM\s+([\s\S]+?)(?:\s+GROUP\s+BY|\s+ORDER\s+BY|\s+LIMIT|$)/i)
  
  if (!fromMatch) {
    ElMessage.warning('当前 SQL 格式无法解析出基础表，无法查看明细')
    return
  }
  
  let fromClause = fromMatch[1].trim()

  // 2. 构造 WHERE 条件 (将同行中的维度作为过滤条件)
  const conditions = []
  const filtersDisplay = {} // 用于弹窗顶部展示
  
  for (const key in row) {
    // 跳过当前点击的指标列
    if (key === colName) continue
    // 粗略过滤掉其他看起来像指标的列
    if (/^(count|sum|avg|max|min|revenue|profit|margin|cnt|total)/i.test(key)) continue
    
    const val = row[key]
    if (val === null || val === undefined) continue
    
    filtersDisplay[key] = val
    if (typeof val === 'string') {
      // 避免单引号导致 SQL 注入/语法错误，简单转义
      const safeVal = val.replace(/'/g, "\\'")
      conditions.push(`${key} = '${safeVal}'`)
    } else {
      conditions.push(`${key} = ${val}`)
    }
  }

  let whereClause = conditions.length > 0 ? conditions.join(' AND ') : ''
  
  // 如果原 SQL 已经自带 WHERE，则拼接 AND
  if (whereClause) {
    if (fromClause.toUpperCase().includes(' WHERE ')) {
      whereClause = ` AND ${whereClause}`
    } else {
      whereClause = ` WHERE ${whereClause}`
    }
  }

  // 保存上下文
  currentContext.value = {
    fromClause,
    whereClause,
    filters: filtersDisplay
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
  
  const { fromClause, whereClause } = currentContext.value
  const offset = (detailPage.value - 1) * detailPageSize.value
  
  // 构造查询总数的 SQL
  const countSql = `SELECT count(*) as total FROM ${fromClause} ${whereClause}`
  // 构造查询当前页明细的 SQL
  const dataSql = `SELECT * FROM ${fromClause} ${whereClause} LIMIT ${detailPageSize.value} OFFSET ${offset}`

  try {
    // 并行请求总数和明细数据
    const [countRes, dataRes] = await Promise.all([
      axios.post(`${API_BASE}/query/raw`, { sql: countSql }),
      axios.post(`${API_BASE}/query/raw`, { sql: dataSql })
    ])
    
    // 解析总数
    if (countRes.data.data.length > 0) {
      detailTotal.value = Number(countRes.data.data[0].total)
    }
    
    // 解析明细数据
    detailColumns.value = dataRes.data.columns
    detailData.value = dataRes.data.data
    
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
