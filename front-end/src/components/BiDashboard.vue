<template>
  <div class="app-container">
    <div class="main-header">
      <h2>统一数据分析控制台</h2>
      <p class="subtitle">支持多数据源直连、拖拽看板、可视化数据下钻。</p>
    </div>

    <el-tabs v-model="activeTab" class="main-tabs" type="border-card" tab-position="left">
      <!-- Tab 1: 数据源管理 -->
      <el-tab-pane label="配置中心 (Data Sources)" name="datasource">
        <!-- ... 省略之前的数据源管理面板代码，保持不变 ... -->
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

      <!-- Tab 2: 组合看板 (Dashboards) -->
      <el-tab-pane label="数据看板 (Dashboards)" name="dashboard">
        <el-container class="dashboard-container">
          <!-- 左侧：看板列表 -->
          <el-aside width="250px" class="saved-queries-aside">
            <div class="aside-header">
              <h3>看板列表</h3>
              <el-button type="primary" size="small" icon="Plus" @click="showNewDashboardDialog" circle title="新建空看板"></el-button>
            </div>
            <el-menu :default-active="String(activeDashboardId || '')" class="saved-queries-menu">
              <el-menu-item 
                v-for="db in dashboards" 
                :key="db.id" 
                :index="String(db.id)"
                @click="loadDashboard(db)"
              >
                <div class="menu-item-content">
                  <span class="query-name" :title="db.name">{{ db.name }}</span>
                  <el-button type="danger" link icon="Delete" @click.stop="deleteDashboard(db.id)" title="删除看板"></el-button>
                </div>
              </el-menu-item>
              <div v-if="dashboards.length === 0" class="empty-text">暂无看板，请先创建</div>
            </el-menu>
          </el-aside>

          <!-- 右侧：看板画布 -->
          <el-main class="dashboard-main" style="background-color: #f0f2f5;">
            <div v-if="activeDashboard" class="board-view">
              <div class="board-title-section" style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 20px;">
                <div style="display: flex; align-items: center; gap: 10px;">
                  <h2 v-if="!isDashboardEditMode || !editingBoardName" style="margin:0;">{{ activeDashboard.name }}</h2>
                  <el-input v-else v-model="tempBoardName" size="small" @blur="saveBoardName" @keyup.enter="saveBoardName" style="width: 200px" />
                  
                  <el-button v-if="isDashboardEditMode && !editingBoardName" link icon="Edit" @click="startEditBoardName"></el-button>
                </div>
                
                <div>
                  <template v-if="!isDashboardEditMode">
                    <el-button type="primary" plain icon="Edit" @click="isDashboardEditMode = true">编辑看板</el-button>
                  </template>
                  <template v-else>
                    <el-button type="primary" plain icon="Plus" @click="showAddWidgetDialog">添加图表</el-button>
                    <el-button type="success" icon="Check" @click="saveDashboardLayout" :loading="savingLayout">保存并退出</el-button>
                    <el-button type="info" plain @click="cancelDashboardEdit">取消编辑</el-button>
                  </template>
                </div>
              </div>
              
              <!-- 拖拽网格区域 -->
              <grid-layout
                v-model:layout="activeDashboardLayout"
                :col-num="12"
                :row-height="30"
                :is-draggable="isDashboardEditMode"
                :is-resizable="isDashboardEditMode"
                :vertical-compact="true"
                :margin="[10, 10]"
                :use-css-transforms="true"
                :class="{'grid-edit-mode': isDashboardEditMode}"
              >
                <grid-item
                  v-for="item in activeDashboardLayout"
                  :key="item.i"
                  :x="item.x"
                  :y="item.y"
                  :w="item.w"
                  :h="item.h"
                  :i="item.i"
                  class="widget-card"
                  :class="{'widget-edit-mode': isDashboardEditMode}"
                >
                  <el-card shadow="hover" style="height: 100%; display: flex; flex-direction: column;" :body-style="{ padding: '10px', flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }">
                    <div class="widget-header">
                      <span class="widget-title">{{ item.query_name }}</span>
                      <div v-show="isDashboardEditMode">
                        <el-button type="warning" link icon="Filter" @click="openWidgetThresholds(item)" title="独立配置预警"></el-button>
                        <el-button type="danger" link icon="Close" @click="removeWidget(item.i)" title="移除"></el-button>
                      </div>
                    </div>
                    
                    <div class="widget-content" style="flex: 1; overflow: auto; margin-top: 10px;" v-loading="widgetLoading[item.i]">
                      <!-- Table View -->
                      <el-table 
                        v-if="widgetData[item.i] && (!item.chart_type || item.chart_type === 'table')"
                        :data="widgetData[item.i].data" 
                        border 
                        size="small"
                        style="width: 100%; height: 100%"
                        :cell-style="(ctx) => getWidgetCellStyle(ctx, item.query_thresholds)"
                        @cell-click="(row, col, cell, evt) => handleCellClick(row, col, item.query_sql, widgetData[item.i].metrics, item.data_source_id)"
                      >
                        <el-table-column 
                          v-for="c in widgetData[item.i].columns" 
                          :key="c" 
                          :prop="c" 
                          :label="c"
                          show-overflow-tooltip
                        >
                          <template #default="scope">
                            <span 
                              v-if="widgetData[item.i].metrics.has(c)" 
                              class="clickable-metric"
                            >
                              {{ scope.row[c] }}
                            </span>
                            <span v-else>{{ scope.row[c] }}</span>
                          </template>
                        </el-table-column>
                      </el-table>

                      <!-- ECharts View (Bar/Line/Pie) -->
                      <v-chart 
                        v-else-if="widgetData[item.i] && item.chart_type !== 'table'" 
                        :option="getChartOption(item)" 
                        autoresize 
                        style="width: 100%; height: 100%;"
                        @click="(params) => handleChartClick(params, item)"
                      />
                    </div>
                  </el-card>
                </grid-item>
              </grid-layout>
              
            </div>
            <div v-else class="empty-board" style="text-align: center; margin-top: 150px;">
              <el-empty description="请从左侧选择或新建一个 Dashboard"></el-empty>
            </div>
          </el-main>
        </el-container>
      </el-tab-pane>

      <!-- Tab 3: SQL 分析工作台 (Queries) -->
      <el-tab-pane label="分析工作台 (Queries)" name="editor">
        <el-container class="editor-main-container">
          <el-aside width="250px" class="editor-aside">
            <div style="padding: 10px; border-bottom: 1px solid #eee;">
              <h4>已保存的查询</h4>
            </div>
            <el-menu class="table-tree-menu">
              <el-menu-item 
                v-for="q in savedQueries" 
                :key="q.id" 
                :index="String(q.id)"
                @click="loadQueryToEditor(q)"
              >
                <el-icon><DataLine /></el-icon>
                <span :title="q.name" style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{{ q.name }}</span>
                <el-button type="danger" link icon="Delete" style="margin-left: auto;" @click.stop="deleteSavedQuery(q.id)"></el-button>
              </el-menu-item>
            </el-menu>
            
            <div style="padding: 10px; border-bottom: 1px solid #eee; margin-top: 10px;">
              <h4>物理表探索</h4>
              <el-select v-model="currentDataSourceId" placeholder="选择数据源" style="width: 100%; margin-top: 10px;" @change="loadTables">
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

          <el-main class="editor-container">
            <div class="query-box">
              <el-input
                v-model="editorSql"
                type="textarea"
                :rows="8"
                placeholder="请输入 SQL 语句..."
                class="sql-input"
              />
              <div class="action-bar" style="justify-content: space-between">
                <div>
                  <el-button type="primary" size="large" @click="runEditorQuery" :loading="editorLoading">
                    执行查询
                  </el-button>
                  <el-button @click="showSaveQueryDialog" size="large" type="success" plain>保存查询</el-button>
                  <el-button @click="editorSql = 'SELECT * FROM bi_demo.orders LIMIT 10'" size="large">重置</el-button>
                </div>
                <div style="display: flex; align-items: center; gap: 10px;">
                  <el-button type="warning" plain icon="Filter" size="small" @click="openEditorThresholds" title="配置默认预警染色">预警配置</el-button>
                  <span>图表类型预览：</span>
                  <el-select v-model="editorChartType" style="width: 120px">
                    <el-option label="Table 表格" value="table" />
                    <el-option label="Bar 柱状图" value="bar" />
                    <el-option label="Line 折线图" value="line" />
                    <el-option label="Pie 饼图" value="pie" />
                  </el-select>
                </div>
              </div>
            </div>

            <div class="result-box" style="height: 400px" v-if="editorColumns.length > 0">
              <!-- 预览：Table -->
              <el-table 
                v-if="editorChartType === 'table'"
                :data="editorTableData" 
                border 
                stripe 
                style="width: 100%; height: 100%" 
                v-loading="editorLoading"
                :cell-style="(ctx) => getWidgetCellStyle(ctx, editorThresholds)"
                @cell-click="(row, col, cell, evt) => handleCellClick(row, col, editorSql, editorMetricColumns, currentDataSourceId)"
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

              <!-- 预览：ECharts -->
              <v-chart 
                v-else
                :option="getEditorChartOption()" 
                autoresize 
                style="width: 100%; height: 100%;"
                @click="handleEditorChartClick"
              />
            </div>
          </el-main>
        </el-container>
      </el-tab-pane>
    </el-tabs>

    <!-- Dialogs -->
    <el-dialog v-model="newDashboardDialogVisible" title="新建数据看板" width="30%">
      <el-form>
        <el-form-item label="看板名称">
          <el-input v-model="newDashboardName" />
        </el-form-item>
        <el-form-item label="看板描述">
          <el-input v-model="newDashboardDesc" type="textarea" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="newDashboardDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="createDashboard">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="addWidgetDialogVisible" title="添加查询图表到看板" width="40%">
      <el-table :data="savedQueries" border stripe>
        <el-table-column prop="name" label="查询名称" />
        <el-table-column prop="chart_type" label="图表类型" width="120">
          <template #default="scope"><el-tag size="small" type="info">{{ scope.row.chart_type }}</el-tag></template>
        </el-table-column>
        <el-table-column label="操作" width="100" align="center">
          <template #default="scope">
            <el-button type="primary" size="small" @click="addWidgetToDashboard(scope.row)">添加</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <!-- Data Source Dialog -->
    <el-dialog v-model="dsDialogVisible" title="接入新数据源" width="30%">
      <el-form :model="dsForm" label-width="100px">
        <el-form-item label="连接名称"><el-input v-model="dsForm.name" /></el-form-item>
        <el-form-item label="类型"><el-select v-model="dsForm.type" style="width: 100%"><el-option label="ClickHouse" value="clickhouse" /></el-select></el-form-item>
        <el-form-item label="主机"><el-input v-model="dsForm.host" /></el-form-item>
        <el-form-item label="端口"><el-input-number v-model="dsForm.port" :controls="false" style="width: 100%" /></el-form-item>
        <el-form-item label="用户名"><el-input v-model="dsForm.username" /></el-form-item>
        <el-form-item label="密码"><el-input v-model="dsForm.password" type="password" show-password /></el-form-item>
        <el-form-item label="数据库"><el-input v-model="dsForm.database" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dsDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveDataSource" :loading="savingDs">测试并保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="saveQueryDialogVisible" title="保存查询" width="30%">
      <el-form @submit.prevent>
        <el-form-item label="查询名称">
          <el-input v-model="saveQueryName" placeholder="请输入查询名称" />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="saveQueryDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="saveCurrentQuery" :loading="savingQuery">保存</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- Drill-through Detail Dialog -->
    <el-dialog v-model="detailVisible" title="指标底层明细穿透数据" width="85%" destroy-on-close>
      <div class="detail-context">
        <el-tag v-for="(val, key) in currentContext.filters" :key="key" style="margin-right: 10px; margin-bottom: 10px;" type="success">
          {{ key }}: {{ val }}
        </el-tag>
      </div>
      <el-table :data="detailData" border stripe height="400" v-loading="detailLoading">
        <el-table-column v-for="col in detailColumns" :key="col" :prop="col" :label="col" show-overflow-tooltip />
      </el-table>
      <div class="pagination-box">
        <el-pagination background layout="total, prev, pager, next" :total="detailTotal" :page-size="detailPageSize" :current-page="detailPage" @current-change="loadDetailData" />
      </div>
    </el-dialog>
    
    <!-- Threshold Dialog -->
    <el-dialog v-model="thresholdDialogVisible" title="组件高亮阈值配置" width="60%">
      <div style="margin-bottom: 15px;"><el-button type="primary" icon="Plus" @click="addThresholdRule" size="small">新增规则</el-button></div>
      <el-table :data="currentThresholds" border size="small">
        <el-table-column label="目标列" width="180">
          <template #default="scope">
            <el-select v-model="scope.row.column" placeholder="选择列" size="small" allow-create filterable>
              <el-option v-for="col in currentThresholdWidgetCols" :key="col" :label="col" :value="col" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="条件" width="130">
          <template #default="scope">
            <el-select v-model="scope.row.operator" placeholder="条件" size="small">
              <el-option label="大于 (>)" value=">" />
              <el-option label="小于 (<)" value="<" />
              <el-option label="等于 (=)" value="=" />
              <el-option label="大于等于 (>=)" value=">=" />
              <el-option label="小于等于 (<=)" value="<=" />
              <el-option label="介于 (between)" value="between" />
              <el-option label="不介于 (not between)" value="not_between" />
            </el-select>
          </template>
        </el-table-column>
        <el-table-column label="阈值" width="220">
          <template #default="scope">
            <div v-if="scope.row.operator === 'between' || scope.row.operator === 'not_between'" style="display: flex; align-items: center; gap: 5px;">
              <el-input-number v-model="scope.row.value" :controls="false" style="width: 100%" size="small" />
              <span>~</span>
              <el-input-number v-model="scope.row.value_max" :controls="false" style="width: 100%" size="small" />
            </div>
            <el-input-number v-else v-model="scope.row.value" :controls="false" style="width: 100%" size="small" />
          </template>
        </el-table-column>
        <el-table-column label="颜色" width="100">
          <template #default="scope"><el-color-picker v-model="scope.row.color" show-alpha size="small" /></template>
        </el-table-column>
        <el-table-column label="操作" width="80" align="center">
          <template #default="scope"><el-button type="danger" link icon="Delete" @click="removeThresholdRule(scope.$index)"></el-button></template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="thresholdDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveThresholds" :loading="savingThresholds">保存配置</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Edit, Plus, Menu, Check, Close, Filter, DataLine } from '@element-plus/icons-vue'
import { GridLayout, GridItem } from 'vue3-grid-layout'

const API_BASE = 'http://127.0.0.1:8000/api/v1/data'
const META_API_BASE = 'http://127.0.0.1:8000/api/v1/saved-queries'
const DS_API_BASE = 'http://127.0.0.1:8000/api/v1/data-sources'
const DASH_API_BASE = 'http://127.0.0.1:8000/api/v1/dashboards'

const dataSources = ref([])
const dsDialogVisible = ref(false)
const savingDs = ref(false)
const dsForm = ref({ name: '', type: 'clickhouse', host: 'localhost', port: 8123, username: 'default', password: '', database: 'default' })

const activeTab = ref('dashboard')
const savedQueries = ref([])

const dashboards = ref([])
const activeDashboardId = ref(null)
const activeDashboard = ref(null)
const activeDashboardLayout = ref([])
const newDashboardDialogVisible = ref(false)
const newDashboardName = ref('')
const newDashboardDesc = ref('')
const savingLayout = ref(false)
const isDashboardEditMode = ref(false) // 看板编辑模式状态
const editingBoardName = ref(false)
const tempBoardName = ref('')
const originalLayoutStr = ref('') // 保存编辑前的快照

const addWidgetDialogVisible = ref(false)
const widgetData = ref({}) 
const widgetLoading = ref({})

const currentDataSourceId = ref(null)
const tables = ref([])
const tablesLoading = ref(false)
const editorSql = ref('SELECT o.country, sum(o.revenue) as total_rev \nFROM bi_demo.orders o \nGROUP BY o.country')
const editorLoading = ref(false)
const editorTableData = ref([])
const editorColumns = ref([])
const editorMetricColumns = ref(new Set())
const editorChartType = ref('table')

const saveQueryDialogVisible = ref(false)
const saveQueryName = ref('')
const savingQuery = ref(false)

const detailVisible = ref(false)
const detailLoading = ref(false)
const detailData = ref([])
const detailColumns = ref([])
const detailTotal = ref(0)
const detailPage = ref(1)
const detailPageSize = ref(10)
const currentContext = ref({ filters: {}, metric: '', sourceSql: '', dataSourceId: null })

const thresholdDialogVisible = ref(false)
const currentThresholds = ref([])
const currentThresholdWidgetId = ref(null)
const currentThresholdWidgetCols = ref([])
const savingThresholds = ref(false)
const editorThresholds = ref([]) // 用于工作台的默认阈值状态
const isEditorThresholdMode = ref(false)

// --- Parsing & ECharts Logic ---
const splitSelectClause = (clause) => {
  const parts = []
  let current = ''; let parenDepth = 0
  for (let i = 0; i < clause.length; i++) {
    const char = clause[i]
    if (char === '(') parenDepth++
    else if (char === ')') parenDepth--
    else if (char === ',' && parenDepth === 0) { parts.push(current.trim()); current = ''; continue }
    current += char
  }
  if (current) parts.push(current.trim())
  return parts
}

const parseMetrics = (sql, columns) => {
  const metricCols = new Set()
  const sqlMatch = sql.match(/SELECT\s+([\s\S]+?)\s+FROM/i)
  const selectClause = sqlMatch ? sqlMatch[1] : ''
  const expressions = splitSelectClause(selectClause)
  
  columns.forEach(col => {
    if (/^(count|sum|avg|max|min)\b/i.test(col)) { metricCols.add(col); return }
    if (selectClause) {
      const escapedCol = col.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
      const regex = new RegExp(`\\b(count|sum|avg|max|min)\\b\\s*\\([\\s\\S]*\\)\\s+(?:AS\\s+)?[\`"']?${escapedCol}[\`"']?$`, 'i')
      for (const expr of expressions) {
        if (regex.test(expr)) { metricCols.add(col); break }
      }
    }
  })
  return metricCols
}

// Generate ECharts Option dynamically based on columns
// Assuming: 1st column is dimension (X axis/Pie name), rest are metrics (Series)
const buildChartOption = (type, columns, data) => {
  if (columns.length < 2 || data.length === 0) return {}
  const dimCol = columns[0]
  const metricCols = columns.slice(1)
  
  if (type === 'pie') {
    // Pie usually takes only the first metric
    const metricCol = metricCols[0]
    return {
      tooltip: { trigger: 'item' },
      legend: { orient: 'vertical', left: 'left' },
      series: [
        {
          name: metricCol,
          type: 'pie',
          radius: '50%',
          data: data.map(row => ({ name: row[dimCol], value: row[metricCol] })),
          emphasis: { itemStyle: { shadowBlur: 10, shadowOffsetX: 0, shadowColor: 'rgba(0, 0, 0, 0.5)' } }
        }
      ]
    }
  } else {
    // Bar or Line
    return {
      tooltip: { trigger: 'axis' },
      legend: { data: metricCols },
      xAxis: { type: 'category', data: data.map(row => row[dimCol]) },
      yAxis: { type: 'value' },
      series: metricCols.map(col => ({
        name: col,
        type: type,
        data: data.map(row => row[col])
      }))
    }
  }
}

const getEditorChartOption = () => {
  return buildChartOption(editorChartType.value, editorColumns.value, editorTableData.value)
}

const getChartOption = (widget) => {
  const wd = widgetData.value[widget.i]
  if (!wd || !wd.columns) return {}
  return buildChartOption(widget.chart_type, wd.columns, wd.data)
}

// Drill down via ECharts click
const handleEditorChartClick = (params) => {
  const dimCol = editorColumns.value[0]
  const rowData = editorTableData.value[params.dataIndex]
  const metricCol = params.seriesName // The clicked metric name
  handleCellClick(rowData, { property: metricCol }, editorSql.value, editorMetricColumns.value, currentDataSourceId.value)
}

const handleChartClick = (params, widget) => {
  const wd = widgetData.value[widget.i]
  const dimCol = wd.columns[0]
  const rowData = wd.data[params.dataIndex]
  const metricCol = params.seriesName
  handleCellClick(rowData, { property: metricCol }, widget.query_sql, wd.metrics, widget.data_source_id)
}

// --- Data Sources ---
const fetchDataSources = async () => {
  try {
    const res = await axios.get(DS_API_BASE + '/')
    dataSources.value = res.data
    if (dataSources.value.length > 0 && !currentDataSourceId.value) {
      currentDataSourceId.value = dataSources.value[0].id
      loadTables()
    }
  } catch (error) {}
}
const showDsDialog = () => { dsDialogVisible.value = true }
const saveDataSource = async () => {
  savingDs.value = true
  try { await axios.post(DS_API_BASE + '/', dsForm.value); ElMessage.success('成功'); dsDialogVisible.value = false; fetchDataSources() } 
  catch (e) { ElMessage.error('失败') } finally { savingDs.value = false }
}
const deleteDataSource = (id) => {
  ElMessageBox.confirm('确定?', '提示', { type: 'warning' }).then(async () => {
    await axios.delete(`${DS_API_BASE}/${id}`); fetchDataSources()
  }).catch(()=>{})
}

// --- Queries (Workspace) ---
const fetchSavedQueries = async () => {
  try {
    const res = await axios.get(META_API_BASE + '/')
    savedQueries.value = res.data
  } catch (error) {}
}
const loadTables = async () => {
  if (!currentDataSourceId.value) return
  tablesLoading.value = true
  try {
    const res = await axios.get(`${API_BASE}/meta/tables`, { headers: { 'x-data-source-id': currentDataSourceId.value } })
    tables.value = res.data.tables
  } catch (error) { tables.value = [] } finally { tablesLoading.value = false }
}
const handleTableSelect = (tableName) => { editorSql.value = `SELECT * FROM ${tableName} LIMIT 10` }

const runEditorQuery = async () => {
  if (!editorSql.value.trim()) return
  editorLoading.value = true
  try {
    const headers = currentDataSourceId.value ? { 'x-data-source-id': currentDataSourceId.value } : {}
    const res = await axios.post(`${API_BASE}/query/raw`, { sql: editorSql.value }, { headers })
    editorColumns.value = res.data.columns
    editorTableData.value = res.data.data
    editorMetricColumns.value = parseMetrics(editorSql.value, res.data.columns)
  } catch (e) { ElMessage.error('查询失败') } finally { editorLoading.value = false }
}

const showSaveQueryDialog = () => { saveQueryName.value = ''; saveQueryDialogVisible.value = true }
const saveCurrentQuery = async () => {
  if (!saveQueryName.value.trim()) {
    ElMessage.warning('请输入名称')
    return
  }
  savingQuery.value = true
  try {
    await axios.post(META_API_BASE + '/', { 
      name: saveQueryName.value, 
      raw_sql: editorSql.value, 
      data_source_id: currentDataSourceId.value,
      chart_type: editorChartType.value,
      thresholds: editorThresholds.value
    })
    ElMessage.success('保存成功')
    saveQueryDialogVisible.value = false
    fetchSavedQueries()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally { 
    savingQuery.value = false 
  }
}
const deleteSavedQuery = async (id) => {
  await axios.delete(`${META_API_BASE}/${id}`); fetchSavedQueries()
}
const loadQueryToEditor = (q) => {
  editorSql.value = q.raw_sql; currentDataSourceId.value = q.data_source_id; editorChartType.value = q.chart_type || 'table'
  editorThresholds.value = Array.isArray(q.thresholds) ? JSON.parse(JSON.stringify(q.thresholds)) : []
  runEditorQuery()
}

// --- Dashboards ---
const fetchDashboards = async () => {
  try {
    const res = await axios.get(DASH_API_BASE + '/')
    dashboards.value = res.data
  } catch (e) {}
}
const showNewDashboardDialog = () => { newDashboardName.value = ''; newDashboardDesc.value = ''; newDashboardDialogVisible.value = true }
const createDashboard = async () => {
  try {
    const res = await axios.post(DASH_API_BASE + '/', { name: newDashboardName.value, description: newDashboardDesc.value })
    newDashboardDialogVisible.value = false; await fetchDashboards(); loadDashboard(res.data)
  } catch (e) {}
}
const deleteDashboard = async (id) => {
  ElMessageBox.confirm('删除?', '警告', {type:'warning'}).then(async () => {
    await axios.delete(`${DASH_API_BASE}/${id}`); if(activeDashboardId.value===id) activeDashboard.value=null; fetchDashboards()
  }).catch(()=>{})
}

const loadDashboard = async (db) => {
  activeDashboardId.value = db.id
  activeDashboard.value = db
  activeDashboardLayout.value = db.widgets || []
  isDashboardEditMode.value = false // 加载看板时默认阅读模式
  editingBoardName.value = false
  
  activeDashboardLayout.value.forEach(w => { fetchWidgetData(w) })
}

const fetchWidgetData = async (widget) => {
  widgetLoading.value[widget.i] = true
  try {
    const headers = widget.data_source_id ? { 'x-data-source-id': widget.data_source_id } : {}
    const res = await axios.post(`${API_BASE}/query/raw`, { sql: widget.query_sql }, { headers })
    widgetData.value[widget.i] = {
      columns: res.data.columns,
      data: res.data.data,
      metrics: parseMetrics(widget.query_sql, res.data.columns)
    }
  } catch (e) {
    widgetData.value[widget.i] = { error: '加载失败' }
  } finally {
    widgetLoading.value[widget.i] = false
  }
}

const showAddWidgetDialog = () => { addWidgetDialogVisible.value = true }
const addWidgetToDashboard = (query) => {
  const newI = Date.now().toString()
  const newWidget = {
    i: newI, x: 0, y: 0, w: 6, h: 8,
    query_id: query.id, query_name: query.name, query_sql: query.raw_sql, query_thresholds: query.thresholds, 
    data_source_id: query.data_source_id, chart_type: query.chart_type || 'table'
  }
  activeDashboardLayout.value.push(newWidget)
  addWidgetDialogVisible.value = false
  fetchWidgetData(newWidget)
}
const removeWidget = (i) => {
  activeDashboardLayout.value = activeDashboardLayout.value.filter(w => w.i !== i)
}
const saveDashboardLayout = async () => {
  savingLayout.value = true
  try {
    await axios.put(`${DASH_API_BASE}/${activeDashboardId.value}`, {
      widgets: activeDashboardLayout.value.map(w => ({ query_id: w.query_id, x: w.x, y: w.y, w: w.w, h: w.h, i: w.i }))
    })
    ElMessage.success('布局已保存')
    isDashboardEditMode.value = false // 保存后退出编辑模式
  } catch (e) { ElMessage.error('保存失败') } finally { savingLayout.value = false }
}

const cancelDashboardEdit = () => {
  isDashboardEditMode.value = false
  // 这里可以考虑恢复 originalLayoutStr, 暂略复杂回滚，直接重新加载
  fetchDashboards()
  const db = dashboards.value.find(d => d.id === activeDashboardId.value)
  if (db) {
    activeDashboardLayout.value = db.widgets || []
  }
}

const startEditBoardName = () => {
  tempBoardName.value = activeDashboard.value.name
  editingBoardName.value = true
}

const saveBoardName = async () => {
  if (!tempBoardName.value.trim() || tempBoardName.value === activeDashboard.value.name) {
    editingBoardName.value = false
    return
  }
  try {
    await axios.put(`${DASH_API_BASE}/${activeDashboardId.value}`, {
      name: tempBoardName.value.trim()
    })
    activeDashboard.value.name = tempBoardName.value.trim()
    ElMessage.success('看板重命名成功')
    fetchDashboards()
  } catch (e) {
    ElMessage.error('重命名失败')
  } finally {
    editingBoardName.value = false
  }
}

// --- Thresholds ---
const openWidgetThresholds = (widget) => {
  isEditorThresholdMode.value = false
  currentThresholdWidgetId.value = widget.query_id
  currentThresholds.value = Array.isArray(widget.query_thresholds) ? JSON.parse(JSON.stringify(widget.query_thresholds)) : []
  currentThresholdWidgetCols.value = widgetData.value[widget.i]?.columns || []
  thresholdDialogVisible.value = true
}
const openEditorThresholds = () => {
  if (editorColumns.value.length === 0) {
    ElMessage.warning('请先执行查询获取结果列'); return
  }
  isEditorThresholdMode.value = true
  currentThresholds.value = JSON.parse(JSON.stringify(editorThresholds.value))
  currentThresholdWidgetCols.value = editorColumns.value
  thresholdDialogVisible.value = true
}

const addThresholdRule = () => { currentThresholds.value.push({ column: '', operator: '>', value: 0, value_max: 0, color: 'rgba(245, 108, 108, 0.2)' }) }
const removeThresholdRule = (idx) => { currentThresholds.value.splice(idx, 1) }

const saveThresholds = async () => {
  if (isEditorThresholdMode.value) {
    editorThresholds.value = JSON.parse(JSON.stringify(currentThresholds.value))
    thresholdDialogVisible.value = false
    ElMessage.success('默认预警配置已暂存，随查询保存时生效')
    return
  }

  savingThresholds.value = true
  try {
    const res = await axios.put(`${META_API_BASE}/${currentThresholdWidgetId.value}`, { thresholds: currentThresholds.value })
    activeDashboardLayout.value.forEach(w => {
      if (w.query_id === currentThresholdWidgetId.value) w.query_thresholds = res.data.thresholds
    })
    thresholdDialogVisible.value = false
  } catch (e) {} finally { savingThresholds.value = false }
}

const getWidgetCellStyle = ({ row, column }, thresholds) => {
  if (!thresholds || thresholds.length === 0) return {}
  const colName = column.property
  for (const rule of thresholds) {
    if (rule.column === colName) {
      const cellValue = Number(row[colName])
      if (isNaN(cellValue)) continue
      const ruleValue = Number(rule.value)
      const ruleValueMax = Number(rule.value_max)
      let match = false
      switch (rule.operator) {
        case '>': match = cellValue > ruleValue; break;
        case '<': match = cellValue < ruleValue; break;
        case '=': match = cellValue === ruleValue; break;
        case '>=': match = cellValue >= ruleValue; break;
        case '<=': match = cellValue <= ruleValue; break;
        case 'between': match = cellValue >= ruleValue && cellValue <= ruleValueMax; break;
        case 'not_between': match = cellValue < ruleValue || cellValue > ruleValueMax; break;
      }
      if (match) {
        // Calculate relative luminance to determine text color
        let textColor = '#303133' // default dark text
        if (rule.color && rule.color.startsWith('rgba')) {
           // Extremely simple heuristic: if it's a solid, non-transparent dark color, use white text. 
           // Usually users pick light transparent colors (alpha < 0.5) so dark text is fine.
           const parts = rule.color.match(/[\d.]+/g)
           if (parts && parts.length === 4) {
             const alpha = parseFloat(parts[3])
             if (alpha > 0.6) textColor = '#ffffff'
           }
        }
        return { backgroundColor: rule.color, color: textColor }
      }
    }
  }
  return {}
}

// --- Drill Through ---
const handleCellClick = (row, column, sourceSql, metricCols, dsId) => {
  const colName = column.property
  if (!metricCols.has(colName)) return
  const filtersMap = {}
  for (const key in row) {
    if (!metricCols.has(key) && row[key] !== null) filtersMap[key] = row[key]
  }
  currentContext.value = { filters: filtersMap, metric: colName, sourceSql, dataSourceId: dsId }
  detailPage.value = 1; detailVisible.value = true; loadDetailData()
}

const loadDetailData = async (colOrPage = 1) => {
  if (typeof colOrPage === 'number') detailPage.value = colOrPage
  detailLoading.value = true
  try {
    const headers = currentContext.value.dataSourceId ? { 'x-data-source-id': currentContext.value.dataSourceId } : {}
    const res = await axios.post(`${API_BASE}/drill-through`, {
      raw_sql: currentContext.value.sourceSql, filters: currentContext.value.filters,
      clicked_metric: currentContext.value.metric, limit: detailPageSize.value, offset: (detailPage.value - 1) * detailPageSize.value
    }, { headers })
    detailTotal.value = res.data.total; detailColumns.value = res.data.columns; detailData.value = res.data.data
  } catch (e) { ElMessage.error('明细加载失败') } finally { detailLoading.value = false }
}

onMounted(() => {
  fetchDataSources()
  fetchSavedQueries()
  fetchDashboards()
  runEditorQuery()
})
</script>

<style scoped>
.app-container { padding: 20px; height: 100vh; display: flex; flex-direction: column; box-sizing: border-box; }
.main-header { margin-bottom: 20px; padding-left: 10px; flex-shrink: 0; }
.main-header h2 { margin: 0 0 10px 0; color: #303133; }
.subtitle { color: #606266; font-size: 14px; margin: 0; }
.main-tabs { flex: 1; display: flex; flex-direction: row; }
:deep(.el-tabs__item) { text-align: left !important; justify-content: flex-start !important; padding-left: 20px !important; }
:deep(.el-tabs__content) { flex: 1; padding: 0 !important; overflow: hidden; }
:deep(.el-tab-pane) { height: 100%; display: flex; flex-direction: column; }
.ds-container { padding: 20px; height: 100%; overflow: auto; box-sizing: border-box; }
.dashboard-container, .editor-main-container { flex: 1; height: 100%; }
.saved-queries-aside, .editor-aside { border-right: 1px solid #dcdfe6; background: #fff; display: flex; flex-direction: column; }
.aside-header { padding: 15px 20px; border-bottom: 1px solid #ebeef5; background-color: #f8f9fa; display: flex; justify-content: space-between; align-items: center;}
.aside-header h3 { margin: 0; color: #303133; font-size: 16px; }
.saved-queries-menu { border-right: none; flex: 1; overflow-y: auto; }
.table-tree-menu { border-right: none; flex: 1; overflow-y: auto; }
.menu-item-content { display: flex; justify-content: space-between; align-items: center; width: 100%; }
.query-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 150px; }
.empty-text { text-align: center; color: #909399; padding: 30px 0; font-size: 14px; }
.dashboard-main { padding: 0; position: relative; display: flex; flex-direction: column; overflow: hidden; }
.board-view { padding: 20px; height: 100%; display: flex; flex-direction: column; box-sizing: border-box; }
.board-title-section { margin-bottom: 20px; display: flex; justify-content: space-between; align-items: flex-start; border-bottom: 2px solid #ebeef5; padding-bottom: 10px; flex-shrink: 0; }
.board-title-section h2 { margin: 0; color: #303133; }
.widget-card { background: #fff; border-radius: 4px; box-shadow: 0 2px 12px 0 rgba(0,0,0,.1); }
.widget-header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #f0f0f0; padding-bottom: 8px; }
.widget-title { font-weight: bold; color: #333; font-size: 14px; }
.empty-board { margin-top: 100px; }
.editor-container { padding: 10px; display: flex; flex-direction: column; height: 100%; box-sizing: border-box; overflow: hidden; }
.query-box { background-color: #f8f9fa; padding: 20px; border-radius: 8px; margin-bottom: 15px; border: 1px solid #ebeef5; flex-shrink: 0; }
.sql-input { font-family: 'Courier New', Courier, monospace; }
.action-bar { margin-top: 15px; display: flex; gap: 10px; }
.result-box { flex: 1; overflow: hidden; display: flex; flex-direction: column; }
.clickable-metric { color: #409EFF; font-weight: bold; cursor: pointer; text-decoration: underline; transition: all 0.2s; }
.clickable-metric:hover { color: #66b1ff; }
.detail-context { margin-bottom: 15px; background-color: #f4f4f5; padding: 10px; border-radius: 4px; }
.pagination-box { margin-top: 20px; display: flex; justify-content: flex-end; }
/* vue-grid-layout styles are handled by the component */
.vue-grid-item:not(.vue-grid-placeholder) { background: transparent; }
.vue-grid-layout { flex: 1; overflow-y: auto; overflow-x: hidden; }

/* Edit mode specific styles */
.grid-edit-mode {
  background-image: linear-gradient(#e5e5e5 1px, transparent 1px), linear-gradient(90deg, #e5e5e5 1px, transparent 1px);
  background-size: 20px 20px;
}
.widget-edit-mode {
  border: 1px dashed #409EFF;
}
</style>
