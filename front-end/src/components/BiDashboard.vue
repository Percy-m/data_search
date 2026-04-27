<template>
  <div class="app-container">
    <div class="main-header">
      <h2 class="title">统一数据分析控制台</h2>
      <span class="subtitle">支持多数据源直连、拖拽看板、可视化智能下钻</span>
    </div>

    <el-tabs v-model="activeTab" class="main-tabs" type="border-card" tab-position="left">
      <!-- Tab 1: 组合看板 (Dashboards) -->
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
                  <el-popconfirm title="确定要删除这个看板吗？" @confirm="deleteDashboard(db.id)" width="200" confirm-button-text="删除" confirm-button-type="danger" cancel-button-text="取消">
                    <template #reference>
                      <el-button type="danger" link icon="Delete" @click.stop title="删除看板"></el-button>
                    </template>
                  </el-popconfirm>
                </div>
              </el-menu-item>
              <div v-if="dashboards.length === 0" class="empty-text">暂无看板，请先创建</div>
            </el-menu>
          </el-aside>

          <!-- 右侧：看板画布 -->
          <el-main class="dashboard-main" style="background-color: #f0f2f5;">
            
            <div class="global-macros-bar" v-if="activeDashboard && globalDashboardMacros.length > 0">
              <span style="font-weight: bold; margin-right: 15px; font-size: 14px; color: #606266;">全局参数 (Macros)</span>
              <div v-for="(macro, idx) in globalDashboardMacros" :key="idx" class="macro-item">
                <span style="margin-right: 5px; font-size: 14px; font-family: monospace;">{{ macro.key }}</span>
                <span style="margin: 0 5px;">=</span>
                <el-input v-model="macro.value" placeholder="Value (如 3_1)" size="small" style="width: 150px;" @change="refreshActiveDashboard" />
              </div>
            </div>
            
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
                  @dragEvent="(eventName) => handleWidgetInteract(eventName, item.i)"
                  @resizeEvent="(eventName) => handleWidgetInteract(eventName, item.i)"
                >
                  <el-card shadow="hover" style="height: 100%; display: flex; flex-direction: column;" :body-style="{ padding: '10px', flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }">
                    <div class="widget-header">
                      <span class="widget-title">{{ item.query_name }}</span>
                      <div>
                        <!-- Always show download button -->
                        <el-button type="success" link icon="Download" @click="exportWidgetToExcel(item)" title="导出 Excel (保留样式)"></el-button>
                        <span v-show="isDashboardEditMode">
                          <el-button type="warning" link icon="Filter" @click="openWidgetThresholds(item)" title="独立配置预警"></el-button>
                          <el-button type="danger" link icon="Close" @click="removeWidget(item.i)" title="移除"></el-button>
                        </span>
                      </div>
                    </div>
                    
                    <div class="widget-content" style="flex: 1; overflow: auto; margin-top: 10px;" v-loading="widgetLoading[item.i]">
                      
                      <!-- 动态骨架屏：仅在组件被物理拖拽/缩放的那一瞬间显示以保证极简DOM树 -->
                      <div v-if="interactingWidgets.has(item.i)" style="width: 100%; height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; background-color: rgba(245, 247, 250, 0.8); border: 2px dashed #409EFF; border-radius: 4px;">
                        <el-icon size="30" color="#409EFF"><Menu /></el-icon>
                        <span style="margin-top: 10px; color: #409EFF; font-size: 14px; font-weight: bold;">正在调整位置/大小...</span>
                      </div>

                      <!-- 真实图表：只要静止下来，永远显示真实数据，以便实时配置阈值观察效果 -->
                      <div v-else v-memo="[widgetData[item.i], widgetLoading[item.i], item.chart_type, item.query_thresholds]" style="width: 100%; height: 100%">
                        <!-- Table View -->
                        <el-table 
                          v-if="widgetData[item.i] && (!item.chart_type || item.chart_type === 'table')"
                          :data="widgetData[item.i].data" 
                          border 
                          size="small"
                          style="width: 100%; height: 100%"
                          :cell-style="(ctx) => getWidgetCellStyle(ctx, item.query_thresholds)"
                          @cell-click="(row, col, cell, evt) => handleCellClick(row, col, item.query_sql, widgetData[item.i].metrics, item.data_source_id, getWidgetMacrosDict(item))"
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
                <span :title="q.name" style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap; flex: 1;">{{ q.name }}</span>
                <el-popconfirm title="确定要删除这个查询吗？" @confirm="deleteSavedQuery(q.id)" width="200" confirm-button-text="删除" confirm-button-type="danger" cancel-button-text="取消">
                  <template #reference>
                    <el-button type="danger" link icon="Delete" style="margin-left: 5px;" @click.stop></el-button>
                  </template>
                </el-popconfirm>
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
            <div class="global-macros-bar" style="border-bottom: 1px solid #ebeef5; border-radius: 0;">
              <span style="font-weight: bold; margin-right: 15px; font-size: 14px; color: #606266;">当前查询变量 (Macros)</span>
              <div v-for="(macro, idx) in editorMacros" :key="idx" class="macro-item">
                <el-input v-model="macro.key" placeholder="Key (如 version)" size="small" style="width: 120px;" />
                <span style="margin: 0 5px;">=</span>
                <el-input v-model="macro.value" placeholder="Value (如 3_1)" size="small" style="width: 150px;" />
                <el-button type="danger" link icon="Close" @click="removeEditorMacro(idx)"></el-button>
              </div>
              <el-button type="primary" link icon="Plus" size="small" @click="addEditorMacro" style="margin-left: 10px;">添加参数</el-button>
            </div>
            
            <div class="query-box">
              <el-input
                v-model="editorSql"
                type="textarea"
                :rows="8"
                placeholder="请输入 SQL 语句..."
                class="sql-input"
              />
              <div class="action-bar">
                <div class="left-actions">
                  <el-button type="primary" size="large" @click="runEditorQuery" :loading="editorLoading">
                    执行查询
                  </el-button>
                  <template v-if="!currentEditorQueryId">
                    <el-button @click="showSaveQueryDialog" size="large" type="success" plain>保存查询</el-button>
                  </template>
                  <template v-else>
                    <el-button @click="updateCurrentQuery" size="large" type="primary" plain :loading="savingQuery">更新当前查询</el-button>
                    <el-button @click="showSaveQueryDialog" size="large" type="success" plain>另存为新查询</el-button>
                  </template>
                  <el-button @click="resetEditor" size="large">重置</el-button>
                </div>
                <div class="right-actions">
                  <el-button type="success" plain icon="Download" size="large" @click="exportEditorToExcel" title="导出查询结果">导出</el-button>
                  <el-button type="warning" plain icon="Filter" size="large" @click="openEditorThresholds" title="配置默认预警染色">预警配置</el-button>
                  <span style="font-size: 14px; color: #606266; margin-left: 5px;">预览：</span>
                  <el-select v-model="editorChartType" style="width: 120px" size="large">
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
                @cell-click="(row, col, cell, evt) => handleCellClick(row, col, editorSql, editorMetricColumns, currentDataSourceId, getEditorMacrosDict())"
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
      <!-- Tab 3: 配置中心 (Data Sources) - Moved to bottom -->
      <el-tab-pane label="配置中心 (Data Sources)" name="datasource">
        <div class="ds-container">
          <div style="margin-bottom: 15px; display: flex; justify-content: space-between;">
            <h3>已接入的数据源</h3>
            <el-button type="primary" icon="Plus" @click="showDsDialog">新增数据源</el-button>
          </div>
          <el-table :data="dataSources" border stripe>
            <el-table-column prop="name" label="连接名称" />
            <el-table-column prop="type" label="类型" width="120">
              <template #default="scope">
                <el-tag size="small">{{ scope.row.type }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="host" label="主机地址" />
            <el-table-column prop="database" label="数据库" />
            <el-table-column label="操作" width="120" align="center">
              <template #default="scope">
                <el-button type="primary" link icon="Edit" @click="editDataSource(scope.row)" title="编辑"></el-button>
                <el-popconfirm title="确定要删除该数据源吗？" @confirm="deleteDataSource(scope.row.id)" confirm-button-text="删除" confirm-button-type="danger" cancel-button-text="取消">
                  <template #reference>
                    <el-button type="danger" link icon="Delete" title="删除"></el-button>
                  </template>
                </el-popconfirm>
              </template>
            </el-table-column>
          </el-table>
        </div>
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
    <el-dialog v-model="dsDialogVisible" :title="currentEditDsId ? '编辑数据源' : '接入新数据源'" width="30%">
      <el-form :model="dsForm" label-width="100px">
        <el-form-item label="连接名称"><el-input v-model="dsForm.name" /></el-form-item>
        <el-form-item label="类型">
          <el-select v-model="dsForm.type" style="width: 100%">
            <el-option label="ClickHouse" value="clickhouse" />
            <el-option label="DuckDB" value="duckdb" />
          </el-select>
        </el-form-item>
        <el-form-item label="主机"><el-input v-model="dsForm.host" :disabled="dsForm.type === 'duckdb'" /></el-form-item>
        <el-form-item label="端口"><el-input-number v-model="dsForm.port" :controls="false" style="width: 100%" :disabled="dsForm.type === 'duckdb'" /></el-form-item>
        <el-form-item label="用户名"><el-input v-model="dsForm.username" :disabled="dsForm.type === 'duckdb'" /></el-form-item>
        <el-form-item label="密码">
          <el-input v-model="dsForm.password" type="password" show-password :placeholder="currentEditDsId ? '不修改请留空' : '请输入密码'" :disabled="dsForm.type === 'duckdb'" />
        </el-form-item>
        <el-form-item label="数据库(路径)">
          <el-input v-model="dsForm.database" :placeholder="dsForm.type === 'duckdb' ? 'DuckDB 文件路径，留空为内存模式' : ''" />
        </el-form-item>
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
      <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom: 15px;">
        <div class="detail-context" style="margin-bottom: 0;">
          <el-tag v-for="(val, key) in currentContext.filters" :key="key" style="margin-right: 10px;" type="success">
            {{ key }}: {{ val }}
          </el-tag>
        </div>
        <el-button type="success" icon="Download" @click="exportDetailToExcel" :loading="exportingDetail">导出全部明细</el-button>
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
import { ref, shallowRef, shallowReactive, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Delete, Edit, Plus, Menu, Check, Close, Filter, DataLine, Download } from '@element-plus/icons-vue'
import { GridLayout, GridItem } from 'vue3-grid-layout'
import ExcelJS from 'exceljs'
import { saveAs } from 'file-saver'

const API_BASE = 'http://127.0.0.1:8000/api/v1/data'
const META_API_BASE = 'http://127.0.0.1:8000/api/v1/saved-queries'
const DS_API_BASE = 'http://127.0.0.1:8000/api/v1/data-sources'
const DASH_API_BASE = 'http://127.0.0.1:8000/api/v1/dashboards'

const dataSources = ref([])
const dsDialogVisible = ref(false)
const savingDs = ref(false)
const currentEditDsId = ref(null)
const dsForm = ref({ name: '', type: 'clickhouse', host: 'localhost', port: 8123, username: 'default', password: '', database: 'default' })

const activeTab = ref('dashboard')
const savedQueries = ref([])
const globalDashboardMacros = ref([]) // 看板全局宏变量配置，自动提取自组件
const editorMacros = ref([{ key: 'version', value: 's' }]) // 编辑器局部宏变量配置

const dashboards = ref([])
const activeDashboardId = ref(null)
const activeDashboard = ref(null)
const activeDashboardLayout = ref([])
const newDashboardDialogVisible = ref(false)
const newDashboardName = ref('')
const newDashboardDesc = ref('')
const savingLayout = ref(false)
const isDashboardEditMode = ref(false) // 看板编辑模式状态
const interactingWidgets = ref(new Set()) // 正在被拖拽或缩放的组件的 i 集合
const editingBoardName = ref(false)
const tempBoardName = ref('')
const originalLayoutStr = ref('') // 保存编辑前的快照

const addWidgetDialogVisible = ref(false)
const widgetData = shallowReactive({}) 
const widgetLoading = ref({})

const currentDataSourceId = ref(null)
const tables = ref([])
const tablesLoading = ref(false)
const currentEditorQueryId = ref(null) // 记录当前正在编辑的已存查询的 ID
const editorSql = ref('SELECT o.country, sum(o.revenue) as total_rev \nFROM bi_demo.orders o \nGROUP BY o.country')
const editorLoading = ref(false)
const editorTableData = shallowRef([])
const editorColumns = ref([])
const editorMetricColumns = ref(new Set())
const editorChartType = ref('table')

const saveQueryDialogVisible = ref(false)
const saveQueryName = ref('')
const savingQuery = ref(false)

const detailVisible = ref(false)
const detailLoading = ref(false)
const exportingDetail = ref(false)
const detailData = shallowRef([])
const detailColumns = ref([])
const detailTotal = ref(0)
const detailPage = ref(1)
const detailPageSize = ref(10)
const currentContext = ref({ filters: {}, metric: '', sourceSql: '', dataSourceId: null, macros: {} })

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
  const wd = widgetData[widget.i]
  if (!wd || !wd.columns) return {}
  return buildChartOption(widget.chart_type, wd.columns, wd.data)
}

// Drill down via ECharts click
const handleEditorChartClick = (params) => {
  const dimCol = editorColumns.value[0]
  const rowData = editorTableData.value[params.dataIndex]
  const metricCol = params.seriesName // The clicked metric name
  handleCellClick(rowData, { property: metricCol }, editorSql.value, editorMetricColumns.value, currentDataSourceId.value, getEditorMacrosDict())
}

const handleChartClick = (params, widget) => {
  const wd = widgetData[widget.i]
  const dimCol = wd.columns[0]
  const rowData = wd.data[params.dataIndex]
  const metricCol = params.seriesName
  handleCellClick(rowData, { property: metricCol }, widget.query_sql, wd.metrics, widget.data_source_id, getWidgetMacrosDict(widget))
}

const handleWidgetInteract = (eventName, i) => {
  // eventName is passed as string by vue3-grid-layout: 'dragstart', 'drag', 'dragend', 'resizestart', 'resize', 'resizeend'
  if (eventName === 'dragstart' || eventName === 'resizestart') {
    interactingWidgets.value.add(i)
  } else if (eventName === 'dragend' || eventName === 'resizeend') {
    interactingWidgets.value.delete(i)
  }
}

// === Macros Logic ===
const addEditorMacro = () => { editorMacros.value.push({ key: '', value: '' }) }
const removeEditorMacro = (idx) => { editorMacros.value.splice(idx, 1) }

const getEditorMacrosDict = () => {
  const dict = {}
  editorMacros.value.forEach(m => {
    if (m.key.trim()) dict[m.key.trim()] = m.value.trim()
  })
  return dict
}

const getWidgetMacrosDict = (widget) => {
  const dict = {}
  if (widget.query_macros && Array.isArray(widget.query_macros)) {
    widget.query_macros.forEach(m => {
      if (m.key.trim()) dict[m.key.trim()] = m.value.trim()
    })
  }
  globalDashboardMacros.value.forEach(m => {
    if (m.key.trim()) dict[m.key.trim()] = m.value.trim()
  })
  return dict
}

const computeDashboardGlobalMacros = () => {
  const map = new Map()
  globalDashboardMacros.value.forEach(m => {
    map.set(m.key, m.value)
  })
  
  const extractedKeys = new Set()
  activeDashboardLayout.value.forEach(w => {
    if (w.query_macros && Array.isArray(w.query_macros)) {
      w.query_macros.forEach(m => {
        extractedKeys.add(m.key)
        if (!map.has(m.key)) {
           map.set(m.key, m.value)
        }
      })
    }
  })
  
  const newGlobalMacros = []
  extractedKeys.forEach(k => {
    newGlobalMacros.push({ key: k, value: map.get(k) || '' })
  })
  globalDashboardMacros.value = newGlobalMacros
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
const showDsDialog = () => { 
  currentEditDsId.value = null
  dsForm.value = { name: '', type: 'clickhouse', host: 'localhost', port: 8123, username: 'default', password: '', database: 'default' }
  dsDialogVisible.value = true 
}
const editDataSource = (row) => {
  currentEditDsId.value = row.id
  dsForm.value = { 
    name: row.name, type: row.type, host: row.host, 
    port: row.port, username: row.username || '', 
    password: '', database: row.database || '' 
  }
  dsDialogVisible.value = true
}
const saveDataSource = async () => {
  savingDs.value = true
  try { 
    if (currentEditDsId.value) {
      await axios.put(`${DS_API_BASE}/${currentEditDsId.value}`, dsForm.value)
    } else {
      await axios.post(DS_API_BASE + '/', dsForm.value)
    }
    ElMessage.success('成功')
    dsDialogVisible.value = false
    fetchDataSources() 
  } 
  catch (e) { ElMessage.error(e.response?.data?.detail || '失败') } finally { savingDs.value = false }
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
    const res = await axios.post(`${API_BASE}/query/raw`, { 
      sql: editorSql.value,
      macros: getEditorMacrosDict()
    }, { headers })
    editorColumns.value = res.data.columns
    editorTableData.value = res.data.data
    editorMetricColumns.value = parseMetrics(editorSql.value, res.data.columns)
  } catch (e) { ElMessage.error('查询失败: ' + e.message) } finally { editorLoading.value = false }
}

const showSaveQueryDialog = () => { saveQueryName.value = ''; saveQueryDialogVisible.value = true }
const saveCurrentQuery = async () => {
  if (!saveQueryName.value.trim()) {
    ElMessage.warning('请输入名称')
    return
  }
  savingQuery.value = true
  try {
    const res = await axios.post(META_API_BASE + '/', { 
      name: saveQueryName.value, 
      raw_sql: editorSql.value, 
      data_source_id: currentDataSourceId.value,
      chart_type: editorChartType.value,
      macros: editorMacros.value,
      thresholds: editorThresholds.value
    })
    ElMessage.success('保存成功')
    currentEditorQueryId.value = res.data.id // 保存成功后，自动进入更新态
    saveQueryDialogVisible.value = false
    fetchSavedQueries()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally { 
    savingQuery.value = false 
  }
}

const updateCurrentQuery = async () => {
  if (!currentEditorQueryId.value) return
  savingQuery.value = true
  try {
    await axios.put(`${META_API_BASE}/${currentEditorQueryId.value}`, { 
      raw_sql: editorSql.value, 
      data_source_id: currentDataSourceId.value,
      chart_type: editorChartType.value,
      macros: editorMacros.value,
      thresholds: editorThresholds.value
    })
    ElMessage.success('更新成功')
    
    // 如果该组件存在于当前激活的看板中，一并刷新看板
    if (activeDashboard.value) {
      const needRefresh = activeDashboardLayout.value.some(w => w.query_id === currentEditorQueryId.value)
      if (needRefresh) refreshActiveDashboard()
    }
    fetchSavedQueries()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '更新失败')
  } finally { 
    savingQuery.value = false 
  }
}

const deleteSavedQuery = async (id) => {
  try {
    await axios.delete(`${META_API_BASE}/${id}`)
    ElMessage.success('删除成功')
    if (currentEditorQueryId.value === id) resetEditor() // 如果刚好在编辑这个被删除的查询，触发重置
    fetchSavedQueries()
  } catch (e) {
    ElMessage.error('删除失败')
  }
}

const loadQueryToEditor = (q) => {
  currentEditorQueryId.value = q.id
  editorSql.value = q.raw_sql; currentDataSourceId.value = q.data_source_id; editorChartType.value = q.chart_type || 'table'
  editorThresholds.value = Array.isArray(q.thresholds) ? JSON.parse(JSON.stringify(q.thresholds)) : []
  editorMacros.value = Array.isArray(q.macros) ? JSON.parse(JSON.stringify(q.macros)) : []
  runEditorQuery()
}

const resetEditor = () => {
  currentEditorQueryId.value = null
  editorSql.value = 'SELECT * FROM bi_demo.orders LIMIT 10'
  editorThresholds.value = []
  editorMacros.value = [{ key: 'version', value: 's' }]
  editorTableData.value = []
  editorColumns.value = []
  editorMetricColumns.value = new Set()
  editorChartType.value = 'table'
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
  try {
    await axios.delete(`${DASH_API_BASE}/${id}`)
    ElMessage.success('删除成功')
    if (activeDashboardId.value === id) activeDashboard.value = null
    fetchDashboards()
  } catch (e) {
    ElMessage.error('删除失败')
  }
}

const loadDashboard = async (db) => {
  activeDashboardId.value = db.id
  activeDashboard.value = db
  activeDashboardLayout.value = db.widgets || []
  isDashboardEditMode.value = false // 加载看板时默认阅读模式
  editingBoardName.value = false
  
  computeDashboardGlobalMacros()
  activeDashboardLayout.value.forEach(w => { fetchWidgetData(w) })
}

const fetchWidgetData = async (widget) => {
  widgetLoading.value[widget.i] = true
  try {
    const headers = widget.data_source_id ? { 'x-data-source-id': widget.data_source_id } : {}
    const res = await axios.post(`${API_BASE}/query/raw`, { 
      sql: widget.query_sql,
      macros: getWidgetMacrosDict(widget)
    }, { headers })
    widgetData[widget.i] = {
      columns: res.data.columns,
      data: res.data.data,
      metrics: parseMetrics(widget.query_sql, res.data.columns)
    }
  } catch (e) {
    widgetData[widget.i] = { error: '加载失败' }
  } finally {
    widgetLoading.value[widget.i] = false
  }
}

const refreshActiveDashboard = () => {
  if (activeDashboardLayout.value) {
    activeDashboardLayout.value.forEach(w => { fetchWidgetData(w) })
  }
}

const showAddWidgetDialog = () => { addWidgetDialogVisible.value = true }
const addWidgetToDashboard = (query) => {
  const newI = Date.now().toString()
  const newWidget = {
    i: newI, x: 0, y: 0, w: 6, h: 8,
    query_id: query.id, query_name: query.name, query_sql: query.raw_sql, query_thresholds: query.thresholds, 
    query_macros: query.macros || [],
    data_source_id: query.data_source_id, chart_type: query.chart_type || 'table'
  }
  activeDashboardLayout.value.push(newWidget)
  computeDashboardGlobalMacros()
  addWidgetDialogVisible.value = false
  fetchWidgetData(newWidget)
}
const removeWidget = (i) => {
  activeDashboardLayout.value = activeDashboardLayout.value.filter(w => w.i !== i)
  computeDashboardGlobalMacros()
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
  currentThresholdWidgetCols.value = widgetData[widget.i]?.columns || []
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

// --- Export Excel ---
const generateExcelWithStyle = async (columns, data, thresholds, filename) => {
  const workbook = new ExcelJS.Workbook()
  const worksheet = workbook.addWorksheet('Data')
  
  worksheet.columns = columns.map(col => ({ header: col, key: col, width: 20 }))
  const headerRow = worksheet.getRow(1)
  headerRow.font = { bold: true }
  headerRow.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb: 'FFF5F7FA' } }
  
  data.forEach((row, index) => {
    const excelRow = worksheet.addRow(row)
    if (!thresholds || thresholds.length === 0) return
    
    columns.forEach((colName, colIdx) => {
      const cell = excelRow.getCell(colIdx + 1)
      const mockCtx = { row, column: { property: colName } }
      const style = getWidgetCellStyle(mockCtx, thresholds)
      
      if (style.backgroundColor) {
        let argb = 'FFFFFFFF'
        if (style.backgroundColor.startsWith('rgba')) {
           const parts = style.backgroundColor.match(/[\d.]+/g)
           if (parts && parts.length >= 3) {
             const r = parseInt(parts[0]).toString(16).padStart(2, '0')
             const g = parseInt(parts[1]).toString(16).padStart(2, '0')
             const b = parseInt(parts[2]).toString(16).padStart(2, '0')
             argb = `FF${r}${g}${b}`.toUpperCase()
           }
        } else if (style.backgroundColor.startsWith('#')) {
           argb = 'FF' + style.backgroundColor.substring(1).toUpperCase()
        }
        cell.fill = { type: 'pattern', pattern: 'solid', fgColor: { argb } }
      }
      
      if (style.color) {
         let fontArgb = 'FF000000'
         if (style.color === '#ffffff' || style.color === '#FFFFFF') fontArgb = 'FFFFFFFF'
         cell.font = { color: { argb: fontArgb } }
      }
    })
  })
  
  const buffer = await workbook.xlsx.writeBuffer()
  saveAs(new Blob([buffer]), `${filename}.xlsx`)
}

const exportWidgetToExcel = (widget) => {
  const wd = widgetData[widget.i]
  if (!wd || !wd.columns || !wd.data) {
    ElMessage.warning('暂无数据')
    return
  }
  generateExcelWithStyle(wd.columns, wd.data, widget.query_thresholds, widget.query_name || 'Widget_Data')
}

const exportEditorToExcel = () => {
  if (editorColumns.value.length === 0) {
    ElMessage.warning('请先查询')
    return
  }
  generateExcelWithStyle(editorColumns.value, editorTableData.value, editorThresholds.value, saveQueryName.value || 'Query_Data')
}

const exportDetailToExcel = async () => {
  exportingDetail.value = true
  try {
    const headers = currentContext.value.dataSourceId ? { 'x-data-source-id': currentContext.value.dataSourceId } : {}
    const exportRes = await axios.post(`${API_BASE}/drill-through`, {
      raw_sql: currentContext.value.sourceSql.trim(),
      filters: currentContext.value.filters,
      clicked_metric: currentContext.value.metric,
      limit: 100000, 
      offset: 0,
      macros: currentContext.value.macros
    }, { headers })
    
    generateExcelWithStyle(exportRes.data.columns, exportRes.data.data, [], 'Drill_Through_Detail')
  } catch (e) {
    ElMessage.error('导出失败')
  } finally {
    exportingDetail.value = false
  }
}

// --- Drill Through ---
const handleCellClick = (row, column, sourceSql, metricCols, dsId, macros = {}) => {
  const colName = column.property
  if (!metricCols.has(colName)) return
  const filtersMap = {}
  for (const key in row) {
    if (!metricCols.has(key) && row[key] !== null) filtersMap[key] = row[key]
  }
  currentContext.value = { filters: filtersMap, metric: colName, sourceSql, dataSourceId: dsId, macros }
  detailPage.value = 1; detailVisible.value = true; loadDetailData()
}

const loadDetailData = async (colOrPage = 1) => {
  if (typeof colOrPage === 'number') detailPage.value = colOrPage
  detailLoading.value = true
  try {
    const headers = currentContext.value.dataSourceId ? { 'x-data-source-id': currentContext.value.dataSourceId } : {}
    const res = await axios.post(`${API_BASE}/drill-through`, {
      raw_sql: currentContext.value.sourceSql, filters: currentContext.value.filters,
      clicked_metric: currentContext.value.metric, limit: detailPageSize.value, offset: (detailPage.value - 1) * detailPageSize.value,
      macros: currentContext.value.macros
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
.action-bar { margin-top: 15px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 15px; }
.left-actions, .right-actions { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
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
