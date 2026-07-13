<template>
  <div class="yolo-models">
    <!-- 固定区域：标题卡片和筛选区域 -->
    <div class="sticky-header">
      <div class="ym-header-card">
        <div class="ym-header-inner">
          <div class="ym-title-group">
            <div class="ym-icon-wrap"><el-icon :size="18"><Aim /></el-icon></div>
            <div>
              <h1 class="ym-title">模型管理</h1>
              <p class="ym-subtitle">管理已训练的 YOLO 模型</p>
            </div>
          </div>
          <div class="ym-header-actions">
            <el-button @click="loadModels()" size="small">
              <el-icon><Refresh /></el-icon> 刷新
            </el-button>
          </div>
        </div>
      </div>

    <div class="filter-card">
      <div class="filter-inner">
        <el-input v-model="searchKeyword" placeholder="搜索模型名称" class="w-44" size="default" @keyup.enter="handleSearch">
          <template #prefix><el-icon :size="14"><Search /></el-icon></template>
        </el-input>
        <el-button type="primary" @click="handleSearch">
          <el-icon :size="14"><Search /></el-icon> 查询
        </el-button>
      </div>
    </div>
    </div>

    <!-- 滚动内容区域 -->
    <div class="scroll-content">
    <div class="table-card">
      <div class="table-container">
        <el-table
          :data="models"
          v-loading="loading"
          element-loading-text="加载中..."
          style="width: 100%"
          :cell-style="{ textAlign: 'center' }"
          :header-cell-style="{ textAlign: 'center', background: '#fafafa', color: '#606266', fontWeight: 600, fontSize: '12px' }"
          stripe
          empty-text="暂无训练好的模型"
          :height="tableHeight"
        >
        <el-table-column prop="id" label="模型ID" width="120">
          <template #default="{ row }">
            <span class="id-text">#{{ row.id }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="name" label="名称" min-width="200">
          <template #default="{ row }">
            <el-tooltip :content="row.name" placement="top">
              <span class="model-name-text">{{ row.name }}</span>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column prop="dataset_id" label="数据集ID" width="120">
          <template #default="{ row }">
            <span class="id-text">#{{ row.dataset_id }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="dataset_name" label="数据集名称" width="200">
          <template #default="{ row }">
            <span>{{ row.dataset_name || '未知数据集' }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="size" label="大小" width="100">
          <template #default="{ row }">
            <span class="size-text">{{ formatFileSize(row.size) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="指标" min-width="280">
          <template #default="{ row }">
            <div v-if="row.metrics" class="metrics-grid">
              <span v-if="row.metrics.map50 !== undefined && row.metrics.map50 !== null" class="metric-badge map50">mAP50: {{ (row.metrics.map50 * 100).toFixed(1) }}%</span>
              <span v-if="row.metrics['map50-95'] !== undefined && row.metrics['map50-95'] !== null" class="metric-badge map50-95">mAP50-95: {{ (row.metrics['map50-95'] * 100).toFixed(1) }}%</span>
              <span v-if="row.metrics.precision !== undefined && row.metrics.precision !== null" class="metric-badge precision">Precision: {{ (row.metrics.precision * 100).toFixed(1) }}%</span>
              <span v-if="row.metrics.recall !== undefined && row.metrics.recall !== null" class="metric-badge recall">Recall: {{ (row.metrics.recall * 100).toFixed(1) }}%</span>
            </div>
            <span v-else class="no-data">-</span>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            <span class="time-text">{{ formatTime(row.created_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <div class="action-buttons">
              <button class="ym-act ym-act-detail" @click="showModelDetail(row)">详情</button>
              <button class="ym-act ym-act-test" @click="openTestModelDialog(row)">测试</button>
              <button class="ym-act ym-act-del" @click="removeModel(row.id)">删除</button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    </div>

    </div>

    <div class="ym-page-footer">
      <el-pagination
        :current-page="pagination.page"
        :page-size="pagination.pageSize"
        :total="pagination.total"
        :page-sizes="[10, 20, 50, 100]"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="(size) => { pagination.pageSize = size; loadModels(1) }"
        @current-change="handlePageChange"
        background
        small
      />
    </div>

    <el-dialog v-model="showTestModelDialog" width="640px">
      <template #header>
        <div class="tm-dialog-header">
          <div class="tm-header-icon">
            <el-icon><Aim /></el-icon>
          </div>
          <div class="tm-header-text">
            <span class="tm-title">测试模型</span>
            <span class="tm-subtitle">上传图片进行模型推理测试</span>
          </div>
        </div>
      </template>

      <div class="tm-section tm-section--blue">
        <div class="tm-section-header">
          <span class="tm-section-icon"><el-icon><UploadFilled /></el-icon></span>
          <span class="tm-section-title">选择图片</span>
        </div>
        <div class="tm-section-body">
          <el-upload
            ref="testUploadRef"
            :auto-upload="false"
            :file-list="testFiles"
            :on-change="handleTestFileChange"
            :on-remove="handleTestFileRemove"
            accept="image/*"
            drag
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">拖拽图片到此处，或 <em>点击上传</em></div>
          </el-upload>
        </div>
      </div>

      <div class="tm-section tm-section--amber">
        <div class="tm-section-header">
          <span class="tm-section-icon"><el-icon><TrendCharts /></el-icon></span>
          <span class="tm-section-title">置信度阈值</span>
          <span class="tm-section-value">{{ (confidenceThreshold * 100).toFixed(0) }}%</span>
        </div>
        <div class="tm-section-body">
          <el-slider v-model="confidenceThreshold" :min="0" :max="1" :step="0.05" />
        </div>
      </div>

      <div v-if="testResults" class="tm-section tm-section--green">
        <div class="tm-section-header">
          <span class="tm-section-icon"><el-icon><List /></el-icon></span>
          <span class="tm-section-title">检测结果</span>
          <span class="tm-section-badge">{{ testResults.predictions.length }} 个目标</span>
        </div>
        <div class="tm-section-body">
          <div class="tm-result-image">
            <img
              v-if="testImageUrl"
              :src="testImageUrl"
              alt="检测结果"
              class="tm-preview-img"
              @click="showImagePreview = true"
            />
            <p class="tm-image-hint">点击图片放大查看</p>
          </div>
          <div v-if="testResults.predictions.length > 0" class="tm-result-list">
            <div
              v-for="(result, index) in testResults.predictions"
              :key="index"
              class="tm-result-item"
            >
              <span class="tm-result-name">{{ result.class_name }}</span>
              <span class="tm-result-conf" :class="confidenceLevel(result.confidence)">
                {{ (result.confidence * 100).toFixed(1) }}%
              </span>
            </div>
          </div>
          <div v-else class="tm-empty">
            <span>未检测到目标，请尝试降低置信度阈值</span>
          </div>
        </div>
      </div>

      <div v-if="showImagePreview" class="image-preview-overlay" @click="closePreview">
        <div class="preview-container" @click.stop>
          <button class="close-btn" @click="closePreview">×</button>
          <div class="preview-controls">
            <button class="control-btn reset-btn" @click="resetView">↺</button>
            <span class="scale-info">{{ Math.round(scale * 100) }}%</span>
          </div>
          <div
            class="image-wrapper"
            @wheel="handleWheel"
            @mousedown="handleMouseDown"
            @mousemove="handleMouseMove"
            @mouseup="handleMouseUp"
            @mouseleave="handleMouseUp"
            @dblclick="handleDoubleClick"
          >
            <img
              ref="imageRef"
              :src="testImageUrl"
              alt="放大预览"
              class="preview-image"
              :style="{
                transform: `translate(${position.x}px, ${position.y}px) scale(${scale})`,
                cursor: scale > 1 ? 'grab' : 'default'
              }"
            />
          </div>
          <div class="preview-hint">
            <p>滚轮缩放 | 拖拽移动（放大后）</p>
          </div>
        </div>
      </div>

      <template #footer>
        <el-button class="tm-btn-cancel" @click="showTestModelDialog = false">取消</el-button>
        <el-button class="tm-btn-primary" type="primary" @click="testModel" :loading="testing">开始测试</el-button>
      </template>
    </el-dialog>

    <el-drawer
      title="模型详情"
      v-model="drawerVisible"
      direction="rtl"
      size="500px"
      :with-header="true"
    >
      <div v-if="currentModel" class="model-detail">
        <div class="detail-section">
          <h3>基本信息</h3>
          <div class="detail-row">
            <span class="label">模型ID:</span>
            <span class="value">#{{ currentModel.id }}</span>
          </div>
          <div class="detail-row">
            <span class="label">模型名称:</span>
            <span class="value">{{ currentModel.name }}</span>
          </div>
          <div class="detail-row">
            <span class="label">模型大小:</span>
            <span class="value">{{ formatFileSize(currentModel.size) }}</span>
          </div>
        </div>

        <div class="detail-section">
          <h3>数据集信息</h3>
          <div class="detail-row">
            <span class="label">数据集ID:</span>
            <span class="value">#{{ currentModel.dataset_id }}</span>
          </div>
          <div class="detail-row">
            <span class="label">数据集名称:</span>
            <span class="value">{{ currentModel.dataset_name || '未知数据集' }}</span>
          </div>
          <div class="detail-row">
            <span class="label">图片数量:</span>
            <span class="value">{{ currentModel.dataset_detail?.image_count || 0 }} 张</span>
          </div>
          <div class="detail-row">
            <span class="label">标注实例:</span>
            <span class="value">{{ currentModel.dataset_detail?.label_count || 0 }} 个</span>
          </div>
          <div class="detail-row">
            <span class="label">类别数量:</span>
            <span class="value">{{ currentModel.dataset_detail?.class_count || 0 }} 类</span>
          </div>
        </div>

        <div class="detail-section">
          <h3>训练参数</h3>
          <div class="detail-row">
            <span class="label">基础模型:</span>
            <span class="value">{{ currentModel.config?.model_name || currentModel.model_name || '-' }}</span>
          </div>
          <div class="detail-row">
            <span class="label">训练轮数:</span>
            <span class="value">{{ currentModel.config?.epochs || '-' }} epochs</span>
          </div>
          <div class="detail-row">
            <span class="label">批次大小:</span>
            <span class="value">{{ currentModel.config?.batch_size || '-' }}</span>
          </div>
          <div class="detail-row">
            <span class="label">图片尺寸:</span>
            <span class="value">{{ currentModel.config?.imgsz || '-' }} px</span>
          </div>
          <div class="detail-row">
            <span class="label">训练设备:</span>
            <span class="value">{{ currentModel.config?.device || '-' }}</span>
          </div>
          <div class="detail-row">
            <span class="label">学习率:</span>
            <span class="value">{{ currentModel.config?.lr0 || '-' }}</span>
          </div>
        </div>

        <div class="detail-section">
          <h3>类别信息</h3>
          <div v-if="currentModel.classes && currentModel.classes.length > 0" class="classes-content">
            <div v-for="(cls, index) in currentModel.classes" :key="index" class="class-item">
              <span class="class-index">{{ index + 1 }}.</span>
              <span class="class-name">{{ cls }}</span>
            </div>
          </div>
          <div v-else class="no-data">暂无类别信息</div>
        </div>

        <div class="detail-section">
          <h3>其他信息</h3>
          <div class="detail-row">
            <span class="label">任务ID:</span>
            <span class="value">#{{ currentModel.task_id }}</span>
          </div>
          <div class="detail-row">
            <span class="label">模型路径:</span>
            <span class="value path-value">{{ currentModel.path }}</span>
          </div>
          <div class="detail-row">
            <span class="label">创建时间:</span>
            <span class="value">{{ formatTime(currentModel.created_at) }}</span>
          </div>
        </div>
      </div>
    </el-drawer>

    <el-dialog
      v-model="showDeleteModelDialog"
      title="删除模型"
      width="420px"
      class="delete-dialog rounded-xl overflow-hidden"
      :close-on-click-modal="false"
    >
      <div class="text-center py-8">
        <div
          class="w-16 h-16 rounded-full bg-red-50 flex items-center justify-center mx-auto mb-4">
          <el-icon :size="32" class="text-red-500">
            <Warning/>
          </el-icon>
        </div>
        <h3 class="text-lg font-medium text-gray-800 mb-3">确定要删除模型吗？</h3>
        <p class="text-gray-600 mb-2">模型名称：<em><strong>{{ deleteModelInfo.name }}</strong></em></p>
        <p class="text-gray-500 text-sm mb-5">删除后模型文件将被永久删除且无法恢复，请谨慎操作</p>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3 p-4 bg-gray-50 rounded-b-xl">
          <el-button @click="showDeleteModelDialog = false"
                     class="border-gray-200 text-gray-700 hover:bg-gray-100 text-sm py-1.5 px-4 rounded-lg">
            取消
          </el-button>
          <el-button type="danger" @click="confirmDeleteModel" :disabled="deleteCountdown > 0"
                     class="bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 border-none text-sm py-1.5 px-4 rounded-lg">
            {{ deleteCountdown > 0 ? '确认删除 (' + deleteCountdown + 's)' : '确定删除' }}
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, watch } from 'vue'
import { Refresh, UploadFilled, Warning, Search, Aim, TrendCharts, List } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getModelsList, deleteModel as deleteModelApi, predictImage } from '@/network/api'

const models = ref([])
const loading = ref(false)
const drawerVisible = ref(false)
const currentModel = ref(null)
const showDeleteModelDialog = ref(false)
const deleteModelInfo = ref({ id: null, name: '' })
const deleteCountdown = ref(0)
let deleteTimer = null
const searchKeyword = ref('')

const pagination = ref({
  page: 1,
  pageSize: 20,
  total: 0
})

const showTestModelDialog = ref(false)
const testForm = ref({})
const testFiles = ref([])
const currentTestModel = ref(null)
const confidenceThreshold = ref(0.25)
const testResults = ref(null)
const testImageUrl = ref('')
const testing = ref(false)
const showImagePreview = ref(false)
const scale = ref(1)
const position = ref({ x: 0, y: 0 })
const isDragging = ref(false)
const dragStart = ref({ x: 0, y: 0 })
const imageRef = ref(null)

const tableHeight = computed(() => {
  return window.innerHeight - 320
})

const loadModels = async (page = pagination.value.page) => {
  loading.value = true
  try {
    const params = { page, page_size: pagination.value.pageSize }
    if (searchKeyword.value?.trim()) {
      params.keyword = searchKeyword.value.trim()
    }
    const resp = await getModelsList(params)
    if (resp.code === 0) {
      models.value = resp.data.models || []
      pagination.value.total = resp.data.total || 0
      pagination.value.page = resp.data.page || 1
    }
  } catch (error) {
    console.error('加载模型列表失败:', error)
  } finally {
    loading.value = false
  }
}

const handlePageChange = (page) => {
  pagination.value.page = page
  loadModels(page)
}

const handleSearch = () => {
  pagination.value.page = 1
  loadModels(1)
}

const removeModel = (id) => {
  const model = models.value.find(m => m.id === id)
  deleteModelInfo.value = {
    id: id,
    name: model ? model.name : '未知模型'
  }
  showDeleteModelDialog.value = true
  deleteCountdown.value = 5
  clearInterval(deleteTimer)
  deleteTimer = setInterval(() => {
    deleteCountdown.value--
    if (deleteCountdown.value <= 0) {
      clearInterval(deleteTimer)
      deleteTimer = null
    }
  }, 1000)
}

const confirmDeleteModel = async () => {
  clearInterval(deleteTimer)
  deleteTimer = null
  try {
    const resp = await deleteModelApi(deleteModelInfo.value.id)
    if (resp.code === 0) {
      ElMessage.success('删除成功')
      showDeleteModelDialog.value = false
      loadModels()
    } else {
      ElMessage.error(resp.message || '删除失败')
    }
  } catch (error) {
    console.error('删除模型失败:', error)
    ElMessage.error('删除失败：网络或服务器错误')
  }
}

const showModelDetail = (model) => {
  currentModel.value = model
  drawerVisible.value = true
}

const openTestModelDialog = (model) => {
  currentTestModel.value = model
  testFiles.value = []
  testResults.value = null
  testImageUrl.value = ''
  confidenceThreshold.value = 0.25
  showTestModelDialog.value = true
}

const handleTestFileChange = (file, fileList) => {
  // 只保留最新的文件，实现单文件自动替换
  testFiles.value = fileList.slice(-1)
  testResults.value = null
  testImageUrl.value = ''
}

const handleTestFileRemove = (file, fileList) => {
  testFiles.value = fileList
  testResults.value = null
  testImageUrl.value = ''
}

const confidenceLevel = (conf) => {
  if (conf >= 0.8) return 'conf-high'
  if (conf >= 0.5) return 'conf-mid'
  return 'conf-low'
}

const testModel = async () => {
  if (testFiles.value.length === 0) {
    ElMessage.warning('请选择要测试的图片')
    return
  }

  testing.value = true
  try {
    const file = testFiles.value[0].raw
    const resp = await predictImage(currentTestModel.value.id, file, {
      conf_threshold: confidenceThreshold.value,
      save_result: true
    })
    if (resp.code === 0) {
      testResults.value = resp.data
      testImageUrl.value = resp.data.result_image || ''
      if (testImageUrl.value && !testImageUrl.value.startsWith('http')) {
        testImageUrl.value = `${import.meta.env.VITE_APP_SERVER_URL}${testImageUrl.value}`
      }
      ElMessage.success('测试完成')
    } else {
      ElMessage.error(resp.message || '测试失败')
    }
  } catch (error) {
    console.error('测试模型失败:', error)
    ElMessage.error('测试失败：网络或服务器错误')
  } finally {
    testing.value = false
  }
}

const handleWheel = (e) => {
  e.preventDefault()
  const rect = e.currentTarget.getBoundingClientRect()
  const mouseX = e.clientX - rect.left - rect.width / 2
  const mouseY = e.clientY - rect.top - rect.height / 2
  
  const delta = e.deltaY > 0 ? -0.1 : 0.1
  const newScale = Math.max(1, Math.min(10, scale.value + delta))
  
  const scaleRatio = newScale / scale.value
  position.value = {
    x: mouseX * (1 - scaleRatio) + position.value.x * scaleRatio,
    y: mouseY * (1 - scaleRatio) + position.value.y * scaleRatio
  }
  
  scale.value = newScale
}

const handleDoubleClick = (e) => {
  if (scale.value <= 1) {
    const rect = e.currentTarget.getBoundingClientRect()
    const mouseX = e.clientX - rect.left - rect.width / 2
    const mouseY = e.clientY - rect.top - rect.height / 2
    
    const targetScale = 3.5
    const scaleRatio = targetScale / scale.value
    position.value = {
      x: mouseX * (1 - scaleRatio) + position.value.x * scaleRatio,
      y: mouseY * (1 - scaleRatio) + position.value.y * scaleRatio
    }
    
    scale.value = targetScale
  } else {
    resetView()
  }
}

const handleMouseDown = (e) => {
  if (scale.value <= 1) return
  e.preventDefault()
  isDragging.value = true
  dragStart.value = { x: e.clientX - position.value.x, y: e.clientY - position.value.y }
}

const handleMouseMove = (e) => {
  if (!isDragging.value) return
  e.preventDefault()
  position.value = {
    x: e.clientX - dragStart.value.x,
    y: e.clientY - dragStart.value.y
  }
}

const handleMouseUp = () => {
  isDragging.value = false
}

const resetView = () => {
  scale.value = 1
  position.value = { x: 0, y: 0 }
}

const closePreview = () => {
  showImagePreview.value = false
  scale.value = 1
  position.value = { x: 0, y: 0 }
  isDragging.value = false
}

const formatTime = (time) => {
  if (!time) return '-'
  const date = new Date(time)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit'
  })
}

const formatFileSize = (bytes) => {
  if (!bytes) return '-'
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
  return (bytes / (1024 * 1024 * 1024)).toFixed(1) + ' GB'
}

const stopCountdown = () => {
  clearInterval(deleteTimer)
  deleteTimer = null
  deleteCountdown.value = 0
}

watch(showDeleteModelDialog, (val) => { if (!val) stopCountdown() })

onMounted(() => {
  loadModels()
})
</script>

<style scoped>
.yolo-models {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.sticky-header {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
  position: sticky;
  top: 0;
  z-index: 100;
  background-color: #f5f5f5;
  padding-bottom: 10px;
}

.scroll-content {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.ym-header-card { background: #fff; border-radius: 12px; border: 1px solid #e8e8e8; }
.ym-header-inner { display: flex; justify-content: space-between; align-items: center; padding: 14px 18px; }
.ym-title-group { display: flex; align-items: center; gap: 12px; }
.ym-icon-wrap { width: 36px; height: 36px; border-radius: 10px; background: #eef2ff; color: #5b6ef7; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.ym-title { margin: 0; font-size: 17px; font-weight: 700; color: #1d1d1f; }
.ym-subtitle { margin: 2px 0 0; font-size: 12px; color: #8e8e93; }
.ym-header-actions { display: flex; gap: 8px; }

.filter-card {
  background: #fff;
  border: 1px solid #e8e8e8;
  border-radius: 12px;
}

.filter-inner {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 16px;
  flex-wrap: wrap;
}

.table-card {
  background: #fff;
  border: 1px solid #e8e8e8;
  border-radius: 12px;
  overflow: hidden;
  flex-shrink: 0;
}

.page-header {
  z-index: 10;
}

.page-header h1 {
  margin: 0;
}

.page-header p {
  margin: 4px 0 0;
}

.action-buttons {
  display: flex;
  gap: 6px;
  justify-content: center;
}

.ym-act {
  border: none;
  border-radius: 6px;
  font-size: 12px;
  padding: 4px 10px;
  cursor: pointer;
  transition: all 0.12s ease;
  font-weight: 500;
}

.ym-act-detail { background: #eef2ff; color: #5b6ef7; }
.ym-act-detail:hover { background: #dde3ff; }
.ym-act-test { background: #ecfdf5; color: #059669; }
.ym-act-test:hover { background: #d1fae5; }
.ym-act-del { background: #fef2f2; color: #dc2626; }
.ym-act-del:hover { background: #fee2e2; }

.table-container {
  padding: 0;
}

.ym-page-footer { background: #fff; border-radius: 12px; border: 1px solid #e8e8e8; display: flex; justify-content: center; align-items: center; padding: 10px 16px; flex-shrink: 0; }

.id-text {
  font-family: monospace;
  font-size: 12px;
  color: #606266;
  background-color: #f5f7fa;
  padding: 2px 6px;
  border-radius: 4px;
}

.time-text {
  font-size: 12px;
  color: #606266;
}

.size-text {
  font-size: 12px;
  color: #606266;
}

.model-name-text {
  font-size: 13px;
  color: #303133;
  font-weight: 500;
  cursor: pointer;
}

.model-name-text:hover {
  color: #409eff;
}

.metrics-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 5px;
}

.metric-badge {
  display: inline-block;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
  white-space: nowrap;
}

.metric-badge.map50 {
  background-color: #e8f4fd;
  color: #1890ff;
}

.metric-badge.map50-95 {
  background-color: #f0f5ff;
  color: #722ed1;
}

.metric-badge.precision {
  background-color: #f6ffed;
  color: #52c41a;
}

.metric-badge.recall {
  background-color: #fff7e6;
  color: #fa8c16;
}

.no-data {
  color: #c0c4cc;
}

.classes-content {
  max-height: 150px;
  overflow-y: auto;
}

.class-item {
  display: flex;
  padding: 6px 0;
  border-bottom: 1px dashed #f0f0f0;
}

.class-item:last-child {
  border-bottom: none;
}

.class-index {
  font-size: 12px;
  color: #909399;
  flex-shrink: 0;
  width: 24px;
}

.class-name {
  font-size: 12px;
  color: #606266;
}

/* ===== SwiftUI 风格测试模型弹窗 ===== */
.tm-dialog-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 4px 0;
}

.tm-header-icon {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  background: #eef2ff;
  color: #5b6ef7;
}

.tm-header-text {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.tm-title {
  font-size: 16px;
  font-weight: 600;
  color: #1f2937;
}

.tm-subtitle {
  font-size: 12px;
  color: #9ca3af;
}

/* 分区卡片 */
.tm-section {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  margin-bottom: 14px;
  overflow: hidden;
}

.tm-section--blue {
  border-left: 3px solid #4b8af4;
}

.tm-section--amber {
  border-left: 3px solid #e8962e;
}

.tm-section--green {
  border-left: 3px solid #34d399;
}

.tm-section-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
  border-bottom: 1px solid #f3f4f6;
}

.tm-section--blue .tm-section-header {
  background: #f5f9fd;
}

.tm-section--amber .tm-section-header {
  background: #fefaf5;
}

.tm-section--green .tm-section-header {
  background: #f4fdf8;
}

.tm-section-icon {
  width: 26px;
  height: 26px;
  min-width: 26px;
  border-radius: 7px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
}

.tm-section--blue .tm-section-icon {
  background: #e8f0fe;
  color: #4b8af4;
}

.tm-section--amber .tm-section-icon {
  background: #fef3e8;
  color: #e8962e;
}

.tm-section--green .tm-section-icon {
  background: #e8faf0;
  color: #34d399;
}

.tm-section-title {
  font-size: 13px;
  font-weight: 600;
  color: #374151;
}

.tm-section-value {
  margin-left: auto;
  font-size: 12px;
  font-weight: 600;
  color: #e8962e;
  background: #fef3e8;
  padding: 1px 9px;
  border-radius: 10px;
}

.tm-section-badge {
  margin-left: auto;
  font-size: 11px;
  font-weight: 600;
  color: #34d399;
  background: #e8faf0;
  padding: 1px 9px;
  border-radius: 10px;
}

.tm-section-body {
  padding: 14px;
}

.tm-result-image {
  text-align: center;
  margin-bottom: 14px;
}

.tm-preview-img {
  max-width: 100%;
  max-height: 360px;
  border-radius: 8px;
  border: 1px solid #e5e7eb;
  cursor: pointer;
  transition: box-shadow 0.15s ease;
}

.tm-preview-img:hover {
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.tm-image-hint {
  font-size: 11px;
  color: #9ca3af;
  margin-top: 6px;
}

.tm-result-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tm-result-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  font-size: 13px;
}

.tm-result-name {
  font-weight: 500;
  color: #374151;
}

.tm-result-conf {
  font-weight: 600;
  font-size: 12px;
  padding: 1px 7px;
  border-radius: 6px;
}

.tm-result-conf.conf-high {
  background: #dcfce7;
  color: #16a34a;
}

.tm-result-conf.conf-mid {
  background: #fef9c3;
  color: #ca8a04;
}

.tm-result-conf.conf-low {
  background: #fee2e2;
  color: #dc2626;
}

.tm-empty {
  text-align: center;
  padding: 20px;
  color: #9ca3af;
  font-size: 13px;
}

.tm-btn-cancel {
  border-radius: 8px;
  font-size: 13px;
}

.tm-btn-primary {
  border-radius: 8px;
  font-size: 13px;
}

.image-preview-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.85);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 2000;
  cursor: pointer;
  backdrop-filter: blur(4px);
}

.preview-container {
  position: relative;
  width: 90vw;
  height: 90vh;
  display: flex;
  flex-direction: column;
  cursor: default;
}

.preview-controls {
  position: absolute;
  top: 10px;
  right: 60px;
  display: flex;
  gap: 10px;
  align-items: center;
  z-index: 10;
}

.control-btn {
  width: 36px;
  height: 36px;
  border: 2px solid rgba(255, 255, 255, 0.8);
  background-color: rgba(0, 0, 0, 0.7);
  color: white;
  font-size: 20px;
  cursor: pointer;
  border-radius: 50%;
  display: flex;
  justify-content: center;
  align-items: center;
  transition: all 0.2s ease;
  position: relative;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4);
}

.control-btn:hover {
  background-color: rgba(255, 255, 255, 0.9);
  color: #333;
}

.close-btn {
  position: absolute;
  top: 10px;
  right: 10px;
  width: 36px;
  height: 36px;
  border: 2px solid rgba(255, 255, 255, 0.8);
  background-color: rgba(0, 0, 0, 0.7);
  color: white;
  font-size: 20px;
  cursor: pointer;
  border-radius: 50%;
  display: flex;
  justify-content: center;
  align-items: center;
  transition: all 0.2s ease;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4);
  z-index: 100;
}

.close-btn:hover {
  background-color: rgba(255, 255, 255, 0.9);
  color: #333;
}

.scale-info {
  color: white;
  font-size: 14px;
  background-color: rgba(255, 255, 255, 0.2);
  padding: 6px 12px;
  border-radius: 4px;
}

.image-wrapper {
  width: 100%;
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
  overflow: hidden;
}

.preview-image {
  max-width: 100%;
  max-height: 100%;
  object-fit: contain;
  transition: transform 0.1s ease-out;
}

.preview-hint {
  position: absolute;
  bottom: 10px;
  left: 50%;
  transform: translateX(-50%);
  color: rgba(255, 255, 255, 0.7);
  font-size: 14px;
}

.model-detail {
  padding: 10px 0;
}

.detail-section {
  margin-bottom: 24px;
  padding-bottom: 20px;
  border-bottom: 1px solid #ebeef5;
}

.detail-section:last-child {
  border-bottom: none;
  margin-bottom: 0;
  padding-bottom: 0;
}

.detail-section h3 {
  font-size: 14px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 16px;
  padding-left: 8px;
  border-left: 3px solid #409eff;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px dashed #f0f0f0;
}

.detail-row:last-child {
  border-bottom: none;
}

.detail-row .label {
  font-size: 13px;
  color: #909399;
  flex-shrink: 0;
  width: 100px;
}

.detail-row .value {
  font-size: 13px;
  color: #606266;
  flex: 1;
  text-align: right;
}

.detail-row .value.path-value {
  font-family: monospace;
  font-size: 11px;
  word-break: break-all;
  overflow-wrap: break-word;
  text-align: left;
  line-height: 1.4;
}

.detail-row .label {
  width: 100px;
  flex-shrink: 0;
}

.detail-row .value {
  flex: 1;
  min-width: 0;
  word-break: break-word;
}

.no-data {
  color: #c0c4cc;
}

.delete-dialog {
  border-radius: 1rem;
  overflow: hidden;
  box-shadow: 0 10px 25px rgba(0, 0, 0, 0.15);

  .el-dialog__header {
    padding: 1.5rem;
    background-color: #f8fafc;
    border-bottom: 1px solid #e2e8f0;
  }

  .el-dialog__title {
    font-size: 1.125rem;
    font-weight: 600;
    color: #1a202c;
  }

  .el-dialog__body {
    padding: 0;
  }

  .el-dialog__footer {
    padding: 0;
    background-color: transparent;
  }
}
</style>