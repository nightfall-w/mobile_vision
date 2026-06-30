<template>
  <div class="yolo-datasets">
    <!-- 固定区域：标题卡片和筛选区域 -->
    <div class="sticky-header">
      <!-- 页面标题卡片 -->
      <el-card
        class="header-card rounded-xl shadow-md border-0 overflow-hidden bg-white"
      >
        <div class="relative overflow-hidden">
          <div class="absolute top-0 right-0 w-48 h-48 bg-gradient-to-bl from-blue-100 to-purple-100 rounded-full -mr-24 -mt-24 opacity-70"></div>
          <div class="absolute bottom-0 left-0 w-36 h-36 bg-gradient-to-tr from-green-100 to-blue-100 rounded-full -ml-18 -mb-18 opacity-70"></div>

          <div class="relative flex flex-col md:flex-row justify-between items-start md:items-center p-4 z-10">
            <div class="page-header mb-3 md:mb-0">
              <h1 class="text-xl font-bold text-gray-800 mb-1">数据集管理</h1>
              <p class="text-sm text-gray-600">管理YOLO目标检测训练数据集</p>
            </div>

            <div class="flex flex-wrap gap-2">
              <el-button
                type="primary"
                @click="showCreateDatasetDialog = true"
                class="text-sm px-4"
              >
                <el-icon class="mr-1" :size="14">
                  <Plus/>
                </el-icon>
                创建数据集
              </el-button>
              <el-button
                type="success"
                @click="loadDatasets"
                class="text-sm px-4"
              >
                <el-icon class="mr-1" :size="14">
                  <Refresh/>
                </el-icon>
                刷新
              </el-button>
            </div>
          </div>
        </div>
      </el-card>

      <!-- 筛选区域卡片 -->
      <el-card class="filter-card rounded-xl shadow-md border-0 bg-white">
        <div class="flex flex-wrap items-center gap-4 p-4">
          <div class="flex items-center gap-2">
            <label class="text-sm text-gray-600">状态:</label>
            <el-select
              v-model="filterStatus"
              placeholder="全部"
              class="w-36"
              size="default"
            >
              <el-option label="全部" :value="''" />
              <el-option label="正常" :value="'active'" />
              <el-option label="已禁用" :value="'disabled'" />
            </el-select>
          </div>
          <el-input
            v-model="searchKeyword"
            placeholder="搜索数据集名称"
            class="w-44"
            size="default"
            @keyup.enter="handleSearch"
          >
            <template #prefix>
              <el-icon :size="14"><Search/></el-icon>
            </template>
          </el-input>
          <el-button
            type="primary"
            @click="handleSearch"
          >
            <el-icon :size="14"><Search/></el-icon> 查询
          </el-button>
        </div>
      </el-card>
    </div>

    <!-- 滚动内容区域 -->
    <div class="scroll-content">
      <!-- 数据集列表 -->
      <div class="dataset-grid">
        <div
            v-for="(dataset, index) in datasets"
            :key="dataset.id"
            class="dataset-card bg-white rounded-lg shadow-sm hover:shadow-md transition-all duration-300 border border-gray-100 overflow-hidden relative"
          >
            <div class="absolute top-2 right-0 z-10">
              <div class="flex gap-1 mb-1 justify-end">
                <div
                  class="p-1 rounded-full bg-white bg-opacity-80 hover:bg-opacity-100 hover:bg-blue-50 cursor-pointer transition-all"
                  @click.stop="openEditDatasetDialog(dataset)"
                >
                  <el-icon :size="14" class="text-gray-600 hover:text-blue-600">
                    <Edit/>
                  </el-icon>
                </div>
                <div
                  class="p-1 rounded-full bg-white bg-opacity-80 hover:bg-opacity-100 hover:bg-red-50 cursor-pointer transition-all"
                  @click.stop="deleteDataset(dataset.id)"
                >
                  <el-icon :size="14" class="text-gray-600 hover:text-red-600">
                    <Delete/>
                  </el-icon>
                </div>
              </div>
              <div class="text-xs text-gray-400 text-right pr-2">ID: {{ dataset.id }}</div>
            </div>
            <div class="p-4">
              <div class="flex items-center mb-2">
                <div
                  class="w-7 h-7 rounded-lg flex items-center justify-center text-white font-bold text-xs"
                  :style="{ backgroundColor: getCardColor(index) }"
                >
                  {{ getFirstLetter(dataset.name) }}
                </div>
                <div class="ml-2 flex-1 min-w-0">
                  <h3 class="font-semibold text-gray-800 text-sm truncate">
                    {{ dataset.name }}
                  </h3>
                </div>
              </div>

              <p class="text-gray-500 text-xs mb-3 line-clamp-2 min-h-[2rem]">
                {{ dataset.description || '' }}
              </p>

              <div class="flex items-center gap-3 mb-3">
                <div class="flex items-center text-xs text-gray-500">
                  <el-icon :size="12" class="mr-1"><PictureRounded/></el-icon>
                  <span>{{ dataset.image_count }} 张</span>
                </div>
                <div class="flex items-center text-xs text-gray-500">
                  <el-icon :size="12" class="mr-1"><Collection/></el-icon>
                  <span>{{ dataset.label_count }} 个标注</span>
                </div>
                <div class="flex items-center text-xs text-gray-500">
                  <el-icon :size="12" class="mr-1"><Folder/></el-icon>
                  <span>{{ dataset.class_count }} 类</span>
                </div>
              </div>

              <el-popover
                v-if="dataset.classes && dataset.classes.length > 0"
                placement="top"
                trigger="hover"
                width="280"
              >
                <template #reference>
                  <div class="flex flex-wrap gap-1 mb-3 cursor-help class-tags-container">
                    <el-tag
                      v-for="cls in dataset.classes.slice(0, 4)"
                      :key="typeof cls === 'string' ? cls : cls.english"
                      size="small"
                      effect="light"
                      class="bg-blue-50 text-blue-600 border-blue-100 text-xs px-1.5 py-0.5"
                    >
                      {{ typeof cls === 'string' ? cls : cls.english }}
                    </el-tag>
                    <span v-if="dataset.classes.length > 4" class="text-xs text-gray-400">
                      +{{ dataset.classes.length - 4 }}
                    </span>
                  </div>
                </template>
                <div class="class-list">
                  <div class="class-list-header">
                    <span class="font-medium text-gray-700">所有类别</span>
                    <span class="text-xs text-gray-400">({{ dataset.classes.length }}个)</span>
                  </div>
                  <div class="class-list-content">
                    <div
                      v-for="(cls, idx) in dataset.classes"
                      :key="idx"
                      class="class-item"
                    >
                      <span class="class-index">{{ idx + 1 }}.</span>
                      <span class="class-name">
                        {{ typeof cls === 'string' ? cls : cls.english }}
                        <span v-if="typeof cls === 'object' && cls.chinese" class="class-chinese">
                          ({{ cls.chinese }})
                        </span>
                      </span>
                    </div>
                  </div>
                </div>
              </el-popover>

              <div class="flex gap-1">
                <el-button
                  size="small"
                  type="primary"
                  @click="goToAnnotation(dataset.id)"
                  class="text-xs py-0.5 px-1.5 flex-1"
                >
                  <el-icon :size="12"><Edit/></el-icon> 标注
                </el-button>
                <el-button
                  size="small"
                  type="info"
                  @click="openEditClassesDialog(dataset)"
                  class="text-xs py-0.5 px-1.5 flex-1"
                >
                  <el-icon :size="12"><Folder/></el-icon> 类别
                </el-button>
                <el-button
                  size="small"
                  type="success"
                  @click="openUploadImagesDialog(dataset.id)"
                  class="text-xs py-0.5 px-1.5 flex-1"
                >
                  <el-icon :size="12"><UploadIcon/></el-icon> 上传
                </el-button>
                <el-button
                  size="small"
                  type="warning"
                  @click="openStartTrainDialog(dataset)"
                  class="text-xs py-0.5 px-1.5 flex-1"
                >
                  <el-icon :size="12"><VideoPlay/></el-icon> 训练
                </el-button>
              </div>
            </div>
        <div v-if="datasets.length === 0" class="empty-state bg-white rounded-xl p-8 text-center border border-gray-100">
        <el-icon :size="48" class="text-gray-300 mb-3">
          <PictureRounded/>
        </el-icon>
        <h3 class="text-gray-700 font-medium mb-2 text-sm">暂无数据集</h3>
        <p class="text-gray-500 mb-4 text-xs">创建一个数据集开始训练吧</p>
        <el-button
          type="primary"
          @click="showCreateDatasetDialog = true"
          class="bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 border-none text-xs py-1.5"
        >
          <el-icon><Plus/></el-icon> 创建数据集
        </el-button>
      </div>
      </div>
    </div>
  </div>

    <el-dialog
      v-model="showEditDatasetDialog"
      title="编辑数据集"
      width="500px"
      class="custom-dialog"
    >
      <el-form
        ref="editDatasetFormRef"
        :model="editingDataset"
        :rules="editDatasetRules"
        label-width="80px"
        class="space-y-4 py-2"
      >
        <el-form-item label="数据集名称" prop="name" class="text-xs">
          <el-input
            v-model="editingDataset.name"
            placeholder="请输入数据集名称"
            clearable
            class="rounded-md border-gray-200 text-xs"
          />
        </el-form-item>
        <el-form-item label="描述" class="text-xs">
          <el-input
            v-model="editingDataset.description"
            type="textarea"
            :rows="3"
            placeholder="请输入数据集描述（可选）"
            resize="none"
            class="rounded-md border-gray-200 text-xs"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="flex justify-end gap-2">
          <el-button
            @click="handleEditDatasetClose"
            class="border-gray-200 text-gray-700 hover:bg-gray-50 text-xs py-1 px-2"
          >
            取消
          </el-button>
          <el-button
            type="primary"
            @click="editDataset"
            :loading="editingDatasetLoading"
            class="bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 border-none text-xs py-1 px-2"
          >
            保存
          </el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog
      v-model="showCreateDatasetDialog"
      title="创建数据集"
      width="500px"
      class="custom-dialog"
    >
      <el-form
        ref="createDatasetFormRef"
        :model="newDataset"
        :rules="createDatasetRules"
        label-width="80px"
        class="space-y-4 py-2"
      >
        <el-form-item label="数据集名称" prop="name" class="text-xs">
          <el-input
            v-model="newDataset.name"
            placeholder="请输入数据集名称"
            clearable
            class="rounded-md border-gray-200 text-xs"
          />
        </el-form-item>
        <el-form-item label="描述" class="text-xs">
          <el-input
            v-model="newDataset.description"
            type="textarea"
            :rows="3"
            placeholder="请输入数据集描述（可选）"
            resize="none"
            class="rounded-md border-gray-200 text-xs"
          />
        </el-form-item>
        
      </el-form>
      <template #footer>
        <div class="flex justify-end gap-2">
          <el-button
            @click="handleCreateDatasetClose"
            class="border-gray-200 text-gray-700 hover:bg-gray-50 text-xs py-1 px-2"
          >
            取消
          </el-button>
          <el-button
            type="primary"
            @click="createDataset"
            :loading="creatingDataset"
            class="bg-gradient-to-r from-blue-500 to-blue-600 hover:from-blue-600 hover:to-blue-700 border-none text-xs py-1 px-2"
          >
            创建
          </el-button>
        </div>
      </template>
    </el-dialog>

    <el-dialog v-model="showEditClassesDialog" title="编辑类别" width="750px">
      <div class="classes-editor">
        <p class="tips">提示：可以修改类别名称或添加新类别，但不能删除类别或改变顺序</p>
        <div class="classes-header">
          <div class="class-header-item class-index-header">序号</div>
          <div class="class-header-item">英文名称 <span class="required">*</span></div>
          <div class="class-header-item">中文名称</div>
          <div class="class-header-item class-action-header"></div>
        </div>
        <div v-for="(cls, index) in editingClasses" :key="index" class="class-item">
          <div class="class-index-cell">{{ index + 1 }}</div>
          <el-input
            v-model="cls.english"
            placeholder="英文名称（必填）"
            :required="true"
          />
          <el-input
            v-model="cls.chinese"
            placeholder="中文名称（选填）"
          />
          <el-button
            v-if="cls._isNew"
            type="danger"
            size="small"
            :icon="Delete"
            @click="removeClass(index)"
            circle
          />
          <div v-else class="delete-btn-placeholder" />
        </div>
        <el-button type="primary" plain @click="addNewClass" class="add-btn">
          <el-icon><Plus /></el-icon> 添加新类别
        </el-button>
      </div>
      <template #footer>
        <div class="flex justify-end gap-2">
          <el-button @click="showEditClassesDialog = false">取消</el-button>
          <el-button type="primary" @click="saveClasses">保存</el-button>
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
        <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
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

    <el-dialog v-model="showStartTrainDialog" title="开始训练" width="500px">
      <el-form :model="trainConfig" label-width="100px">
        <el-form-item label="选择模型">
          <el-select v-model="trainConfig.model_name" placeholder="请选择模型" class="w-full">
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
        </el-form-item>
        <el-form-item label="训练轮次">
          <el-input-number v-model="trainConfig.epochs" :min="1" :max="1000" />
        </el-form-item>
        <el-form-item label="批次大小">
          <el-input-number v-model="trainConfig.batch_size" :min="1" :max="128" />
        </el-form-item>
        <el-form-item label="图像尺寸">
          <el-input-number v-model="trainConfig.imgsz" :min="320" :max="1280" :step="32" />
        </el-form-item>
        <el-form-item label="设备">
          <el-select v-model="trainConfig.device" placeholder="请选择设备">
            <el-option label="CPU" value="cpu" />
            <el-option label="GPU (CUDA)" value="cuda" />
            <el-option label="Apple MPS" value="mps" />
          </el-select>
        </el-form-item>
        <el-form-item label="学习率">
          <el-slider v-model="trainConfig.lr0" :min="0.0001" :max="0.1" :step="0.001" />
          <span>{{ trainConfig.lr0 }}</span>
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="flex justify-end gap-2">
          <el-button @click="showStartTrainDialog = false">取消</el-button>
          <el-button type="primary" @click="startTraining">开始训练</el-button>
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
        <p class="text-gray-600 mb-2">数据集名称：<em><strong>{{ deleteDatasetInfo.name }}</strong></em></p>
        <p class="text-gray-500 text-sm mb-5">删除后所有图片和标注将被永久删除且无法恢复，请谨慎操作</p>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3 p-4 bg-gray-50 rounded-b-xl">
          <el-button @click="showDeleteDatasetDialog = false"
                     class="border-gray-200 text-gray-700 hover:bg-gray-100 text-sm py-1.5 px-4 rounded-lg">
            取消
          </el-button>
          <el-button type="danger" @click="confirmDeleteDataset"
                     class="bg-gradient-to-r from-red-500 to-red-600 hover:from-red-600 hover:to-red-700 border-none text-sm py-1.5 px-4 rounded-lg">
            确定删除
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { Plus, Refresh, Edit, VideoPlay, Delete, PictureRounded, Collection, Folder, InfoFilled, Upload as UploadIcon, UploadFilled, Warning, Search } from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
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
const showCreateDatasetDialog = ref(false)
const showEditDatasetDialog = ref(false)
const showUploadDialog = ref(false)
const showStartTrainDialog = ref(false)
const showEditClassesDialog = ref(false)
const showDeleteDatasetDialog = ref(false)
const editingClasses = ref([])
const currentEditDatasetId = ref(null)
const deleteDatasetInfo = ref({ id: null, name: '' })
const editingDataset = ref({ id: null, name: '', description: '' })
const editDatasetFormRef = ref()
const editingDatasetLoading = ref(false)

const newDataset = ref({
  name: '',
  description: ''
})

const createDatasetFormRef = ref()
const creatingDataset = ref(false)

const createDatasetRules = {
  name: [
    { required: true, message: '请输入数据集名称', trigger: 'blur' },
    { max: 50, message: '名称不能超过50个字符', trigger: 'blur' }
  ]
}

const editDatasetRules = {
  name: [
    { required: true, message: '请输入数据集名称', trigger: 'blur' },
    { max: 50, message: '名称不能超过50个字符', trigger: 'blur' }
  ]
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
const filterStatus = ref('')
const searchKeyword = ref('')
const allDatasets = ref([])

const baseModels = computed(() => {
  return availableModels.value.filter(m => m.type === 'base')
})

const trainedModels = computed(() => {
  return availableModels.value.filter(m => m.type === 'trained')
})

const loadDatasets = async () => {
  try {
    const resp = await getYoloDatasets()
    if (resp.code === 0) {
      allDatasets.value = resp.data || []
      datasets.value = allDatasets.value
    }
  } catch (error) {
    console.error('加载数据集失败:', error)
  }
}

const handleSearch = () => {
  let filtered = allDatasets.value
  const keyword = searchKeyword.value?.trim().toLowerCase()
  if (keyword) {
    filtered = filtered.filter(d => d.name?.toLowerCase().includes(keyword))
  }
  if (filterStatus.value) {
    filtered = filtered.filter(d => d.status === filterStatus.value)
  }
  datasets.value = filtered
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
  if (!createDatasetFormRef.value) return

  await createDatasetFormRef.value.validate(async (valid) => {
    if (!valid) return

    creatingDataset.value = true
    try {
      const resp = await createYoloDataset({
        name: newDataset.value.name,
        description: newDataset.value.description
      })

      if (resp.code === 0) {
        ElMessage.success('数据集创建成功')
        showCreateDatasetDialog.value = false
        newDataset.value = { name: '', description: '' }
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
  })
}

const handleCreateDatasetClose = () => {
  showCreateDatasetDialog.value = false
  createDatasetFormRef.value?.resetFields()
  newDataset.value = { name: '', description: '' }
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
  if (!editDatasetFormRef.value) return

  await editDatasetFormRef.value.validate(async (valid) => {
    if (!valid) return

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
  })
}

const handleEditDatasetClose = () => {
  showEditDatasetDialog.value = false
  editDatasetFormRef.value?.resetFields()
}

const deleteDataset = (id) => {
  const dataset = datasets.value.find(d => d.id === id)
  deleteDatasetInfo.value = {
    id: id,
    name: dataset ? dataset.name : '未知数据集'
  }
  showDeleteDatasetDialog.value = true
}

const confirmDeleteDataset = async () => {
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
      return { english: cls, chinese: '', _isNew: false }
    }
    return { ...cls, _isNew: false }
  })
  showEditClassesDialog.value = true
}

const addNewClass = () => {
  editingClasses.value.push({ english: '', chinese: '', _isNew: true })
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

onMounted(() => {
  loadDatasets()
})
</script>

<style scoped>
.yolo-datasets {
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
  padding-top: 10px;
}

.page-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.dataset-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
}

.header-card {
  background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
}

.filter-card {
  background: white;
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

.dataset-card {
  margin-bottom: 0;
}

.empty-state {
  grid-column: 1 / -1;
}

.class-tags-container {
  min-height: 24px;
  max-height: 24px;
  overflow: hidden;
}

.class-list {
  max-width: 280px;
}

.class-list-header {
  padding: 8px 12px;
  border-bottom: 1px solid #eee;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.class-list-content {
  max-height: 250px;
  overflow-y: auto;
}

.class-item {
  padding: 6px 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.class-item:hover {
  background-color: #f5f7fa;
}

.class-index {
  color: #909399;
  font-size: 12px;
  min-width: 24px;
}

.class-name {
  font-size: 13px;
  color: #303133;
}

.class-chinese {
  color: #909399;
  font-size: 12px;
}

.classes-editor .tips {
  color: #909399;
  font-size: 12px;
  margin-bottom: 16px;
}

.classes-header {
  display: flex;
  padding: 8px 6px;
  background-color: #f5f7fa;
  border-radius: 4px;
  margin-bottom: 8px;
  font-weight: 500;
  color: #606266;
  font-size: 13px;
}

.class-header-item {
  flex: 1;
  padding: 0 8px;
}

.class-header-item.required {
  color: #f56c6c;
}

.class-index-header {
  width: 50px;
  flex: none;
  text-align: center;
  padding: 0;
}

.class-action-header {
  width: 32px;
  flex: none;
  padding: 0;
  background-color: transparent;
}

.classes-editor .class-item {
  display: flex;
  align-items: center;
  padding: 8px 6px;
  gap: 8px;
}

.class-index-cell {
  width: 50px;
  text-align: center;
  color: #909399;
  font-size: 13px;
  flex: none;
}

.delete-btn-placeholder {
  width: 32px;
  flex: none;
}

.add-btn {
  margin-top: 12px;
}

.upload-component {
  width: 100%;
}

.w-full {
  width: 100%;
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