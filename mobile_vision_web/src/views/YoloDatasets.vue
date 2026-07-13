<template>
  <div class="yolo-datasets">
    <!-- 固定区域：标题和筛选 -->
    <div class="sticky-header">
      <!-- Apple-style header card -->
      <div class="yd-header-card">
        <div class="yd-header-inner">
          <div class="yd-title-group">
            <div class="yd-icon-wrap"><el-icon :size="18"><Collection /></el-icon></div>
            <div>
              <h1 class="yd-title">数据集管理</h1>
              <p class="yd-subtitle">管理 YOLO 训练数据集</p>
            </div>
          </div>
          <div class="yd-header-actions">
            <button class="yd-btn yd-btn-primary" @click="showCreateDatasetDialog = true">
              <el-icon :size="14"><Plus/></el-icon> 创建数据集
            </button>
            <button class="yd-btn yd-btn-ghost" @click="loadDatasets()">
              <el-icon :size="14"><Refresh/></el-icon> 刷新
            </button>
          </div>
        </div>
      </div>

      <!-- 搜索区域 -->
      <div class="filter-card">
        <div class="filter-inner">
          <el-input v-model="searchKeyword" placeholder="搜索数据集名称" class="filter-input"
                    @keyup.enter="handleSearch">
            <template #prefix>
              <el-icon>
                <Search/>
              </el-icon>
            </template>
          </el-input>
          <button class="filter-btn" @click="handleSearch">
            <el-icon :size="13"><Search/></el-icon> 查询
          </button>
        </div>
      </div>
    </div>

    <!-- 滚动内容区域 -->
    <div class="yd-scroll">
      <div v-if="datasets.length === 0" class="yd-empty">
        <div class="yd-empty-icon-wrap">
          <div class="yd-empty-icon-ring">
            <div class="yd-empty-icon-inner">
              <el-icon :size="28">
                <PictureRounded/>
              </el-icon>
            </div>
          </div>
        </div>
        <h3 class="yd-empty-title">暂无数据集</h3>
        <p class="yd-empty-desc">创建一个数据集开始训练吧</p>
        <button class="yd-empty-btn" @click="showCreateDatasetDialog = true">
          <el-icon :size="15">
            <Plus/>
          </el-icon>
          <span>创建数据集</span>
        </button>
      </div>

      <div v-else class="yd-grid">
        <div
          v-for="(dataset, index) in datasets"
          :key="dataset.id"
          class="yd-card"
          :style="{ borderLeftColor: getCardColor(index) }"
        >
          <!-- 头部：名称 + ID + 操作 -->
          <div class="yd-card-top">
            <div class="yd-card-title-row">
              <h3 class="yd-card-name">{{ dataset.name }}</h3>
              <span class="yd-card-id">#{{ dataset.id }}</span>
            </div>
            <div class="yd-card-actions">
              <button class="yd-icon-btn" @click.stop="openEditDatasetDialog(dataset)" title="编辑">
                <el-icon :size="13"><Edit/></el-icon>
              </button>
              <button v-if="isCreator(dataset)" class="yd-icon-btn yd-icon-btn--danger" @click.stop="deleteDataset(dataset.id)" title="删除">
                <el-icon :size="13"><Delete/></el-icon>
              </button>
            </div>
          </div>

          <!-- 创建人 -->
          <div class="yd-card-meta" v-if="dataset.create_user_nickname">
            <el-icon :size="12"><User /></el-icon>
            <span>{{ dataset.create_user_nickname }}</span>
          </div>

          <!-- 描述（始终占位，保证卡片等⾼） -->
          <p class="yd-card-desc" :class="{ 'yd-card-desc--empty': !dataset.description }">{{ dataset.description || '暂无描述' }}</p>

          <!-- 统计 + 类别 -->
          <div class="yd-card-info">
            <div class="yd-card-stats">
              <span class="yd-stat"><el-icon :size="13"><PictureRounded/></el-icon>{{ dataset.image_count }}张</span>
              <span class="yd-stat"><el-icon :size="13"><Collection/></el-icon>{{ dataset.label_count }}个</span>
              <span class="yd-stat"><el-icon :size="13"><Folder/></el-icon>{{ dataset.class_count }}类</span>
            </div>
          </div>

          <!-- 底部操作 -->
          <div class="yd-card-footer">
            <button class="yd-action-btn yd-action-btn--primary" @click="goToAnnotation(dataset.id)">
              <el-icon :size="13"><Edit/></el-icon> 标注
            </button>
            <button class="yd-action-btn yd-action-btn--info" @click="openEditClassesDialog(dataset)">
              <el-icon :size="13"><Folder/></el-icon> 类别
            </button>
            <button class="yd-action-btn yd-action-btn--accent" @click="openUploadImagesDialog(dataset.id)">
              <el-icon :size="13"><UploadIcon/></el-icon> 上传
            </button>
            <button class="yd-action-btn yd-action-btn--warning" @click="openStartTrainDialog(dataset)">
              <el-icon :size="13"><VideoPlay/></el-icon> 训练
            </button>
          </div>
        </div>
      </div>
    </div>

    <el-dialog v-model="showEditDatasetDialog" width="500px" :close-on-click-modal="false" class="ed-dialog">
      <template #header>
        <div class="ed-header">
          <span class="ed-header-icon"><el-icon :size="20"><Edit/></el-icon></span>
          <div>
            <h2 class="ed-header-title">编辑数据集</h2>
            <p class="ed-header-desc">修改数据集名称和描述信息</p>
          </div>
        </div>
      </template>
      <div class="ed-body">
        <div class="ed-section">
          <div class="ed-section-header">
            <span class="ed-section-icon"><el-icon><InfoFilled/></el-icon></span>
            <h3 class="ed-section-title">基本信息</h3>
          </div>
          <div class="ed-section-body">
            <div class="ed-field">
              <label class="ed-label">数据集名称 <span class="ed-required">*</span></label>
              <el-input v-model="editingDataset.name" placeholder="请输入数据集名称" clearable class="ed-input" />
            </div>
            <div class="ed-field">
              <label class="ed-label">描述</label>
              <el-input v-model="editingDataset.description" type="textarea" :rows="3" placeholder="请输入数据集描述（可选）" resize="none" class="ed-textarea" />
            </div>
          </div>
        </div>
      </div>
      <template #footer>
        <div class="ed-footer">
          <el-button @click="handleEditDatasetClose" class="ed-btn-cancel">取消</el-button>
          <el-button type="primary" @click="editDataset" :loading="editingDatasetLoading" class="ed-btn-primary">保存</el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog v-model="showCreateDatasetDialog" width="500px" :close-on-click-modal="false" class="cd-dialog">
      <template #header>
        <div class="cd-header">
          <span class="cd-header-icon"><el-icon :size="20"><PictureRounded/></el-icon></span>
          <div>
            <h2 class="cd-header-title">创建数据集</h2>
            <p class="cd-header-desc">创建一个新的 YOLO 目标检测训练数据集</p>
          </div>
        </div>
      </template>
      <div class="cd-body">
        <div class="cd-section">
          <div class="cd-section-header">
            <span class="cd-section-icon"><el-icon><InfoFilled/></el-icon></span>
            <h3 class="cd-section-title">基本信息</h3>
          </div>
          <div class="cd-section-body">
            <div class="cd-field">
              <label class="cd-label">数据集名称 <span class="cd-required">*</span></label>
              <el-input v-model="newDataset.name" placeholder="请输入数据集名称" clearable class="cd-input" />
            </div>
            <div class="cd-field">
              <label class="cd-label">描述</label>
              <el-input v-model="newDataset.description" type="textarea" :rows="3" placeholder="请输入数据集描述（可选）" resize="none" class="cd-textarea" />
            </div>
          </div>
        </div>
      </div>
      <template #footer>
        <div class="cd-footer">
          <el-button @click="handleCreateDatasetClose" class="cd-btn-cancel">取消</el-button>
          <el-button type="primary" @click="createDataset" :loading="creatingDataset" class="cd-btn-primary">创建</el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog v-model="showEditClassesDialog" width="720px" :close-on-click-modal="false" class="ec-dialog">
      <template #header>
        <div class="ec-header">
          <span class="ec-header-icon"><el-icon :size="20"><Folder/></el-icon></span>
          <div>
            <h2 class="ec-header-title">编辑类别</h2>
            <p class="ec-header-desc">管理数据集的标注类别列表</p>
          </div>
        </div>
      </template>
      <div class="ec-body">
        <div class="ec-section">
          <div class="ec-section-header">
            <span class="ec-section-icon"><el-icon><Collection/></el-icon></span>
            <h3 class="ec-section-title">类别列表</h3>
          </div>
          <div class="ec-section-body">
            <p class="ec-tip">提示：可以修改类别名称或添加新类别，但不能删除类别或改变顺序</p>
            <div v-for="(cls, index) in editingClasses" :key="index" class="ec-row">
              <span class="ec-badge">{{ index + 1 }}</span>
              <div class="ec-row-fields">
                <div class="ec-field">
                  <label class="ec-field-label">英文名称</label>
                  <el-input v-model="cls.english" placeholder="必填" :required="true" class="ec-input" />
                </div>
                <div class="ec-field">
                  <label class="ec-field-label">中文名称</label>
                  <el-input v-model="cls.chinese" placeholder="选填" class="ec-input" />
                </div>
              </div>
              <button v-if="cls._isNew" class="ec-btn-del" @click="removeClass(index)" title="删除">
                <el-icon :size="14"><Delete/></el-icon>
              </button>
            </div>
            <button class="ec-btn-add" @click="addNewClass">
              <el-icon :size="13"><Plus/></el-icon>
              添加新类别
            </button>
          </div>
        </div>
      </div>
      <template #footer>
        <div class="ec-footer">
          <el-button @click="showEditClassesDialog = false" class="ec-btn-cancel">取消</el-button>
          <el-button type="primary" @click="saveClasses" class="ec-btn-primary">保存</el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog v-model="showUploadDialog" title="上传图片" width="600px">
      <div class="mb-4">
        <label class="block text-sm font-medium mb-2">选择要上传到的集合</label>
        <el-radio-group v-model="selectedSplit" size="small">
          <el-radio-button value="train" label="训练集">训练集</el-radio-button>
          <el-radio-button value="val" label="验证集">验证集</el-radio-button>
          <el-radio-button value="test" label="测试集">测试集</el-radio-button>
        </el-radio-group>
      </div>
      <el-upload
        ref="uploadRef"
        :auto-upload="false"
        :file-list="uploadFiles"
        :on-change="handleFileChange"
        :on-remove="handleFileRemove"
        multiple
        drag
        accept="image/*"
        class="upload-component"
      >
        <el-icon class="el-icon--upload">
          <UploadFilled/>
        </el-icon>
        <div class="el-upload__text">拖拽图片到此处，或 <em>点击上传</em></div>
        <template #tip>
          <div class="el-upload__tip">支持 jpg、png 等图片格式</div>
        </template>
      </el-upload>
      <template #footer>
        <div class="flex justify-end gap-2">
          <el-button @click="showUploadDialog = false">取消</el-button>
          <el-button type="primary" @click="uploadImages" :loading="uploading">上传</el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog v-model="showStartTrainDialog" width="560px" :close-on-click-modal="false" class="st-dialog">
      <template #header>
        <div class="st-header">
          <span class="st-header-icon"><el-icon :size="20"><VideoPlay/></el-icon></span>
          <div>
            <h2 class="st-header-title">开始训练</h2>
            <p class="st-header-desc">配置训练参数并启动 YOLO 模型训练</p>
          </div>
        </div>
      </template>

      <!-- 模型配置 -->
      <div class="st-section">
        <div class="st-section-header">
          <span class="st-section-icon st-icon--model"><el-icon><Setting/></el-icon></span>
          <h3 class="st-section-title">模型配置</h3>
        </div>
        <div class="st-section-body">
          <div class="st-field">
            <label class="st-label">选择模型</label>
            <el-select v-model="trainConfig.model_name" placeholder="请选择模型" class="st-select-full">
              <el-option-group label="基础预训练模型">
                <el-option
                  v-for="model in baseModels"
                  :key="model.path"
                  :label="model.name"
                  :value="model.path"
                />
              </el-option-group>
              <el-option-group label="已训练模型">
                <el-option
                  v-for="model in trainedModels"
                  :key="model.path"
                  :label="`📦 ${model.name} (数据集: ${model.dataset_id}, mAP50: ${model.metrics?.map50 ? (model.metrics.map50 * 100).toFixed(1) : '-'})`"
                  :value="model.path"
                />
              </el-option-group>
            </el-select>
          </div>
        </div>
      </div>

      <!-- 训练参数 -->
      <div class="st-section">
        <div class="st-section-header">
          <span class="st-section-icon st-icon--params"><el-icon><Operation/></el-icon></span>
          <h3 class="st-section-title">训练参数</h3>
        </div>
        <div class="st-section-body">
          <div class="st-field-row">
            <div class="st-field st-field--third">
              <label class="st-label">训练轮次</label>
              <el-input-number v-model="trainConfig.epochs" :min="1" :max="1000" controls-position="right" class="st-number" />
            </div>
            <div class="st-field st-field--third">
              <label class="st-label">批次大小</label>
              <el-input-number v-model="trainConfig.batch_size" :min="1" :max="128" controls-position="right" class="st-number" />
            </div>
            <div class="st-field st-field--third">
              <label class="st-label">图像尺寸</label>
              <el-input-number v-model="trainConfig.imgsz" :min="320" :max="1280" :step="32" controls-position="right" class="st-number" />
            </div>
          </div>
          <div class="st-field">
            <label class="st-label">设备</label>
            <el-select v-model="trainConfig.device" placeholder="请选择设备" class="st-select-full">
              <el-option label="CPU" value="cpu"/>
              <el-option label="GPU (CUDA)" value="cuda"/>
              <el-option label="Apple MPS" value="mps"/>
            </el-select>
          </div>
          <div class="st-field">
            <label class="st-label">学习率</label>
            <div class="st-slider-wrap">
              <el-slider v-model="trainConfig.lr0" :min="0.0001" :max="0.1" :step="0.001" class="st-slider" />
              <span class="st-slider-value">{{ trainConfig.lr0 }}</span>
            </div>
          </div>
        </div>
      </div>

      <template #footer>
        <div class="st-footer">
          <el-button @click="showStartTrainDialog = false" class="st-btn-cancel">取消</el-button>
          <el-button type="primary" @click="startTraining" class="st-btn-primary">
            <el-icon :size="14"><VideoPlay/></el-icon> 开始训练
          </el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog
      v-model="showDeleteDatasetDialog"
      title="删除数据集"
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
        <h3 class="text-lg font-medium text-gray-800 mb-3">确定要删除数据集吗？</h3>
        <p class="text-gray-600 mb-2">数据集名称：<em><strong>{{
            deleteDatasetInfo.name
          }}</strong></em></p>
        <p class="text-gray-500 text-sm mb-5">
          删除后所有图片和标注将被永久删除且无法恢复，请谨慎操作</p>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3 p-4 bg-gray-50 rounded-b-xl">
          <el-button @click="showDeleteDatasetDialog = false"
                     class="border-gray-200 text-gray-700 hover:bg-gray-100 text-sm py-1.5 px-4 rounded-lg">
            取消
          </el-button>
          <el-button type="danger" @click="confirmDeleteDataset" :disabled="deleteCountdown > 0"
                     class="bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 border-none text-sm py-1.5 px-4 rounded-lg">
            {{ deleteCountdown > 0 ? '确认删除 (' + deleteCountdown + 's)' : '确定删除' }}
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import {ref, onMounted, computed, watch} from 'vue'
import {useRouter} from 'vue-router'
import {
  Plus,
  Refresh,
  Edit,
  VideoPlay,
  Delete,
  PictureRounded,
  Collection,
  Folder,
  InfoFilled,
  Upload as UploadIcon,
  UploadFilled,
  Warning,
  Search,
	  Setting,
	  Operation,
  User
} from '@element-plus/icons-vue'
import {ElMessage, ElMessageBox} from 'element-plus'
import {
  getYoloDatasets,
  createYoloDataset,
  deleteYoloDataset,
  updateYoloDataset,
  updateYoloDatasetClasses,
  uploadYoloImages,
  getTrainModels,
  startTrain
} from '@/network/api'

const router = useRouter()

const datasets = ref([])
const currentUsername = ref('')

const isCreator = (dataset) => {
  return dataset.create_user && currentUsername.value && dataset.create_user === currentUsername.value
}
const showCreateDatasetDialog = ref(false)
const showEditDatasetDialog = ref(false)
const showUploadDialog = ref(false)
const showStartTrainDialog = ref(false)
const showEditClassesDialog = ref(false)
const showDeleteDatasetDialog = ref(false)
const editingClasses = ref([])
const currentEditDatasetId = ref(null)
const deleteDatasetInfo = ref({id: null, name: ''})
const deleteCountdown = ref(0)
let deleteTimer = null
const editingDataset = ref({id: null, name: '', description: ''})
const editingDatasetLoading = ref(false)

const newDataset = ref({
  name: '',
  description: ''
})

const creatingDataset = ref(false)

const newDatasetCleanup = () => {
  newDataset.value = {name: '', description: ''}
}

const cardColors = [
  '#4299e1', '#38b2ac', '#805ad5', '#ed64a6', '#ed8936',
  '#319795', '#6b46c1', '#d53f8c', '#dd6b20', '#4c51bf',
  '#e53e3e', '#10b981', '#f56565', '#f6ad55', '#48bb78'
]

const getCardColor = (index) => {
  return cardColors[index % cardColors.length]
}

const getFirstLetter = (name) => {
  if (!name) return 'D'
  return name.charAt(0).toUpperCase()
}

const trainConfig = ref({
  model_name: '',
  epochs: 50,
  batch_size: 8,
  imgsz: 640,
  device: 'cpu',
  lr0: 0.01
})

const currentDatasetId = ref(null)
const uploadFiles = ref([])
const availableModels = ref([])
const uploading = ref(false)
const selectedSplit = ref('')
const searchKeyword = ref('')

const baseModels = computed(() => {
  return availableModels.value.filter(m => m.type === 'base')
})

const trainedModels = computed(() => {
  return availableModels.value.filter(m => m.type === 'trained')
})

const loadDatasets = async (keyword) => {
  try {
    const params = {}
    if (keyword) {
      params.keyword = keyword
    }
    const resp = await getYoloDatasets(params)
    if (resp.code === 0) {
      datasets.value = resp.data || []
    }
  } catch (error) {
    console.error('加载数据集失败:', error)
  }
}

const handleSearch = () => {
  const keyword = searchKeyword.value?.trim()
  loadDatasets(keyword)
}

const loadAvailableModels = async () => {
  try {
    const resp = await getTrainModels()
    if (resp.code === 0) {
      availableModels.value = resp.data || []
    }
  } catch (error) {
    console.error('加载预训练模型列表失败:', error)
  }
}

const createDataset = async () => {
  if (!newDataset.value.name.trim()) {
    ElMessage.warning('请输入数据集名称')
    return
  }
  if (newDataset.value.name.trim().length > 50) {
    ElMessage.warning('名称不能超过50个字符')
    return
  }

  creatingDataset.value = true
  try {
    const resp = await createYoloDataset({
      name: newDataset.value.name,
      description: newDataset.value.description
    })

    if (resp.code === 0) {
      ElMessage.success('数据集创建成功')
      showCreateDatasetDialog.value = false
      newDatasetCleanup()
      loadDatasets()
    } else {
      ElMessage.error(resp.message || '创建失败')
    }
  } catch (error) {
    console.error('创建数据集失败:', error)
    ElMessage.error('创建失败：网络或服务器错误')
  } finally {
    creatingDataset.value = false
  }
}

const handleCreateDatasetClose = () => {
  showCreateDatasetDialog.value = false
  newDatasetCleanup()
}

const openEditDatasetDialog = (dataset) => {
  editingDataset.value = {
    id: dataset.id,
    name: dataset.name,
    description: dataset.description || ''
  }
  showEditDatasetDialog.value = true
}

const editDataset = async () => {
  if (!editingDataset.value.name.trim()) {
    ElMessage.warning('请输入数据集名称')
    return
  }
  if (editingDataset.value.name.trim().length > 50) {
    ElMessage.warning('名称不能超过50个字符')
    return
  }

  editingDatasetLoading.value = true
  try {
    const resp = await updateYoloDataset(editingDataset.value.id, {
      name: editingDataset.value.name,
      description: editingDataset.value.description
    })

    if (resp.code === 0) {
      ElMessage.success('数据集更新成功')
      showEditDatasetDialog.value = false
      loadDatasets()
    } else {
      ElMessage.error(resp.message || '更新失败')
    }
  } catch (error) {
    console.error('更新数据集失败:', error)
    ElMessage.error('更新失败：网络或服务器错误')
  } finally {
    editingDatasetLoading.value = false
  }
}

const handleEditDatasetClose = () => {
  showEditDatasetDialog.value = false
}

const deleteDataset = (id) => {
  const dataset = datasets.value.find(d => d.id === id)
  deleteDatasetInfo.value = {
    id: id,
    name: dataset ? dataset.name : '未知数据集'
  }
  showDeleteDatasetDialog.value = true
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

const confirmDeleteDataset = async () => {
  clearInterval(deleteTimer)
  deleteTimer = null
  try {
    const resp = await deleteYoloDataset(deleteDatasetInfo.value.id)
    if (resp.code === 0) {
      ElMessage.success('删除成功')
      showDeleteDatasetDialog.value = false
      loadDatasets()
    } else {
      ElMessage.error(resp.message || '删除失败')
    }
  } catch (error) {
    console.error('删除数据集失败:', error)
    ElMessage.error('删除失败：网络或服务器错误')
  }
}

const goToAnnotation = (datasetId) => {
  router.push(`/yolo/annotation/${datasetId}`)
}

const openUploadImagesDialog = (datasetId) => {
  currentDatasetId.value = datasetId
  uploadFiles.value = []
  selectedSplit.value = 'train'
  showUploadDialog.value = true
}

const handleFileChange = (file, fileList) => {
  uploadFiles.value = fileList
}

const handleFileRemove = (file, fileList) => {
  uploadFiles.value = fileList
}

const uploadImages = async () => {
  if (uploadFiles.value.length === 0) {
    ElMessage.warning('请选择要上传的图片')
    return
  }

  if (!selectedSplit.value) {
    ElMessage.warning('请选择要上传到的集合')
    return
  }

  uploading.value = true
  try {
    const resp = await uploadYoloImages(currentDatasetId.value, uploadFiles.value.map(f => f.raw), selectedSplit.value)
    if (resp.code === 0) {
      ElMessage.success('上传成功')
      showUploadDialog.value = false
      loadDatasets()
    } else {
      ElMessage.error(resp.message || '上传失败')
    }
  } catch (error) {
    console.error('上传图片失败:', error)
    ElMessage.error('上传失败：网络或服务器错误')
  } finally {
    uploading.value = false
  }
}

const openStartTrainDialog = (dataset) => {
  currentDatasetId.value = dataset.id
  trainConfig.value = {
    model_name: '',
    epochs: 50,
    batch_size: 8,
    imgsz: 640,
    device: 'cpu',
    lr0: 0.01
  }
  showStartTrainDialog.value = true
  loadAvailableModels()
}

const startTraining = async () => {
  if (!trainConfig.value.model_name) {
    ElMessage.warning('请选择基础模型')
    return
  }

  try {
    const resp = await startTrain({
      dataset_id: currentDatasetId.value,
      config: trainConfig.value
    })

    if (resp.code === 0) {
      ElMessage.success('训练任务已启动')
      showStartTrainDialog.value = false
      router.push('/yolo/training')
    } else {
      ElMessage.error(resp.message || '启动训练失败')
    }
  } catch (error) {
    console.error('启动训练失败:', error)
    ElMessage.error('启动训练失败：网络或服务器错误')
  }
}

const openEditClassesDialog = (dataset) => {
  currentEditDatasetId.value = dataset.id
  editingClasses.value = (dataset.classes || []).map(cls => {
    if (typeof cls === 'string') {
      return {english: cls, chinese: '', _isNew: false}
    }
    return {...cls, _isNew: false}
  })
  showEditClassesDialog.value = true
}

const addNewClass = () => {
  editingClasses.value.push({english: '', chinese: '', _isNew: true})
}

const removeClass = (index) => {
  if (editingClasses.value[index]._isNew) {
    editingClasses.value.splice(index, 1)
  }
}

const saveClasses = async () => {
  const englishPattern = /^[a-zA-Z_]+$/
  const chinesePattern = /^[\u4e00-\u9fa5a-zA-Z_]+$/

  for (let i = 0; i < editingClasses.value.length; i++) {
    const cls = editingClasses.value[i]
    if (cls.english && cls.english.trim() !== '') {
      if (!englishPattern.test(cls.english.trim())) {
        ElMessage.error(`第 ${i + 1} 行英文名称只能包含英文字母和下划线`)
        return
      }
      if (cls.chinese && cls.chinese.trim() !== '' && !chinesePattern.test(cls.chinese.trim())) {
        ElMessage.error(`第 ${i + 1} 行中文名称只能包含中文、英文字母和下划线`)
        return
      }
    } else {
      ElMessage.error(`第 ${i + 1} 行英文名称不能为空`)
      return
    }
  }

  try {
    const classes = editingClasses.value.map(cls => ({
      english: cls.english.trim(),
      chinese: cls.chinese ? cls.chinese.trim() : ''
    }))

    const resp = await updateYoloDatasetClasses(currentEditDatasetId.value, classes)
    if (resp.code === 0) {
      ElMessage.success('更新成功')
      showEditClassesDialog.value = false
      loadDatasets()
    } else {
      ElMessage.error(resp.message || '更新失败')
    }
  } catch (error) {
    console.error('更新类别失败:', error)
    ElMessage.error('更新失败：网络或服务器错误')
  }
}

const stopCountdown = () => {
  clearInterval(deleteTimer)
  deleteTimer = null
  deleteCountdown.value = 0
}


watch(showDeleteDatasetDialog, (val) => {
  if (!val) stopCountdown()
})

onMounted(() => {
  const user = JSON.parse(localStorage.getItem('currentUser') || '{}')
  currentUsername.value = user.username || ''
  loadDatasets()
})
</script>

<style scoped>
.yolo-datasets {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  background: #f5f5f5;
}

/* ===== Sticky Header ===== */
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

.yd-header-card { background: #fff; border-radius: 12px; border: 1px solid #e8e8e8; }
.yd-header-inner { display: flex; justify-content: space-between; align-items: center; padding: 14px 18px; }
.yd-title-group { display: flex; align-items: center; gap: 12px; }
.yd-icon-wrap { width: 36px; height: 36px; border-radius: 10px; background: #eef2ff; color: #5b6ef7; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.yd-title { margin: 0; font-size: 17px; font-weight: 700; color: #1d1d1f; }
.yd-subtitle { margin: 2px 0 0; font-size: 12px; color: #8e8e93; }
.yd-header-actions { display: flex; gap: 8px; }

.yd-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  padding: 7px 14px;
  transition: all 0.15s ease;
}

.yd-btn-primary {
  background: #5b6ef7;
  color: #fff;
  border: none;
}

.yd-btn-primary:hover { background: #4c5fd8; }

.yd-btn-ghost {
  background: transparent;
  color: #505050;
  border: 1px solid #d1d5db;
}

.yd-btn-ghost:hover { background: #f0f0f0; }

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

.filter-input {
  width: 200px;
}

.filter-btn {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: #f5f7fa;
  border: 1px solid #e4e8ec;
  color: #646a73;
  border-radius: 6px;
  font-size: 13px;
  padding: 7px 14px;
  cursor: pointer;
  transition: all 0.15s ease;
  font-weight: 500;
}

.filter-btn:hover {
  background: #e8eef3;
}

/* ===== Scroll Content ===== */
.yd-scroll {
  flex: 1;
  overflow-y: auto;
  padding: 10px 0 20px;
}

/* ===== Empty State — SwiftUI Style ===== */
.yd-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px 60px;
  text-align: center;
  min-height: 400px;
}

.yd-empty-icon-wrap {
  margin-bottom: 24px;
  position: relative;
}

.yd-empty-icon-ring {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: linear-gradient(135deg, rgba(91, 110, 247, 0.08) 0%, rgba(91, 110, 247, 0.03) 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
  border: 1.5px solid rgba(91, 110, 247, 0.12);
  transition: all 0.3s cubic-bezier(0.25, 0.1, 0.25, 1);
}

.yd-empty-icon-inner {
  width: 52px;
  height: 52px;
  border-radius: 50%;
  background: linear-gradient(135deg, #5b6ef7 0%, #7c5ce7 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  box-shadow: 0 4px 12px rgba(91, 110, 247, 0.3);
  transition: transform 0.3s cubic-bezier(0.25, 0.1, 0.25, 1);
}

.yd-empty-icon-wrap:hover .yd-empty-icon-ring {
  border-color: rgba(91, 110, 247, 0.2);
  box-shadow: 0 0 24px rgba(91, 110, 247, 0.08);
}

.yd-empty-icon-wrap:hover .yd-empty-icon-inner {
  transform: scale(1.05);
}

.yd-empty-title {
  margin: 0 0 8px;
  font-size: 22px;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: #1d1d1f;
  background: linear-gradient(135deg, #1d1d1f 0%, #4a4a4e 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.yd-empty-desc {
  margin: 0 0 28px;
  font-size: 15px;
  color: #86868b;
  font-weight: 400;
  letter-spacing: -0.01em;
}

.yd-empty-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 7px;
  padding: 12px 28px;
  background: linear-gradient(135deg, #5b6ef7 0%, #7c5ce7 100%);
  border: none;
  border-radius: 50px;
  font-size: 15px;
  font-weight: 500;
  color: #fff;
  cursor: pointer;
  box-shadow: 0 4px 16px rgba(91, 110, 247, 0.35);
  transition: all 0.25s cubic-bezier(0.25, 0.1, 0.25, 1);
  letter-spacing: -0.01em;
  -webkit-font-smoothing: antialiased;
}

.yd-empty-btn:hover {
  background: linear-gradient(135deg, #4c5fd8 0%, #6b4cd6 100%);
  box-shadow: 0 6px 24px rgba(91, 110, 247, 0.45);
  transform: translateY(-1px);
}

.yd-empty-btn:active {
  transform: translateY(0);
  box-shadow: 0 2px 8px rgba(91, 110, 247, 0.3);
}

/* ===== Card Grid ===== */
.yd-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 14px;
  padding: 0;
}


/* ===== SwiftUI 风格卡片 ===== */
.yd-card {
  background: #fff;
  border: 1px solid #e5e7eb;
  border-left: 3px solid #4299e1;
  border-radius: 12px;
  padding: 14px 16px;
  transition: box-shadow 0.2s ease, border-color 0.2s ease;
}

.yd-card:hover {
  border-color: #d1d5db;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
}

.yd-card-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 4px;
}

.yd-card-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  flex: 1;
}

.yd-card-name {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #1d1d1f;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.yd-card-id {
  font-size: 11px;
  color: #9ca3af;
  flex-shrink: 0;
  font-feature-settings: "tnum";
}

.yd-card-actions {
  display: flex;
  gap: 2px;
  flex-shrink: 0;
}

.yd-icon-btn {
  width: 26px;
  height: 26px;
  border-radius: 6px;
  border: 1px solid #e5e7eb;
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: #9ca3af;
  transition: all 0.15s ease;
}

.yd-icon-btn:hover {
  color: #2563eb;
  border-color: #bfdbfe;
  background: #eff6ff;
}

.yd-icon-btn--danger:hover {
  color: #dc2626;
  border-color: #fecaca;
  background: #fef2f2;
}

.yd-card-meta {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-bottom: 8px;
  font-size: 11px;
  color: #9ca3af;
}

.yd-card-desc {
  margin: 0 0 10px;
  font-size: 12.5px;
  color: #6b7280;
  line-height: 1.5;
  min-height: 2.6em;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.yd-card-desc--empty {
  color: #d1d5db;
  font-style: italic;
  font-size: 12px;
}

.yd-card-info {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
}

.yd-card-stats {
  display: flex;
  gap: 4px;
  flex-shrink: 0;
}

.yd-stat {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  font-size: 11px;
  color: #6b7280;
  padding: 2px 7px;
  background: #f9fafb;
  border-radius: 6px;
  line-height: 1.3;
  white-space: nowrap;
}

.yd-card-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 3px;
  min-width: 0;
}

.yd-tag {
  display: inline-flex;
  align-items: center;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 10px;
  font-weight: 500;
  color: #4b5563;
  background: #f3f4f6;
  line-height: 1.3;
}

.yd-tag-more {
  font-size: 10px;
  color: #9ca3af;
  display: inline-flex;
  align-items: center;
  padding: 1px 4px;
}

.yd-card-footer {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 6px;
  padding-top: 10px;
  border-top: 1px solid #f3f4f6;
}

.yd-action-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: 6px 4px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  font-size: 11.5px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.15s ease;
  background: #fff;
  color: #6b7280;
  line-height: 1;
  white-space: nowrap;
}

.yd-action-btn:hover {
  border-color: #d1d5db;
  background: #f9fafb;
  color: #374151;
}

.yd-action-btn--primary {
  color: #2563eb;
  border-color: #bfdbfe;
  background: #eff6ff;
}

.yd-action-btn--primary:hover {
  color: #1d4ed8;
  border-color: #93c5fd;
  background: #dbeafe;
}

.yd-action-btn--info {
  color: #7c3aed;
  border-color: #ddd6fe;
  background: #f5f3ff;
}

.yd-action-btn--info:hover {
  color: #6d28d9;
  border-color: #c4b5fd;
  background: #ede9fe;
}

.yd-action-btn--accent {
  color: #059669;
  border-color: #a7f3d0;
  background: #ecfdf5;
}

.yd-action-btn--accent:hover {
  color: #047857;
  border-color: #6ee7b7;
  background: #d1fae5;
}

.yd-action-btn--warning {
  color: #d97706;
  border-color: #fde68a;
  background: #fffbeb;
}

.yd-action-btn--warning:hover {
  color: #b45309;
  border-color: #fcd34d;
  background: #fef3c7;
}

/* ===== 编辑类别弹窗 ===== */
.ec-dialog :deep(.el-dialog__header) {
  padding: 0;
}

.ec-dialog :deep(.el-dialog__body) {
  padding: 0 24px 20px;
}

.ec-dialog :deep(.el-dialog__footer) {
  padding: 0 24px 20px;
}

.ec-header {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 20px 24px;
  border-bottom: 1px solid #e5e7eb;
}

.ec-header-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: #5b6ef7;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 18px;
  flex-shrink: 0;
}

.ec-header-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #111827;
}

.ec-header-desc {
  margin: 2px 0 0;
  font-size: 12.5px;
  color: #9ca3af;
}

.ec-body {
  padding: 20px 0 4px;
}

.ec-section {
  border: 1px solid #e5e7eb;
  border-left: 2px solid #7c5ce7;
  border-radius: 10px;
  overflow: hidden;
}

.ec-section-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  background: #f5f3ff;
  border-bottom: 1px solid #e5e7eb;
}

.ec-section-icon {
  width: 26px;
  height: 26px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  flex-shrink: 0;
  background: #f0e8fe;
  color: #7c5ce7;
}

.ec-section-title {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
  color: #1f2937;
}

.ec-section-body {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.ec-tip {
  margin: 0;
  font-size: 12px;
  color: #9ca3af;
  line-height: 1.5;
  padding-bottom: 4px;
}

.ec-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: #fafafa;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.ec-row:hover {
  border-color: #d1d5db;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.04);
}

.ec-badge {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 7px;
  background: #f0e8fe;
  color: #7c5ce7;
  font-size: 12px;
  font-weight: 600;
  flex-shrink: 0;
  font-feature-settings: "tnum";
}

.ec-row-fields {
  display: flex;
  gap: 10px;
  flex: 1;
  min-width: 0;
}

.ec-field {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}

.ec-field-label {
  font-size: 11px;
  font-weight: 500;
  color: #9ca3af;
  padding-left: 2px;
}

.ec-input .el-input__wrapper {
  border-radius: 7px;
  box-shadow: 0 0 0 1px #e5e7eb inset;
  background: #fff;
  transition: box-shadow 0.15s ease, background 0.15s ease;
}

.ec-input .el-input__wrapper:hover {
  box-shadow: 0 0 0 1px #d1d5db inset;
}

.ec-input .el-input.is-focus .el-input__wrapper {
  box-shadow: 0 0 0 2px #5b6ef7 inset;
  background: #ffffff;
}

.ec-input .el-input__inner {
  height: 32px;
  font-size: 13px;
}

.ec-btn-del {
  width: 28px;
  height: 28px;
  border-radius: 7px;
  border: 1px solid #fecaca;
  background: #fef2f2;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: #ef4444;
  flex-shrink: 0;
  transition: all 0.15s ease;
}

.ec-btn-del:hover {
  background: #fee2e2;
  border-color: #fca5a5;
}

.ec-btn-add {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 9px 16px;
  border: 1px dashed #d1d5db;
  border-radius: 10px;
  font-size: 13px;
  font-weight: 500;
  color: #6b7280;
  background: transparent;
  cursor: pointer;
  transition: all 0.15s ease;
  margin-top: 4px;
}

.ec-btn-add:hover {
  border-color: #7c5ce7;
  color: #7c5ce7;
  background: #f5f3ff;
}

.ec-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.ec-btn-cancel {
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  padding: 8px 20px;
}

.ec-btn-primary {
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  padding: 8px 20px;
  background: #5b6ef7;
  border-color: #5b6ef7;
  box-shadow: 0 1px 3px rgba(91, 110, 247, 0.3);
}

.ec-btn-primary:hover {
  background: #4c5fd8;
  border-color: #4c5fd8;
  box-shadow: 0 2px 6px rgba(91, 110, 247, 0.4);
}

/* ===== 创建数据集弹窗 ===== */
.cd-dialog :deep(.el-dialog__header) {
  padding: 0;
}

.cd-dialog :deep(.el-dialog__body) {
  padding: 0 24px 20px;
}

.cd-dialog :deep(.el-dialog__footer) {
  padding: 0 24px 20px;
}

.cd-header {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 20px 24px;
  border-bottom: 1px solid #e5e7eb;
}

.cd-header-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: #5b6ef7;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 18px;
  flex-shrink: 0;
}

.cd-header-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #111827;
}

.cd-header-desc {
  margin: 2px 0 0;
  font-size: 12.5px;
  color: #9ca3af;
}

.cd-body {
  padding: 20px 0 4px;
}

.cd-section {
  border: 1px solid #e5e7eb;
  border-left: 2px solid #4b8af4;
  border-radius: 10px;
  overflow: hidden;
}

.cd-section-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  background: #f5f7fd;
  border-bottom: 1px solid #e5e7eb;
}

.cd-section-icon {
  width: 26px;
  height: 26px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  flex-shrink: 0;
  background: #e8f0fe;
  color: #4b8af4;
}

.cd-section-title {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
  color: #1f2937;
}

.cd-section-body {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.cd-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.cd-label {
  font-size: 12px;
  font-weight: 500;
  color: #6b7280;
}

.cd-required {
  color: #ef4444;
}

.cd-input .el-input__wrapper {
  border-radius: 8px;
  box-shadow: 0 0 0 1px #d1d5db inset;
  background: #f9fafb;
  transition: box-shadow 0.15s ease, background 0.15s ease;
}

.cd-input .el-input__wrapper:hover {
  box-shadow: 0 0 0 1px #9ca3af inset;
}

.cd-input .el-input.is-focus .el-input__wrapper {
  box-shadow: 0 0 0 2px #5b6ef7 inset;
  background: #ffffff;
}

.cd-input .el-input__inner {
  height: 38px;
  font-size: 14px;
}

.cd-textarea .el-textarea__inner {
  border-radius: 8px;
  box-shadow: 0 0 0 1px #d1d5db inset;
  background: #f9fafb;
  transition: box-shadow 0.15s ease, background 0.15s ease;
  font-size: 14px;
  line-height: 1.6;
}

.cd-textarea .el-textarea__inner:hover {
  box-shadow: 0 0 0 1px #9ca3af inset;
}

.cd-textarea .el-textarea__inner:focus {
  box-shadow: 0 0 0 2px #5b6ef7 inset;
  background: #ffffff;
}

.cd-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.cd-btn-cancel {
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  padding: 8px 20px;
}

.cd-btn-primary {
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  padding: 8px 20px;
  background: #5b6ef7;
  border-color: #5b6ef7;
  box-shadow: 0 1px 3px rgba(91, 110, 247, 0.3);
}

.cd-btn-primary:hover {
  background: #4c5fd8;
  border-color: #4c5fd8;
  box-shadow: 0 2px 6px rgba(91, 110, 247, 0.4);
}

/* ===== 编辑数据集弹窗 ===== */
.ed-dialog :deep(.el-dialog__header) {
  padding: 0;
}

.ed-dialog :deep(.el-dialog__body) {
  padding: 0;
}

.ed-dialog :deep(.el-dialog__footer) {
  padding: 0;
}

.ed-header {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 24px 24px 0;
}

.ed-header-icon {
  width: 40px;
  height: 40px;
  border-radius: 12px;
  background: #e8f0fe;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #4b8af4;
  flex-shrink: 0;
}

.ed-header-title {
  margin: 0;
  font-size: 17px;
  font-weight: 600;
  color: #1d1d1f;
}

.ed-header-desc {
  margin: 2px 0 0;
  font-size: 13px;
  color: #8e8e93;
}

.ed-body {
  padding: 20px 24px;
}

.ed-section {
  border: 1px solid #e5e7eb;
  border-radius: 12px;
  border-left: 2px solid #4b8af4;
  overflow: hidden;
}

.ed-section-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  background: #f5f7fd;
  border-bottom: 1px solid #e5e7eb;
}

.ed-section-icon {
  width: 28px;
  height: 28px;
  border-radius: 8px;
  background: #e8f0fe;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #4b8af4;
  font-size: 14px;
  flex-shrink: 0;
}

.ed-section-title {
  margin: 0;
  font-size: 14px;
  font-weight: 600;
  color: #1d1d1f;
}

.ed-section-body {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.ed-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.ed-label {
  font-size: 13px;
  font-weight: 500;
  color: #374151;
}

.ed-required {
  color: #dc2626;
}

.ed-input .el-input__wrapper {
  border-radius: 8px;
  box-shadow: 0 0 0 1px #d1d5db inset;
  background: #fafafa;
  transition: box-shadow 0.15s ease, background 0.15s ease;
}

.ed-input .el-input__wrapper:hover {
  box-shadow: 0 0 0 1px #9ca3af inset;
}

.ed-input .el-input.is-focus .el-input__wrapper {
  box-shadow: 0 0 0 2px #5b6ef7 inset;
  background: #ffffff;
}

.ed-input .el-input__inner {
  height: 38px;
  font-size: 14px;
}

.ed-textarea .el-textarea__inner {
  border-radius: 8px;
  box-shadow: 0 0 0 1px #d1d5db inset;
  background: #fafafa;
  border: none;
  font-size: 14px;
  font-family: inherit;
  transition: box-shadow 0.15s ease, background 0.15s ease;
}

.ed-textarea .el-textarea__inner:hover {
  box-shadow: 0 0 0 1px #9ca3af inset;
}

.ed-textarea .el-textarea__inner:focus {
  box-shadow: 0 0 0 2px #5b6ef7 inset;
  background: #ffffff;
}

.ed-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 16px 24px;
  border-top: 1px solid #f3f4f6;
}

.ed-btn-cancel {
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  padding: 9px 20px;
}

.ed-btn-primary {
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  padding: 9px 22px;
  background: #5b6ef7;
  border-color: #5b6ef7;
  box-shadow: 0 1px 3px rgba(91, 110, 247, 0.3);
  transition: all 0.15s ease;
}

.ed-btn-primary:hover {
  background: #4c5fd8;
  border-color: #4c5fd8;
  box-shadow: 0 2px 6px rgba(91, 110, 247, 0.4);
}

.upload-component {
  width: 100%;
}

.w-full {
  width: 100%;
}

/* ===== 开始训练弹窗 ===== */
.st-dialog :deep(.el-dialog__header) {
  padding: 0;
}

.st-dialog :deep(.el-dialog__body) {
  padding: 0 24px 20px;
}

.st-dialog :deep(.el-dialog__footer) {
  padding: 0 24px 20px;
}

.st-header {
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 20px 24px;
  border-bottom: 1px solid #e5e7eb;
}

.st-header-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  background: #5b6ef7;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-size: 18px;
  flex-shrink: 0;
}

.st-header-title {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  color: #111827;
}

.st-header-desc {
  margin: 2px 0 0;
  font-size: 12.5px;
  color: #9ca3af;
}

.st-section {
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  overflow: hidden;
  margin-bottom: 14px;
}

.st-section:last-of-type {
  margin-bottom: 0;
}

.st-section:first-of-type {
  border-left: 2px solid #4b8af4;
}

.st-section:last-of-type {
  border-left: 2px solid #7c5ce7;
}

.st-section-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  border-bottom: 1px solid #e5e7eb;
}

.st-section:first-of-type .st-section-header {
  background: #f5f7fd;
}

.st-section:last-of-type .st-section-header {
  background: #f5f3ff;
}

.st-section-icon {
  width: 26px;
  height: 26px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 13px;
  flex-shrink: 0;
}

.st-icon--model {
  background: #e8f0fe;
  color: #4b8af4;
}

.st-icon--params {
  background: #f0e8fe;
  color: #7c5ce7;
}

.st-section-title {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
  color: #1f2937;
}

.st-section-body {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.st-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.st-field--third {
  flex: 1;
  min-width: 0;
}

.st-field-row {
  display: flex;
  gap: 12px;
}

.st-label {
  font-size: 12px;
  font-weight: 500;
  color: #6b7280;
}

.st-select-full {
  width: 100%;
}

.st-select-full .el-input__wrapper {
  border-radius: 8px;
  box-shadow: 0 0 0 1px #d1d5db inset;
  background: #f9fafb;
  transition: box-shadow 0.15s ease, background 0.15s ease;
}

.st-select-full .el-input__wrapper:hover {
  box-shadow: 0 0 0 1px #9ca3af inset;
}

.st-select-full .el-input.is-focus .el-input__wrapper {
  box-shadow: 0 0 0 2px #5b6ef7 inset;
  background: #ffffff;
}

.st-number {
  width: 100%;
}

.st-number .el-input__wrapper {
  border-radius: 8px;
  box-shadow: 0 0 0 1px #d1d5db inset;
  background: #f9fafb;
}

.st-number .el-input__wrapper:hover {
  box-shadow: 0 0 0 1px #9ca3af inset;
}

.st-number .el-input.is-focus .el-input__wrapper {
  box-shadow: 0 0 0 2px #5b6ef7 inset;
  background: #ffffff;
}

.st-slider-wrap {
  display: flex;
  align-items: center;
  gap: 14px;
}

.st-slider {
  flex: 1;
}

.st-slider-value {
  font-size: 13px;
  font-weight: 500;
  color: #374151;
  font-feature-settings: "tnum";
  min-width: 48px;
  text-align: right;
}

.st-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.st-btn-cancel {
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  padding: 8px 20px;
}

.st-btn-primary {
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  padding: 8px 20px;
  background: #5b6ef7;
  border-color: #5b6ef7;
  box-shadow: 0 1px 3px rgba(91, 110, 247, 0.3);
}

.st-btn-primary:hover {
  background: #4c5fd8;
  border-color: #4c5fd8;
  box-shadow: 0 2px 6px rgba(91, 110, 247, 0.4);
}
</style>
