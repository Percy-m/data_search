<template>
  <el-container class="dashboard-container">
    <!-- 左侧：数据看板列表 -->
    <el-aside width="300px" class="saved-queries-aside">
      <div class="aside-header">
        <h3>我的数据看板</h3>
        <el-button type="primary" size="small" icon="Plus" @click="startNewAnalysis" circle title="新建分析"></el-button>
      </div>
      <el-menu default-active="" class="saved-queries-menu">
        <el-menu-item 
          v-for="query in savedQueries" 
          :key="query.id" 
          :index="String(query.id)"
          @click="loadSavedQuery(query)"
        >
          <div class="menu-item-content">
            <span class="query-name" :title="query.name">{{ query.name }}</span>
            <el-button type="danger" link icon="Delete" @click.stop="deleteSavedQuery(query.id)" title="删除此看板"></el-button>
          </div>
        </el-menu-item>
        <div v-if="savedQueries.length === 0" class="empty-text">暂无保存的数据看板</div>
      </el-menu>
    </el-aside>

    <!-- 右侧：主要工作区 -->
    <el-main>
      <el-card class="dashboard-card">
        <div class="header-section">
          <div>
            <h2>统一数据分析控制台</h2>
            <p class="subtitle">支持标准数据明细查询、多表 JOIN、聚合分析。点击结果中的<strong>数值指标</strong>即可自动下钻查看底层明细数据。</p>
          </div>
          <div class="header-actions" v-if="currentContext.loadedBoardId">
            <el-button 
              type="info" 
              plain 
              :icon="isViewingSavedBoard ? 'Edit' : 'View'" 
              @click="toggleEditMode"
            >
              {{ isViewingSavedBoard ? '查看 / 编辑 SQL' : '退出编辑模式' }}
            </el-button>
          </div>
        </div>

        <!-- SQL 输入区 (阅览模式下隐藏) -->
        <div class="query-box" v-show="!isViewingSavedBoard">
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
            <el-button @click="showSaveDialog" size="large" type="success" plain>保存为新看板</el-button>
            <el-button @click="resetSql" size="large">重置示例</el-button>
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
              @current-change="loadDetailData"
            />
          </div>
        </el-dialog>
        
        <!-- 保存看板对话框 -->
        <el-dialog v-model="saveDialogVisible" title="保存数据看板" width="30%">
          <el-form @submit.prevent>
            <el-form-item label="看板名称">
              <el-input v-model="saveQueryName" placeholder="请输入看板业务名称" />
            </el-form-item>
          </el-form>
          <template #footer>
            <span class="dialog-footer">
              <el-button @click="saveDialogVisible = false">取消</el-button>
              <el-button type="primary" @click="saveCurrentQuery" :loading="savingQuery">保存</el-button>
            </span>
          </template>
        </el-dialog>

      </el-card>
    </el-main>
  </el-container>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Plus, Edit } from '@element-plus/icons-vue'

const API_BASE = 'http://127.0.0.1:8000/api/v1/data'
const META_API_BASE = 'http://127.0.0.1:8000/api/v1/saved-queries'

// === 看板状态 ===
const savedQueries = ref([])
const saveDialogVisible = ref(false)
const saveQueryName = ref('')
const savingQuery = ref(false)
const isViewingSavedBoard = ref(false) // 是否处于看板阅览模式（隐藏输入框）

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
const rawSql = ref('SELECT o.country, count(DISTINCT o.order_id) as unique_orders, count(DISTINCT c.customer_id) as unique_customers, count(DISTINCT s.shipping_company) as active_carriers, sum(o.revenue) as total_revenue \nFROM bi_demo.orders o \nJOIN bi_demo.customers c ON o.customer_id = c.customer_id \nJOIN bi_demo.shipping s ON o.order_id = s.order_id \nGROUP BY o.country \nORDER BY total_revenue DESC')
const loading = ref(false)
const tableData = ref([])
const columns = ref([])
const metricColumns = ref(new Set()) 

// === 明细弹窗状态 ===
const detailVisible = ref(false)
const detailLoading = ref(false)
const detailData = ref([])
const detailColumns = ref([])
const detailTotal = ref(0)
const detailPage = ref(1)
const detailPageSize = ref(10)

const currentContext = ref({
  filters: {},
  metric: '',
  loadedBoardId: null // 记录当前载入的看板ID
})

// === 获取固化查询列表 ===
const fetchSavedQueries = async () => {
  try {
    const res = await axios.get(META_API_BASE + '/')
    savedQueries.value = res.data
  } catch (error) {
    ElMessage.error('获取固化查询列表失败')
  }
}

// === 载入固化看板并执行 ===
const loadSavedQuery = (query) => {
  rawSql.value = query.raw_sql
  currentContext.value.loadedBoardId = query.id
  isViewingSavedBoard.value = true // 进入看板阅览模式，隐藏 SQL 输入框
  executeMainQuery()
}

// === 开启新分析 (退出阅览模式) ===
const startNewAnalysis = () => {
  isViewingSavedBoard.value = false
  currentContext.value.loadedBoardId = null
  rawSql.value = ''
  columns.value = []
  tableData.value = []
}

// === 切换编辑模式 ===
const toggleEditMode = () => {
  isViewingSavedBoard.value = !isViewingSavedBoard.value
}

// === 弹出保存对话框 ===
const showSaveDialog = () => {
  if (!rawSql.value.trim()) {
    ElMessage.warning('没有可保存的 SQL 语句')
    return
  }
  saveQueryName.value = ''
  saveDialogVisible.value = true
}

// === 提交保存固化查询 ===
const saveCurrentQuery = async () => {
  if (!saveQueryName.value.trim()) {
    ElMessage.warning('请输入名称')
    return
  }
  savingQuery.value = true
  try {
    await axios.post(META_API_BASE + '/', {
      name: saveQueryName.value.trim(),
      raw_sql: rawSql.value.trim()
    })
    ElMessage.success('保存成功')
    saveDialogVisible.value = false
    fetchSavedQueries()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '保存失败')
  } finally {
    savingQuery.value = false
  }
}

// === 删除固化查询 ===
const deleteSavedQuery = (id) => {
  ElMessageBox.confirm('确定要删除这条固化查询吗?', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  }).then(async () => {
    try {
      await axios.delete(`${META_API_BASE}/${id}`)
      ElMessage.success('删除成功')
      fetchSavedQueries()
    } catch (error) {
      ElMessage.error('删除失败')
    }
  }).catch(() => {})
}

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
    
    // 解析哪些列是聚合指标列
    metricColumns.value = new Set()
    const sqlMatch = rawSql.value.match(/SELECT\s+([\s\S]+?)\s+FROM/i)
    const selectClause = sqlMatch ? sqlMatch[1] : ''
    const expressions = splitSelectClause(selectClause)
    
    columns.value.forEach(col => {
      if (/^(count|sum|avg|max|min)\b/i.test(col)) {
        metricColumns.value.add(col)
        return
      }
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
  
  if (!metricColumns.value.has(colName)) return

  const filtersMap = {}
  
  for (const key in row) {
    if (metricColumns.value.has(key)) continue
    
    const val = row[key]
    if (val === null || val === undefined) continue
    
    filtersMap[key] = val
  }

  currentContext.value = {
    filters: filtersMap,
    metric: colName
  }

  detailPage.value = 1
  detailVisible.value = true
  
  loadDetailData()
}

// === 加载分页明细数据 ===
const loadDetailData = async (colName, page = 1) => {
  if (typeof colName === 'number') {
    page = colName
    colName = currentContext.value.metric
  } else if (!colName || typeof colName === 'object') {
    colName = currentContext.value.metric
  }
  
  detailPage.value = page
  detailLoading.value = true
  
  const { filters } = currentContext.value
  const offset = (detailPage.value - 1) * detailPageSize.value
  
  try {
    const res = await axios.post(`${API_BASE}/drill-through`, {
      raw_sql: rawSql.value.trim(),
      filters: filters,
      clicked_metric: colName,
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

onMounted(() => {
  fetchSavedQueries()
  executeMainQuery()
})
</script>

<style scoped>
.dashboard-container {
  min-height: 85vh;
}
.saved-queries-aside {
  background-color: #ffffff;
  border-right: 1px solid #dcdfe6;
  padding-right: 1px;
}
.aside-header {
  padding: 15px 20px;
  border-bottom: 1px solid #ebeef5;
  background-color: #f8f9fa;
}
.aside-header h3 {
  margin: 0;
  color: #303133;
  font-size: 16px;
}
.saved-queries-menu {
  border-right: none;
}
.menu-item-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;
}
.query-name {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 200px;
}
.empty-text {
  text-align: center;
  color: #909399;
  padding: 30px 0;
  font-size: 14px;
}
.dashboard-card {
  height: 100%;
}
.header-section {
  margin-bottom: 20px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}
.header-actions {
  margin-top: 10px;
}
.aside-header {
  padding: 15px 20px;
  border-bottom: 1px solid #ebeef5;
  background-color: #f8f9fa;
  display: flex;
  justify-content: space-between;
  align-items: center;
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
