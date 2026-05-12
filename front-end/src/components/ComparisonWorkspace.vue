<template>
  <el-container class="comparison-layout">
    <el-aside width="260px" class="comparison-aside">
      <div class="aside-header">
        <h3>对比配置</h3>
        <el-button type="primary" size="small" icon="Plus" circle title="新建对比" @click="resetForm" />
      </div>
      <el-menu :default-active="String(currentComparisonId || '')" class="comparison-menu">
        <el-menu-item
          v-for="item in comparisons"
          :key="item.id"
          :index="String(item.id)"
          @click="loadComparison(item)"
        >
          <div class="menu-item-content">
            <span class="config-name" :title="item.name">{{ item.name }}</span>
            <el-popconfirm title="确定要删除这个对比配置吗？" @confirm="deleteComparison(item.id)" width="220" confirm-button-text="删除" confirm-button-type="danger" cancel-button-text="取消">
              <template #reference>
                <el-button type="danger" link icon="Delete" @click.stop title="删除配置" />
              </template>
            </el-popconfirm>
          </div>
        </el-menu-item>
        <div v-if="comparisons.length === 0" class="empty-text">暂无对比配置</div>
      </el-menu>
    </el-aside>

    <el-main class="comparison-main">
      <div class="editor-panel">
        <div class="form-row">
          <el-input v-model="form.name" placeholder="对比名称" class="name-input" />
          <el-select v-model="form.data_source_id" placeholder="选择数据源" class="source-select">
            <el-option v-for="ds in dataSources" :key="ds.id" :label="ds.name" :value="ds.id" />
          </el-select>
          <el-input-number v-model="form.max_rows" :min="1" :max="500000" :step="10000" controls-position="right" class="max-rows" />
        </div>

        <el-input
          v-model="form.raw_sql"
          type="textarea"
          :rows="7"
          placeholder="输入需要对比的 SQL，可使用 {{version}} 等宏变量"
          class="sql-input"
        />

        <div class="side-grid">
          <div class="side-block">
            <div class="block-title">Baseline</div>
            <el-input v-model="form.baseline_name" placeholder="baseline 名称" />
            <div class="macro-list">
              <div v-for="(macro, idx) in baselineMacros" :key="idx" class="macro-row">
                <el-input v-model="macro.key" placeholder="Key" size="small" />
                <el-input v-model="macro.value" placeholder="Value" size="small" />
                <el-button type="danger" link icon="Close" @click="baselineMacros.splice(idx, 1)" />
              </div>
              <el-button type="primary" link icon="Plus" size="small" @click="baselineMacros.push({ key: '', value: '' })">添加参数</el-button>
            </div>
          </div>
          <div class="side-block">
            <div class="block-title">Target</div>
            <el-input v-model="form.target_name" placeholder="target 名称" />
            <div class="macro-list">
              <div v-for="(macro, idx) in targetMacros" :key="idx" class="macro-row">
                <el-input v-model="macro.key" placeholder="Key" size="small" />
                <el-input v-model="macro.value" placeholder="Value" size="small" />
                <el-button type="danger" link icon="Close" @click="targetMacros.splice(idx, 1)" />
              </div>
              <el-button type="primary" link icon="Plus" size="small" @click="targetMacros.push({ key: '', value: '' })">添加参数</el-button>
            </div>
          </div>
        </div>

        <div class="field-row">
          <el-select v-model="form.key_columns" multiple filterable allow-create default-first-option placeholder="主键列" class="field-select" />
          <el-select v-model="form.group_columns" multiple filterable allow-create default-first-option placeholder="分组列，可为空" class="field-select" />
        </div>

        <div class="criteria-header">
          <span>对比标准</span>
          <el-button type="primary" link icon="Plus" @click="addCriterion">新增标准</el-button>
        </div>
        <el-table :data="form.criteria" border size="small" class="criteria-table">
          <el-table-column label="名称" min-width="140">
            <template #default="scope"><el-input v-model="scope.row.name" size="small" /></template>
          </el-table-column>
          <el-table-column label="比较列" min-width="140">
            <template #default="scope"><el-input v-model="scope.row.column" size="small" /></template>
          </el-table-column>
          <el-table-column label="方式" width="180">
            <template #default="scope">
              <el-select v-model="scope.row.mode" size="small">
                <el-option label="严格相等" value="strict_equal" />
                <el-option label="绝对容差" value="absolute_tolerance" />
                <el-option label="百分比容差" value="percent_tolerance" />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column label="容差" width="140">
            <template #default="scope">
              <el-input-number v-model="scope.row.tolerance" :controls="false" size="small" class="tolerance-input" />
            </template>
          </el-table-column>
          <el-table-column label="操作" width="80" align="center">
            <template #default="scope">
              <el-button type="danger" link icon="Delete" @click="form.criteria.splice(scope.$index, 1)" />
            </template>
          </el-table-column>
        </el-table>

        <div class="action-bar">
          <div>
            <el-button type="primary" icon="DataLine" @click="runCompare" :loading="running">运行对比</el-button>
            <el-button v-if="currentComparisonId" type="primary" plain icon="Check" @click="updateComparison" :loading="saving">更新配置</el-button>
            <el-button type="success" plain icon="Plus" @click="saveComparison" :loading="saving">{{ currentComparisonId ? '另存为' : '保存配置' }}</el-button>
            <el-button @click="resetForm">重置</el-button>
          </div>
          <el-button type="success" plain icon="Download" @click="exportSummary" :disabled="summaryRows.length === 0">导出汇总</el-button>
        </div>
      </div>

      <div class="summary-panel" v-if="summaryRows.length > 0">
        <el-table :data="summaryRows" border stripe height="100%" v-loading="running">
          <el-table-column v-for="col in resultColumns" :key="col" :prop="col" :label="columnLabel(col)" min-width="130">
            <template #default="scope">
              <el-button
                v-if="isClickableCount(col)"
                link
                type="primary"
                @click="openDetail(scope.row, statusByColumn[col])"
              >
                {{ scope.row[col] }}
              </el-button>
              <span v-else>{{ formatCell(scope.row[col], col) }}</span>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-main>

    <el-dialog v-model="detailVisible" title="对比明细" width="86%" destroy-on-close>
      <div class="detail-toolbar">
        <div>
          <el-tag v-for="(value, key) in currentDetail.group_values" :key="key" type="success" class="detail-tag">{{ key }}: {{ value }}</el-tag>
          <el-tag type="info" class="detail-tag">{{ currentDetail.criterion_name }}</el-tag>
          <el-tag :type="statusTagType(currentDetail.status)" class="detail-tag">{{ statusText(currentDetail.status) }}</el-tag>
        </div>
        <el-button type="success" icon="Download" @click="exportDetail" :disabled="detailRows.length === 0">导出当前明细</el-button>
      </div>
      <el-table :data="detailRows" border stripe height="420" v-loading="detailLoading">
        <el-table-column v-for="col in detailColumns" :key="col" :prop="col" :label="columnLabel(col)" min-width="140">
          <template #default="scope">{{ formatCell(scope.row[col], col) }}</template>
        </el-table-column>
      </el-table>
      <div class="pagination-box">
        <el-pagination background layout="total, prev, pager, next" :total="detailTotal" :page-size="detailPageSize" :current-page="detailPage" @current-change="loadDetail" />
      </div>
    </el-dialog>
  </el-container>
</template>

<script setup>
import { onMounted, ref, shallowRef } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'
import ExcelJS from 'exceljs'
import { saveAs } from 'file-saver'

const DATA_API_BASE = 'http://127.0.0.1:8000/api/v1/data'
const DS_API_BASE = 'http://127.0.0.1:8000/api/v1/data-sources'
const COMPARISON_API_BASE = 'http://127.0.0.1:8000/api/v1/comparisons'

const comparisons = ref([])
const dataSources = ref([])
const currentComparisonId = ref(null)
const saving = ref(false)
const running = ref(false)

const defaultForm = () => ({
  name: '',
  data_source_id: null,
  raw_sql: 'SELECT * FROM table_{{version}}',
  baseline_name: 'baseline',
  target_name: 'target',
  key_columns: [],
  group_columns: [],
  criteria: [{ name: '字段一致性', column: '', mode: 'strict_equal', tolerance: 0 }],
  compare_columns: [],
  max_rows: 100000,
})

const form = ref(defaultForm())
const baselineMacros = ref([{ key: 'version', value: 'baseline' }])
const targetMacros = ref([{ key: 'version', value: 'target' }])

const resultColumns = ref([])
const summaryRows = shallowRef([])
const detailVisible = ref(false)
const detailLoading = ref(false)
const detailColumns = ref([])
const detailRows = shallowRef([])
const detailTotal = ref(0)
const detailPage = ref(1)
const detailPageSize = ref(50)
const currentDetail = ref({ group_values: {}, criterion_name: '', status: '' })

const statusByColumn = {
  matched_count: 'match',
  mismatched_count: 'mismatch',
  baseline_missing_count: 'baseline_missing',
  target_missing_count: 'target_missing',
}

const fetchDataSources = async () => {
  try {
    const res = await axios.get(`${DS_API_BASE}/`)
    dataSources.value = res.data
    if (dataSources.value.length > 0 && !form.value.data_source_id) {
      form.value.data_source_id = dataSources.value[0].id
    }
  } catch (e) {
    ElMessage.error('数据源加载失败')
  }
}

const fetchComparisons = async () => {
  try {
    const res = await axios.get(`${COMPARISON_API_BASE}/`)
    comparisons.value = res.data
  } catch (e) {
    ElMessage.error('对比配置加载失败')
  }
}

const macroRowsToDict = (rows) => {
  const dict = {}
  rows.forEach(row => {
    if (row.key && row.key.trim()) dict[row.key.trim()] = String(row.value ?? '').trim()
  })
  return dict
}

const dictToMacroRows = (dict) => {
  const entries = Object.entries(dict || {})
  return entries.length ? entries.map(([key, value]) => ({ key, value })) : [{ key: '', value: '' }]
}

const buildPayload = () => ({
  ...form.value,
  baseline_macros: macroRowsToDict(baselineMacros.value),
  target_macros: macroRowsToDict(targetMacros.value),
  criteria: form.value.criteria.filter(item => item.name && item.column),
})

const validateForm = () => {
  const payload = buildPayload()
  if (!payload.data_source_id) throw new Error('请选择数据源')
  if (!payload.raw_sql.trim()) throw new Error('请输入 SQL')
  if (payload.key_columns.length === 0) throw new Error('请配置主键列')
  if (payload.criteria.length === 0) throw new Error('请至少配置一个对比标准')
  return payload
}

const runCompare = async () => {
  running.value = true
  try {
    const payload = validateForm()
    const res = await axios.post(`${DATA_API_BASE}/compare`, { config: payload })
    resultColumns.value = res.data.columns
    summaryRows.value = res.data.summary
    ElMessage.success('对比完成')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || e.message || '对比失败')
  } finally {
    running.value = false
  }
}

const saveComparison = async () => {
  saving.value = true
  try {
    const payload = validateForm()
    if (!payload.name.trim()) throw new Error('请输入对比名称')
    const res = await axios.post(`${COMPARISON_API_BASE}/`, payload)
    currentComparisonId.value = res.data.id
    await fetchComparisons()
    ElMessage.success('保存成功')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || e.message || '保存失败')
  } finally {
    saving.value = false
  }
}

const updateComparison = async () => {
  if (!currentComparisonId.value) return
  saving.value = true
  try {
    const payload = validateForm()
    await axios.put(`${COMPARISON_API_BASE}/${currentComparisonId.value}`, payload)
    await fetchComparisons()
    ElMessage.success('更新成功')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || e.message || '更新失败')
  } finally {
    saving.value = false
  }
}

const deleteComparison = async (id) => {
  try {
    await axios.delete(`${COMPARISON_API_BASE}/${id}`)
    if (currentComparisonId.value === id) resetForm()
    await fetchComparisons()
    ElMessage.success('删除成功')
  } catch (e) {
    ElMessage.error('删除失败')
  }
}

const loadComparison = (item) => {
  currentComparisonId.value = item.id
  form.value = {
    name: item.name,
    data_source_id: item.data_source_id,
    raw_sql: item.raw_sql,
    baseline_name: item.baseline_name || 'baseline',
    target_name: item.target_name || 'target',
    key_columns: item.key_columns || [],
    group_columns: item.group_columns || [],
    criteria: item.criteria?.length ? JSON.parse(JSON.stringify(item.criteria)) : [{ name: '字段一致性', column: '', mode: 'strict_equal', tolerance: 0 }],
    compare_columns: item.compare_columns || [],
    max_rows: item.max_rows || 100000,
  }
  baselineMacros.value = dictToMacroRows(item.baseline_macros)
  targetMacros.value = dictToMacroRows(item.target_macros)
  summaryRows.value = []
  resultColumns.value = []
}

const resetForm = () => {
  currentComparisonId.value = null
  form.value = defaultForm()
  if (dataSources.value.length > 0) form.value.data_source_id = dataSources.value[0].id
  baselineMacros.value = [{ key: 'version', value: 'baseline' }]
  targetMacros.value = [{ key: 'version', value: 'target' }]
  summaryRows.value = []
  resultColumns.value = []
}

const addCriterion = () => {
  form.value.criteria.push({ name: '', column: '', mode: 'strict_equal', tolerance: 0 })
}

const isClickableCount = (col) => ['matched_count', 'mismatched_count', 'baseline_missing_count', 'target_missing_count'].includes(col)

const openDetail = (row, status) => {
  currentDetail.value = {
    group_values: row.group_values || {},
    criterion_name: row.criterion_name,
    status,
  }
  detailPage.value = 1
  detailVisible.value = true
  loadDetail(1)
}

const loadDetail = async (page = 1) => {
  detailPage.value = page
  detailLoading.value = true
  try {
    const payload = validateForm()
    const res = await axios.post(`${DATA_API_BASE}/compare/detail`, {
      config: payload,
      group_values: currentDetail.value.group_values,
      criterion_name: currentDetail.value.criterion_name,
      status: currentDetail.value.status,
      limit: detailPageSize.value,
      offset: (detailPage.value - 1) * detailPageSize.value,
    })
    detailColumns.value = res.data.columns
    detailRows.value = res.data.data
    detailTotal.value = res.data.total
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '明细加载失败')
  } finally {
    detailLoading.value = false
  }
}

const generateExcel = async (columns, rows, filename) => {
  const workbook = new ExcelJS.Workbook()
  const worksheet = workbook.addWorksheet('Data')
  worksheet.columns = columns.map(col => ({ header: columnLabel(col), key: col, width: 22 }))
  worksheet.getRow(1).font = { bold: true }
  rows.forEach(row => {
    const normalized = {}
    columns.forEach(col => {
      normalized[col] = formatCell(row[col], col)
    })
    worksheet.addRow(normalized)
  })
  const buffer = await workbook.xlsx.writeBuffer()
  saveAs(new Blob([buffer]), `${filename}.xlsx`)
}

const exportSummary = () => {
  if (summaryRows.value.length === 0) return
  generateExcel(resultColumns.value, summaryRows.value, form.value.name || 'Comparison_Summary')
}

const exportDetail = () => {
  if (detailRows.value.length === 0) return
  generateExcel(detailColumns.value, detailRows.value, 'Comparison_Detail')
}

const columnLabel = (col) => ({
  criterion_name: '对比标准',
  baseline_count: 'Baseline 数量',
  target_count: 'Target 数量',
  matched_count: '一致数',
  mismatched_count: '不一致数',
  baseline_missing_count: 'Baseline 缺失',
  target_missing_count: 'Target 缺失',
  match_rate: '一致率',
  compare_column: '比较列',
  baseline_value: 'Baseline 值',
  target_value: 'Target 值',
  difference: '差值',
  change_rate: '变化率',
  diff_fields: '差异字段',
  status: '状态',
}[col] || col)

const formatCell = (value, col) => {
  if (value === null || value === undefined) return ''
  if (col === 'match_rate' || col === 'change_rate') return `${(Number(value) * 100).toFixed(2)}%`
  if (Array.isArray(value)) return value.join(', ')
  if (typeof value === 'object') return JSON.stringify(value)
  return value
}

const statusText = (status) => ({
  match: '一致',
  mismatch: '不一致',
  baseline_missing: 'Baseline 缺失',
  target_missing: 'Target 缺失',
}[status] || status)

const statusTagType = (status) => ({
  match: 'success',
  mismatch: 'danger',
  baseline_missing: 'warning',
  target_missing: 'warning',
}[status] || 'info')

onMounted(() => {
  fetchDataSources()
  fetchComparisons()
})
</script>

<style scoped>
.comparison-layout { height: 100%; }
.comparison-aside { border-right: 1px solid #dcdfe6; background: #fff; display: flex; flex-direction: column; }
.aside-header { padding: 15px 20px; border-bottom: 1px solid #ebeef5; background-color: #f8f9fa; display: flex; justify-content: space-between; align-items: center; }
.aside-header h3 { margin: 0; color: #303133; font-size: 16px; }
.comparison-menu { border-right: none; flex: 1; overflow-y: auto; }
.menu-item-content { display: flex; justify-content: space-between; align-items: center; width: 100%; }
.config-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 165px; }
.empty-text { text-align: center; color: #909399; padding: 30px 0; font-size: 14px; }
.comparison-main { display: flex; flex-direction: column; height: 100%; padding: 12px; box-sizing: border-box; overflow: hidden; }
.editor-panel { background: #fff; border: 1px solid #ebeef5; border-radius: 6px; padding: 16px; flex-shrink: 0; }
.form-row, .field-row, .action-bar { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; flex-wrap: wrap; }
.name-input { width: 260px; }
.source-select { width: 220px; }
.max-rows { width: 160px; }
.sql-input { font-family: 'Courier New', Courier, monospace; margin-bottom: 12px; }
.side-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 12px; margin-bottom: 12px; }
.side-block { border: 1px solid #ebeef5; border-radius: 6px; padding: 12px; background: #fafafa; }
.block-title { font-weight: 600; color: #303133; margin-bottom: 8px; }
.macro-list { margin-top: 8px; }
.macro-row { display: grid; grid-template-columns: minmax(80px, 1fr) minmax(100px, 1fr) 28px; gap: 8px; align-items: center; margin-bottom: 6px; }
.field-select { min-width: 260px; flex: 1; }
.criteria-header { display: flex; justify-content: space-between; align-items: center; margin: 4px 0 8px; font-weight: 600; color: #303133; }
.criteria-table { margin-bottom: 12px; }
.tolerance-input { width: 100%; }
.action-bar { justify-content: space-between; margin-bottom: 0; }
.summary-panel { flex: 1; min-height: 260px; margin-top: 12px; overflow: hidden; }
.detail-toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; gap: 12px; }
.detail-tag { margin-right: 8px; }
.pagination-box { margin-top: 14px; display: flex; justify-content: flex-end; }
</style>
