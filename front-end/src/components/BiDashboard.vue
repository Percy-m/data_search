<template>
  <div class="app-container">
    <div class="main-header">
      <h2>统一数据分析控制台</h2>
      <p class="subtitle">支持多数据源直连、拖拽看板、可视化数据下钻。</p>
    </div>

    <el-tabs v-model="activeTab" class="main-tabs" type="border-card">
      <!-- Tab 1: 数据源管理 -->
      <el-tab-pane label="配置中心 (Data Sources)" name="datasource">
        <div class="ds-container">
          <div style="margin-bottom: 15px; display: flex; justify-content: space-between;">
            <h3>已接入的数据源</h3>
            <el-button type="primary" icon="Plus" @click="showDsDialog">新增数据源</el-button>
          </div>
          <el-table :data="dataSources" border stripe>
            <el-table-column prop="id" label="ID" width="80" />
            <el-table-column prop="name" label="连接名称" />
            <el-table-column prop="type" label="类型" width="120">
              <template #default="scope">
                <el-tag size="small">{{ scope.row.type }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="host" label="主机地址" />
            <el-table-column prop="database" label="数据库" />
            <el-table-column label="操作" width="100" align="center">
              <template #default="scope">
                <el-button type="danger" link icon="Delete" @click="deleteDataSource(scope.row.id)"></el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>

      <!-- Tab 2: 数据看板 (阅览模式) -->
      <el-tab-pane label="数据看板 (Dashboard)" name="dashboard">
        <!-- ... 保持原有 dashboard tab 不变 ... -->
        <el-container class="dashboard-container">
          <el-aside width="300px" class="saved-queries-aside">
            <div class="aside-header">
              <h3>我的数据看板</h3>
            </div>
            <el-menu :default-active="String(boardSelectedId || '')" class="saved-queries-menu">
              <el-menu-item 
                v-for="query in savedQueries" 
                :key="query.id" 
                :index="String(query.id)"
                @click="loadSavedBoard(query)"
              >
                <div class="menu-item-content">
                  <span class="query-name" :title="query.name">{{ query.name }}</span>
                  <div class="actions">
                    <el-button type="primary" link icon="Edit" @click.stop="editSavedQuery(query)" title="在工作台编辑 SQL"></el-button>
                    <el-button type="danger" link icon="Delete" @click.stop="deleteSavedQuery(query.id)" title="删除此看板"></el-button>
                  </div>
                </div>
              </el-menu-item>
              <div v-if="savedQueries.length === 0" class="empty-text">暂无保存的数据看板</div>
            </el-menu>
          </el-aside>

          <el-main class="dashboard-main">
            <div v-if="boardSelectedId" class="board-view">
              <div class="board-title-section">
                <h2>{{ boardName }}</h2>
                <el-button type="warning" plain icon="Filter" @click="openThresholdDialog">配置高亮阈值</el-button>
              </div>
              
              <el-table 
                :data="boardTableData" 
                border 
                stripe 
                style="width: 100%" 
                v-loading="boardLoading"
                :cell-style="getBoardCellStyle"
                @cell-click="(row, col, cell, evt) => handleCellClick(row, col, boardSql, boardMetricColumns)"
              >
                <el-table-column v-for="col in boardColumns" :key="col" :prop="col" :label="col">
                  <template #default="scope">
                    <span 
                      v-if="boardMetricColumns.has(col)" 
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
            <div v-else class="empty-board">
              <el-empty description="请从左侧选择一个数据看板进行预览"></el-empty>
            </div>
          </el-main>
        </el-container>
      </el-tab-pane>

      <!-- Tab 3: SQL 分析工作台 (编辑模式) -->
      <el-tab-pane label="SQL 分析工作台 (Workspace)" name="editor">
        <el-container class="editor-main-container">
          <!-- 工作台左侧：数据源与表结构 -->
          <el-aside width="250px" class="editor-aside">
            <div style="padding: 10px;">
              <el-select v-model="currentDataSourceId" placeholder="选择数据源" style="width: 100%" @change="loadTables">
                <el-option v-for="ds in dataSources" :key="ds.id" :label="ds.name" :value="ds.id" />
              </el-select>
            </div>
            <el-menu class="table-tree-menu" @select="handleTableSelect" v-loading="tablesLoading">
              <el-menu-item v-for="t in tables" :key="t" :index="t">
                <el-icon><Menu /></el-icon>
                <span>{{ t }}</span>
              </el-menu-item>
            </el-menu>
          </el-aside>

          <!-- 工作台右侧：SQL 编写区 -->
          <el-main class="editor-container">
            <div class="query-box">
              <el-input
                v-model="editorSql"
                type="textarea"
                :rows="8"
                placeholder="请输入 SQL 语句..."
                class="sql-input"
              />
              <div class="action-bar">
                <el-button type="primary" size="large" @click="runEditorQuery" :loading="editorLoading">
                  执行查询
                </el-button>
                <el-button @click="showSaveDialog" size="large" type="success" plain>保存为新看板</el-button>
                <el-button @click="editorSql = 'SELECT * FROM bi_demo.orders LIMIT 10'" size="large">重置</el-button>
              </div>
            </div>

            <div class="result-box" v-if="editorColumns.length > 0">
              <el-table 
                :data="editorTableData" 
                border 
                stripe 
                style="width: 100%" 
                v-loading="editorLoading"
                @cell-click="(row, col, cell, evt) => handleCellClick(row, col, editorSql, editorMetricColumns)"
              >
                <el-table-column v-for="col in editorColumns" :key="col" :prop="col" :label="col">
                  <template #default="scope">
                    <span 
                      v-if="editorMetricColumns.has(col)" 
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
          </el-main>
        </el-container>
      </el-tab-pane>
    </el-tabs>

    <!-- 新增数据源对话框 -->
    <el-dialog v-model="dsDialogVisible" title="接入新数据源" width="30%">
      <el-form :model="dsForm" label-width="100px">
        <el-form-item label="连接名称">
          <el-input v-model="dsForm.name" placeholder="例如: 生产库-ClickHouse" />
        </el-form-item>
        <el-form-item label="数据库类型">
          <el-select v-model="dsForm.type" style="width: 100%">
            <el-option label="ClickHouse" value="clickhouse" />
          </el-select>
        </el-form-item>
        <el-form-item label="主机地址">
          <el-input v-model="dsForm.host" placeholder="localhost" />
        </el-form-item>
        <el-form-item label="端口">
          <el-input-number v-model="dsForm.port" :controls="false" style="width: 100%" />
        </el-form-item>
        <el-form-item label="用户名">
          <el-input v-model="dsForm.username" placeholder="default" />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="dsForm.password" type="password" show-password />
        </el-form-item>
        <el-form-item label="默认数据库">
          <el-input v-model="dsForm.database" placeholder="default" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="dsDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="saveDataSource" :loading="savingDs">测试连接并保存</el-button>
        </span>
      </template>
    </el-dialog>
    <!-- ... 省略之前存在的 Dialog (明细弹窗、保存看板、阈值配置等) ... -->

    <!-- 数据明细下钻弹窗 (全屏共享) -->
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

    <!-- 阈值高亮配置对话框 -->
    <el-dialog v-model="thresholdDialogVisible" title="看板条件高亮配置" width="60%">
      <div style="margin-bottom: 15px;">
        <el-button type="primary" icon="Plus" @click="addThresholdRule" size="small">新增规则</el-button>
      </div>
      
      <el-table :data="currentThresholds" border size="small">
        <el-table-column label="目标列" width="180">
          <template #default="scope">
            <el-select v-model="scope.row.column" placeholder="选择列" size="small">
              <el-option v-for="col in boardColumns" :key="col" :label="col" :value="col" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="条件" width="120">
          <template #default="scope">
            <el-select v-model="scope.row.operator" placeholder="条件" size="small">
              <el-option label="大于 (>)" value=">" />
              <el-option label="小于 (<)" value="<" />
              <el-option label="等于 (=)" value="=" />
              <el-option label="大于等于 (>=)" value=">=" />
              <el-option label="小于等于 (<=)" value="<=" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="阈值" width="150">
          <template #default="scope">
            <el-input-number v-model="scope.row.value" :controls="false" style="width: 100%" size="small" />
          </template>
        </el-table-column>
        <el-table-column label="背景色" width="100">
          <template #default="scope">
            <el-color-picker v-model="scope.row.color" show-alpha size="small" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80" align="center">
          <template #default="scope">
            <el-button type="danger" link icon="Delete" @click="removeThresholdRule(scope.$index)"></el-button>
          </template>
        </el-table-column>
      </el-table>

      <template #footer>
        <span class="dialog-footer">
          <el-button @click="thresholdDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="saveThresholds" :loading="savingThresholds">保存配置</el-button>
        </span>
      </template>
    </el-dialog>

  </div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Edit, Plus, Menu } from '@element-plus/icons-vue'

const API_BASE = 'http://127.0.0.1:8000/api/v1/data'
const META_API_BASE = 'http://127.0.0.1:8000/api/v1/saved-queries'
const DS_API_BASE = 'http://127.0.0.1:8000/api/v1/data-sources'

// === 数据源管理状态 ===
const dataSources = ref([])
const dsDialogVisible = ref(false)
const savingDs = ref(false)
const dsForm = ref({
  name: '',
  type: 'clickhouse',
  host: 'localhost',
  port: 8123,
  username: 'default',
  password: '',
  database: 'default'
})

// === 全局状态 ===
const activeTab = ref('dashboard')
const savedQueries = ref([])

// === 看板阅读模式状态 (Tab 1) ===
const boardSelectedId = ref(null)
const boardName = ref('')
const boardSql = ref('')
const boardLoading = ref(false)
const boardTableData = ref([])
const boardColumns = ref([])
const boardMetricColumns = ref(new Set())

// === SQL 分析工作台状态 (Tab 3) ===
const currentDataSourceId = ref(null)
const tables = ref([])
const tablesLoading = ref(false)
const editorSql = ref('SELECT * FROM system.tables LIMIT 10')
const editorLoading = ref(false)
const editorTableData = ref([])
const editorColumns = ref([])
const editorMetricColumns = ref(new Set())

// === 明细下钻弹窗状态 ===
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
  sourceSql: ''
})

// === 保存弹窗状态 ===
const saveDialogVisible = ref(false)
const saveQueryName = ref('')
const savingQuery = ref(false)

// === 阈值高亮配置状态 ===
const thresholdDialogVisible = ref(false)
const currentThresholds = ref([])
const savingThresholds = ref(false)

// 解析 SQL 中 SELECT 子句
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

// === 通用执行 SQL 函数 ===
const executeQuery = async (sql, loadingRef, columnsRef, dataRef, metricsRef) => {
  if (!sql.trim()) {
    ElMessage.warning('请输入 SQL 语句')
    return false
  }
  loadingRef.value = true
  try {
    const headers = currentDataSourceId.value ? { 'x-data-source-id': currentDataSourceId.value } : {}
    const res = await axios.post(`${API_BASE}/query/raw`, { sql: sql }, { headers })
    columnsRef.value = res.data.columns
    dataRef.value = res.data.data
    
    // 解析聚合指标列
    const metricCols = new Set()
    const sqlMatch = sql.match(/SELECT\s+([\s\S]+?)\s+FROM/i)
    const selectClause = sqlMatch ? sqlMatch[1] : ''
    const expressions = splitSelectClause(selectClause)
    
    columnsRef.value.forEach(col => {
      if (/^(count|sum|avg|max|min)\b/i.test(col)) {
        metricCols.add(col)
        return
      }
      if (selectClause) {
        const escapedCol = col.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
        const regex = new RegExp(`\\b(count|sum|avg|max|min)\\b\\s*\\([\\s\\S]*\\)\\s+(?:AS\\s+)?[\`"']?${escapedCol}[\`"']?$`, 'i')
        for (const expr of expressions) {
          if (regex.test(expr)) {
            metricCols.add(col)
            break
          }
        }
      }
    })
    metricsRef.value = metricCols
    return true
  } catch (error) {
    ElMessage.error('SQL执行失败: ' + (error.response?.data?.detail || error.message))
    return false
  } finally {
    loadingRef.value = false
  }
}

// === 工作台执行查询 ===
const runEditorQuery = async () => {
  const success = await executeQuery(editorSql.value, editorLoading, editorColumns, editorTableData, editorMetricColumns)
  if (success) ElMessage.success('工作台查询成功')
}

// === 获取数据源列表 ===
const fetchDataSources = async () => {
  try {
    const res = await axios.get(DS_API_BASE + '/')
    dataSources.value = res.data
    if (dataSources.value.length > 0 && !currentDataSourceId.value) {
      currentDataSourceId.value = dataSources.value[0].id
      loadTables()
    }
  } catch (error) {
    ElMessage.error('获取数据源失败')
  }
}

// === 数据源管理操作 ===
const showDsDialog = () => {
  dsForm.value = { name: '', type: 'clickhouse', host: 'localhost', port: 8123, username: 'default', password: '', database: 'default' }
  dsDialogVisible.value = true
}

const saveDataSource = async () => {
  savingDs.value = true
  try {
    await axios.post(DS_API_BASE + '/', dsForm.value)
    ElMessage.success('连接成功并保存')
    dsDialogVisible.value = false
    fetchDataSources()
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '连接失败')
  } finally {
    savingDs.value = false
  }
}

const deleteDataSource = (id) => {
  ElMessageBox.confirm('确定要删除该数据源吗?', '提示', { type: 'warning' }).then(async () => {
    try {
      await axios.delete(`${DS_API_BASE}/${id}`)
      ElMessage.success('删除成功')
      if (currentDataSourceId.value === id) {
        currentDataSourceId.value = null
        tables.value = []
      }
      fetchDataSources()
    } catch (e) {
      ElMessage.error('删除失败')
    }
  }).catch(() => {})
}

// === 加载左侧表结构树 ===
const loadTables = async () => {
  if (!currentDataSourceId.value) return
  tablesLoading.value = true
  try {
    const res = await axios.get(`${API_BASE}/meta/tables`, {
      headers: { 'x-data-source-id': currentDataSourceId.value }
    })
    tables.value = res.data.tables
  } catch (error) {
    ElMessage.error('获取表结构失败')
    tables.value = []
  } finally {
    tablesLoading.value = false
  }
}

const handleTableSelect = (tableName) => {
  editorSql.value = `SELECT * FROM ${tableName} LIMIT 10`
}

// === 获取看板列表 ===
const fetchSavedQueries = async () => {
  try {
    const res = await axios.get(META_API_BASE + '/')
    savedQueries.value = res.data
  } catch (error) {
    ElMessage.error('获取看板列表失败')
  }
}

// === 载入并阅览看板 ===
const loadSavedBoard = async (query) => {
  boardSelectedId.value = query.id
  boardName.value = query.name
  boardSql.value = query.raw_sql
  // 初始化该看板对应的阈值规则
  currentThresholds.value = Array.isArray(query.thresholds) ? JSON.parse(JSON.stringify(query.thresholds)) : []
  
  await executeQuery(boardSql.value, boardLoading, boardColumns, boardTableData, boardMetricColumns)
}

// === 从看板跳转到工作台编辑 ===
const editSavedQuery = (query) => {
  editorSql.value = query.raw_sql
  activeTab.value = 'editor'
  runEditorQuery()
}

// === 保存新看板 ===
const showSaveDialog = () => {
  if (!editorSql.value.trim()) {
    ElMessage.warning('没有可保存的 SQL 语句')
    return
  }
  saveQueryName.value = ''
  saveDialogVisible.value = true
}

const saveCurrentQuery = async () => {
  if (!saveQueryName.value.trim()) {
    ElMessage.warning('请输入名称')
    return
  }
  savingQuery.value = true
  try {
    const res = await axios.post(META_API_BASE + '/', {
      name: saveQueryName.value.trim(),
      raw_sql: editorSql.value.trim(),
      thresholds: []
    })
    ElMessage.success('保存成功')
    saveDialogVisible.value = false
    await fetchSavedQueries()
    
    // 保存后，自动跳转到看板页面查看
    activeTab.value = 'dashboard'
    loadSavedBoard(res.data)
  } catch (error) {
    ElMessage.error(error.response?.data?.detail || '保存失败')
  } finally {
    savingQuery.value = false
  }
}

const deleteSavedQuery = (id) => {
  ElMessageBox.confirm('确定要删除这条看板吗?', '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  }).then(async () => {
    try {
      await axios.delete(`${META_API_BASE}/${id}`)
      ElMessage.success('删除成功')
      if (boardSelectedId.value === id) {
        boardSelectedId.value = null
        boardTableData.value = []
      }
      fetchSavedQueries()
    } catch (error) {
      ElMessage.error('删除失败')
    }
  }).catch(() => {})
}

// === 阈值高亮功能 ===
const openThresholdDialog = () => {
  if (!boardSelectedId.value) return
  // Deep clone to avoid mutating state before save
  const currentBoard = savedQueries.value.find(q => q.id === boardSelectedId.value)
  if (currentBoard) {
     currentThresholds.value = Array.isArray(currentBoard.thresholds) 
        ? JSON.parse(JSON.stringify(currentBoard.thresholds)) 
        : []
  }
  thresholdDialogVisible.value = true
}

const addThresholdRule = () => {
  currentThresholds.value.push({
    column: '',
    operator: '>',
    value: 0,
    color: 'rgba(245, 108, 108, 0.2)' // Default light red
  })
}

const removeThresholdRule = (index) => {
  currentThresholds.value.splice(index, 1)
}

const saveThresholds = async () => {
  if (!boardSelectedId.value) return
  savingThresholds.value = true
  try {
    const res = await axios.put(`${META_API_BASE}/${boardSelectedId.value}`, {
      thresholds: currentThresholds.value
    })
    ElMessage.success('高亮阈值配置已保存')
    
    // Update local state
    const queryIdx = savedQueries.value.findIndex(q => q.id === boardSelectedId.value)
    if (queryIdx !== -1) {
      savedQueries.value[queryIdx].thresholds = res.data.thresholds
    }
    
    thresholdDialogVisible.value = false
  } catch (error) {
    ElMessage.error('保存失败')
  } finally {
    savingThresholds.value = false
  }
}

// 动态计算单元格样式
const getBoardCellStyle = ({ row, column }) => {
  const colName = column.property
  if (!currentThresholds.value || currentThresholds.value.length === 0) return {}
  
  for (const rule of currentThresholds.value) {
    if (rule.column === colName) {
      const cellValue = Number(row[colName])
      if (isNaN(cellValue)) continue
      
      const ruleValue = Number(rule.value)
      let match = false
      
      switch (rule.operator) {
        case '>': match = cellValue > ruleValue; break;
        case '<': match = cellValue < ruleValue; break;
        case '=': match = cellValue === ruleValue; break;
        case '>=': match = cellValue >= ruleValue; break;
        case '<=': match = cellValue <= ruleValue; break;
      }
      
      if (match) {
        // 如果文字和背景对比度差，也可以在这里扩展控制字体颜色
        return { backgroundColor: rule.color }
      }
    }
  }
  return {}
}

// === 处理单元格点击 (下钻明细) ===
const handleCellClick = (row, column, sourceSql, metricCols) => {
  const colName = column.property
  if (!metricCols.has(colName)) return

  const filtersMap = {}
  for (const key in row) {
    if (metricCols.has(key)) continue
    const val = row[key]
    if (val === null || val === undefined) continue
    filtersMap[key] = val
  }

  currentContext.value = {
    filters: filtersMap,
    metric: colName,
    sourceSql: sourceSql
  }

  detailPage.value = 1
  detailVisible.value = true
  loadDetailData()
}

const loadDetailData = async (colName, page = 1) => {
  if (typeof colName === 'number') {
    page = colName
    colName = currentContext.value.metric
  } else if (!colName || typeof colName === 'object') {
    colName = currentContext.value.metric
  }
  
  detailPage.value = page
  detailLoading.value = true
  
  const { filters, sourceSql } = currentContext.value
  const offset = (detailPage.value - 1) * detailPageSize.value
  
  try {
    const headers = currentDataSourceId.value ? { 'x-data-source-id': currentDataSourceId.value } : {}
    const res = await axios.post(`${API_BASE}/drill-through`, {
      raw_sql: sourceSql.trim(),
      filters: filters,
      clicked_metric: colName,
      limit: detailPageSize.value,
      offset: offset
    }, { headers })
    
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
  fetchDataSources()
  fetchSavedQueries()
  runEditorQuery()
})
</script>

<style scoped>
.app-container {
  padding: 20px;
}
.main-header {
  margin-bottom: 20px;
  padding-left: 10px;
}
.main-header h2 {
  margin: 0 0 10px 0;
  color: #303133;
}
.subtitle {
  color: #606266;
  font-size: 14px;
  margin: 0;
}
.main-tabs {
  min-height: 80vh;
}
.dashboard-container {
  min-height: 70vh;
}
.saved-queries-aside {
  border-right: 1px solid #dcdfe6;
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
  max-width: 180px;
}
.actions {
  display: flex;
  gap: 5px;
}
.empty-text {
  text-align: center;
  color: #909399;
  padding: 30px 0;
  font-size: 14px;
}
.dashboard-main {
  padding: 20px 30px;
}
.board-title-section {
  margin-bottom: 20px;
  padding-bottom: 10px;
  border-bottom: 2px solid #ebeef5;
}
.board-title-section h2 {
  margin: 0;
  color: #303133;
}
.empty-board {
  margin-top: 100px;
}
.editor-container {
  padding: 10px;
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
