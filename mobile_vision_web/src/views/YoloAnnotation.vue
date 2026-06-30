<template>
  <div class="yolo-annotation">
    <!-- 页面标题卡片 -->
    <div class="annotation-header">
      <el-card class="header-card rounded-xl shadow-md border-0 overflow-hidden bg-white">
        <div class="relative overflow-hidden">
          <div class="absolute top-0 right-0 w-48 h-48 bg-gradient-to-bl from-blue-100 to-purple-100 rounded-full -mr-24 -mt-24 opacity-70"></div>
          <div class="absolute bottom-0 left-0 w-36 h-36 bg-gradient-to-tr from-green-100 to-blue-100 rounded-full -ml-18 -mb-18 opacity-70"></div>

          <div class="relative flex flex-col md:flex-row justify-between items-start md:items-center p-1 z-10">
            <div class="header-left flex items-center gap-3 mb-3 md:mb-0">
              <el-button @click="goBack" class="back-btn">
                <el-icon><ArrowLeft /></el-icon>
              </el-button>
              <div class="header-title">
                <h1 class="text-xl font-bold text-gray-800 mb-1">标注工具</h1>
                <p class="text-sm text-gray-600">{{ dataset?.name || '数据集标注' }}</p>
              </div>
            </div>

            <div class="header-actions flex flex-wrap gap-2">
              <el-select
                v-model="selectedModelId"
                placeholder="选择模型（自动标注用）"
                size="default"
                class="model-select"
              >
                <el-option
                  v-for="model in availableModels"
                  :key="model.id"
                  :label="`${model.name} (mAP50: ${model.metrics?.map50 ? (model.metrics.map50 * 100).toFixed(1) : '-'}%)`"
                  :value="model.id"
                />
              </el-select>
              <el-button
                  type="success"
                  @click="autoAnnotate"
                  :loading="autoAnnotating"
                  :disabled="!selectedModelId || images.length === 0"
                  class="action-btn"
                >
                <el-icon><Refresh /></el-icon> 自动标注
              </el-button>
              <el-button type="primary" @click="saveAnnotations" class="action-btn">
                <el-icon><Document /></el-icon> 保存标注
              </el-button>
            </div>
          </div>
        </div>
      </el-card>
    </div>

    <div class="annotation-container">
      <!-- 左侧边栏 -->
      <div class="sidebar-left">
        <div class="sidebar-card">
          <h3 class="sidebar-title">
            <el-icon><Picture /></el-icon> 图片列表
          </h3>
          <div class="split-selector mb-3">
            <el-radio-group v-model="currentSplit" size="small" @change="loadImages">
              <el-radio-button value="" label="全部">全部</el-radio-button>
              <el-radio-button value="train" label="训练集">训练集</el-radio-button>
              <el-radio-button value="val" label="验证集">验证集</el-radio-button>
              <el-radio-button value="test" label="测试集">测试集</el-radio-button>
            </el-radio-group>
          </div>
          <el-scrollbar style="flex: 1;">
            <div
              v-for="(img, index) in images"
              :key="img"
              class="image-item"
              :class="{ active: currentImageIndex === index }"
              @click="selectImage(index)"
            >
              <span>{{ img }}</span>
            </div>
          </el-scrollbar>
        </div>

        <div class="sidebar-card">
          <h3 class="sidebar-title">
            <el-icon><Collection /></el-icon> 类别
          </h3>
          <div class="class-selector">
            <el-tag
              v-for="(cls, index) in dataset?.classes || []"
              :key="index"
              class="class-tag"
              :class="{ active: currentClassIndex === index }"
              @click="currentClassIndex = index"
            >
              {{ cls }}
            </el-tag>
          </div>
        </div>
      </div>

      <!-- 中间画布区域 -->
      <div class="canvas-area">
        <div class="canvas-wrapper" ref="canvasWrapper">
          <canvas
            ref="canvas"
            @mousedown="handleMouseDown"
            @mousemove="handleMouseMove"
            @mouseup="handleMouseUp"
            @click="handleCanvasClick"
          />
        </div>

        <div class="canvas-controls">
          <el-button :disabled="currentImageIndex <= 0" @click="prevImage" class="control-btn">
            <el-icon><ArrowLeft /></el-icon> 上一张
          </el-button>
          <div class="image-counter">
            <span class="current">{{ currentImageIndex + 1 }}</span>
            <span class="separator">/</span>
            <span class="total">{{ images.length }}</span>
          </div>
          <el-button :disabled="currentImageIndex >= images.length - 1" @click="nextImage" class="control-btn">
            下一张 <el-icon><ArrowRight /></el-icon>
          </el-button>
        </div>
      </div>

      <!-- 右侧边栏 -->
      <div class="sidebar-right">
        <div class="sidebar-card">
          <h3 class="sidebar-title">
            <el-icon><List /></el-icon> 标注列表 ({{ annotations.length }})
          </h3>
          <el-scrollbar height="calc(100vh - 240px)">
            <div
              v-for="(ann, index) in annotations"
              :key="index"
              class="annotation-item"
              :class="{ selected: selectedAnnotationIndex === index }"
              @click="selectAnnotation(index)"
            >
              <div class="annotation-info">
                <span class="class-name">{{ getClassName(ann.class_id) }}</span>
                <span class="confidence">{{ getBoxInfo(ann) }}</span>
              </div>
              <div class="annotation-actions">
                <el-button type="primary" size="small" @click.stop="editAnnotationLabel(index)">
                  <el-icon><Edit /></el-icon>
                </el-button>
                <el-button type="danger" size="small" @click.stop="deleteAnnotation(index)">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </div>
            </div>
          </el-scrollbar>
        </div>
      </div>
    </div>

    <el-dialog v-model="showLabelDialog" title="选择标签" width="700px">
      <div class="label-selector">
        <el-radio-group v-model="selectedClassIndex">
          <el-radio-button
            v-for="(cls, index) in dataset?.classes || []"
            :key="index"
            :value="index"
          >
            {{ cls }}
          </el-radio-button>
        </el-radio-group>
      </div>
      <template #footer>
        <el-button @click="cancelLabelSelection">取消</el-button>
        <el-button type="primary" @click="confirmLabelSelection">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ArrowLeft, ArrowRight, Delete, Document, Edit, Refresh, Picture, Collection, List } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { getYoloDataset, getDatasetImages, getAnnotation, saveAnnotation, getModelsList, predictImage } from '@/network/api'

const router = useRouter()
const route = useRoute()

const canvas = ref(null)
const canvasWrapper = ref(null)
const currentImageIndex = ref(0)
const images = ref([])
const annotations = ref([])
const dataset = ref(null)
const currentClassIndex = ref(0)
const currentSplit = ref('')

const isDrawing = ref(false)
const startX = ref(0)
const startY = ref(0)
const tempBox = ref(null)
const image = ref(null)
const imageWidth = ref(0)
const imageHeight = ref(0)
const canvasDpr = ref(1)

const showLabelDialog = ref(false)
const selectedClassIndex = ref(0)
const pendingAnnotation = ref(null)
const editingAnnotationIndex = ref(-1)
const selectedAnnotationIndex = ref(-1)

const availableModels = ref([])
const selectedModelId = ref('')
const autoAnnotating = ref(false)

const datasetId = computed(() => route.params.datasetId)

const loadDataset = async () => {
  try {
    const resp = await getYoloDataset(datasetId.value)
    if (resp.code === 0) {
      dataset.value = resp.data
    }
  } catch (error) {
    console.error('加载数据集失败:', error)
  }
}

const loadImages = async () => {
  try {
    const resp = await getDatasetImages(datasetId.value, currentSplit.value || null)
    if (resp.code === 0) {
      images.value = resp.data || []
      if (images.value.length > 0) {
        currentImageIndex.value = 0
        await loadCurrentImage()
        await loadAnnotations()
        drawImage()
      }
    }
  } catch (error) {
    console.error('加载图片列表失败:', error)
  }
}

const hasAnnotation = (imageName) => {
  const imgIndex = images.value.indexOf(imageName)
  return imgIndex === currentImageIndex.value && annotations.value.length > 0
}

const selectImage = async (index) => {
  await saveCurrentAnnotations()
  currentImageIndex.value = index
  annotations.value = []
  selectedAnnotationIndex.value = -1
  await loadCurrentImage()
  await loadAnnotations()
  drawImage()
}

const loadCurrentImage = async () => {
  const imgPath = images.value[currentImageIndex.value]
  const fullUrl = `/api/v1/dataset/${datasetId.value}/images/${encodeURIComponent(imgPath)}`

  const currentUserSource = localStorage.getItem('currentUser')
  let authHeader = ''
  if (currentUserSource) {
    const currentUser = JSON.parse(currentUserSource)
    if (currentUser.access_token && currentUser.token_type) {
      authHeader = `${currentUser.token_type} ${currentUser.access_token}`
    }
  }

  return new Promise((resolve, reject) => {
    fetch(fullUrl, {
      method: 'GET',
      headers: {
        'Authorization': authHeader
      }
    })
    .then(response => {
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`)
      }
      return response.blob()
    })
    .then(blob => {
      const objectUrl = URL.createObjectURL(blob)
      image.value = new Image()
      image.value.onload = () => {
        URL.revokeObjectURL(objectUrl)
        resizeCanvas()
        resolve()
      }
      image.value.onerror = (err) => {
        URL.revokeObjectURL(objectUrl)
        console.error('图片加载失败:', fullUrl, err)
        reject(err)
      }
      image.value.src = objectUrl
    })
    .catch(err => {
      console.error('图片获取失败:', fullUrl, err)
      reject(err)
    })
  })
}

const resizeCanvas = () => {
  if (!canvas.value || !image.value) return

  const containerWidth = canvasWrapper.value.clientWidth
  const containerHeight = canvasWrapper.value.clientHeight

  const imageRatio = image.value.width / image.value.height
  const containerRatio = containerWidth / containerHeight

  let displayWidth, displayHeight

  if (imageRatio > containerRatio) {
    displayWidth = containerWidth
    displayHeight = containerWidth / imageRatio
  } else {
    displayHeight = containerHeight
    displayWidth = containerHeight * imageRatio
  }

  canvasDpr.value = window.devicePixelRatio || 1

  canvas.value.width = displayWidth * canvasDpr.value
  canvas.value.height = displayHeight * canvasDpr.value

  canvas.value.style.width = displayWidth + 'px'
  canvas.value.style.height = displayHeight + 'px'

  imageWidth.value = canvas.value.width
  imageHeight.value = canvas.value.height
}

const drawImage = () => {
  if (!canvas.value || !image.value) return

  const ctx = canvas.value.getContext('2d')

  ctx.clearRect(0, 0, canvas.value.width, canvas.value.height)

  ctx.imageSmoothingEnabled = true
  ctx.imageSmoothingQuality = 'high'

  ctx.drawImage(image.value, 0, 0, imageWidth.value, imageHeight.value)

  drawAnnotations()
}

const drawAnnotations = () => {
  if (!canvas.value) return

  const ctx = canvas.value.getContext('2d')
  const colors = ['#e74c3c', '#2ecc71', '#3498db', '#f39c12', '#9b59b6', '#1abc9c']

  annotations.value.forEach((ann, index) => {
    if (!ann) return

    const color = colors[ann.class_id % colors.length]
    const x = ann.x ?? ann.x_center ?? 0
    const y = ann.y ?? ann.y_center ?? 0
    const width = ann.width ?? 0
    const height = ann.height ?? 0

    const x1 = x * imageWidth.value - (width * imageWidth.value) / 2
    const y1 = y * imageHeight.value - (height * imageHeight.value) / 2
    const w = width * imageWidth.value
    const h = height * imageHeight.value

    ctx.strokeStyle = color
    ctx.lineWidth = (selectedAnnotationIndex.value === index ? 5 : 3) * canvasDpr.value
    ctx.strokeRect(x1, y1, w, h)

    // 文字背景
    const fontSize = Math.round(10 * canvasDpr.value)
    const padding = Math.round(2 * canvasDpr.value)
    const lineHeight = Math.round(16 * canvasDpr.value)
    const textOffset = Math.round(4 * canvasDpr.value)
    ctx.font = `bold ${fontSize}px Arial`
    const text = getClassName(ann.class_id)
    const textWidth = ctx.measureText(text).width
    ctx.fillStyle = 'rgba(0, 0, 0, 0.7)'
    ctx.fillRect(x1 - 1 * canvasDpr.value, y1 - lineHeight, textWidth + padding * 2, lineHeight)
    // 文字（与线框同色）
    ctx.fillStyle = color
    ctx.fillText(text, x1, y1 - textOffset)

    if (selectedAnnotationIndex.value === index) {
      ctx.fillStyle = 'rgba(64, 158, 255, 0.2)'
      ctx.fillRect(x1, y1, w, h)
    }
  })

  if (tempBox.value) {
    const color = colors[currentClassIndex.value % colors.length]
    ctx.strokeStyle = color
    ctx.lineWidth = 2 * canvasDpr.value
    ctx.setLineDash([5, 5])
    ctx.strokeRect(
      Math.min(startX.value, tempBox.value.endX),
      Math.min(startY.value, tempBox.value.endY),
      Math.abs(tempBox.value.endX - startX.value),
      Math.abs(tempBox.value.endY - startY.value)
    )
    ctx.setLineDash([])
  }
}

const getClassName = (classId) => {
  if (!dataset.value || !dataset.value.classes) return `class_${classId}`
  const cls = dataset.value.classes[classId]
  if (!cls) return `class_${classId}`
  if (typeof cls === 'object' && cls.chinese) {
    return cls.chinese
  }
  return String(cls) || `class_${classId}`
}

const getBoxInfo = (ann) => {
  const x = ann.x ?? ann.x_center ?? 0
  const y = ann.y ?? ann.y_center ?? 0
  const width = ann.width ?? 0
  const height = ann.height ?? 0
  return `x: ${x.toFixed(3)}, y: ${y.toFixed(3)}, w: ${width.toFixed(3)}, h: ${height.toFixed(3)}`
}

const loadAnnotations = async () => {
  try {
    const imgName = images.value[currentImageIndex.value]
    const resp = await getAnnotation(datasetId.value, imgName)
    if (resp.code === 0) {
      annotations.value = resp.data?.annotations || []
    } else {
      annotations.value = []
    }
  } catch (error) {
    console.error('加载标注失败:', error)
    annotations.value = []
  }
}

const saveCurrentAnnotations = async () => {
  if (annotations.value.length === 0) return

  try {
    const imgName = images.value[currentImageIndex.value]
    await saveAnnotation(datasetId.value, imgName, annotations.value)
  } catch (error) {
    console.error('保存标注失败:', error)
  }
}

const saveAnnotations = async () => {
  await saveCurrentAnnotations()
  ElMessage.success('标注保存成功')
}

const handleMouseDown = (e) => {
  isDrawing.value = true
  selectedAnnotationIndex.value = -1
  const rect = canvas.value.getBoundingClientRect()
  const scaleX = canvas.value.width / rect.width
  const scaleY = canvas.value.height / rect.height
  startX.value = (e.clientX - rect.left) * scaleX
  startY.value = (e.clientY - rect.top) * scaleY
}

const handleMouseMove = (e) => {
  if (!isDrawing.value) return

  const rect = canvas.value.getBoundingClientRect()
  const scaleX = canvas.value.width / rect.width
  const scaleY = canvas.value.height / rect.height
  tempBox.value = {
    endX: (e.clientX - rect.left) * scaleX,
    endY: (e.clientY - rect.top) * scaleY
  }
  drawImage()
}

const handleMouseUp = (e) => {
  if (!isDrawing.value) return

  isDrawing.value = false

  const rect = canvas.value.getBoundingClientRect()
  const scaleX = canvas.value.width / rect.width
  const scaleY = canvas.value.height / rect.height
  const endX = (e.clientX - rect.left) * scaleX
  const endY = (e.clientY - rect.top) * scaleY

  const x1 = Math.min(startX.value, endX)
  const y1 = Math.min(startY.value, endY)
  const w = Math.abs(endX - startX.value)
  const h = Math.abs(endY - startY.value)

  if (w > 10 && h > 10) {
    const centerX = (x1 + w / 2) / imageWidth.value
    const centerY = (y1 + h / 2) / imageHeight.value
    const normW = w / imageWidth.value
    const normH = h / imageHeight.value

    pendingAnnotation.value = {
      x: centerX,
      y: centerY,
      width: normW,
      height: normH
    }
    editingAnnotationIndex.value = -1
    selectedClassIndex.value = currentClassIndex.value
    showLabelDialog.value = true
  }

  tempBox.value = null
  drawImage()
}

const handleCanvasClick = (e) => {
  const rect = canvas.value.getBoundingClientRect()
  const scaleX = canvas.value.width / rect.width
  const scaleY = canvas.value.height / rect.height
  const clickX = (e.clientX - rect.left) * scaleX
  const clickY = (e.clientY - rect.top) * scaleY

  for (let i = annotations.value.length - 1; i >= 0; i--) {
    const ann = annotations.value[i]
    const x1 = ann.x * imageWidth.value - (ann.width * imageWidth.value) / 2
    const y1 = ann.y * imageHeight.value - (ann.height * imageHeight.value) / 2
    const w = ann.width * imageWidth.value
    const h = ann.height * imageHeight.value

    if (clickX >= x1 && clickX <= x1 + w && clickY >= y1 && clickY <= y1 + h) {
      selectAnnotation(i)
      return
    }
  }
  selectedAnnotationIndex.value = -1
  drawImage()
}

const selectAnnotation = (index) => {
  selectedAnnotationIndex.value = index
  drawImage()
}

const editAnnotationLabel = (index) => {
  editingAnnotationIndex.value = index
  selectedClassIndex.value = annotations.value[index].class_id
  showLabelDialog.value = true
}

const cancelLabelSelection = () => {
  if (editingAnnotationIndex.value === -1 && pendingAnnotation.value) {
    pendingAnnotation.value = null
  }
  editingAnnotationIndex.value = -1
  showLabelDialog.value = false
}

const confirmLabelSelection = () => {
  if (editingAnnotationIndex.value >= 0) {
    annotations.value[editingAnnotationIndex.value].class_id = selectedClassIndex.value
  } else if (pendingAnnotation.value) {
    annotations.value.push({
      class_id: selectedClassIndex.value,
      ...pendingAnnotation.value
    })
    pendingAnnotation.value = null
  }
  showLabelDialog.value = false
  editingAnnotationIndex.value = -1
  drawImage()
}

const deleteAnnotation = (index) => {
  annotations.value.splice(index, 1)
  if (selectedAnnotationIndex.value === index) {
    selectedAnnotationIndex.value = -1
  }
  drawImage()
}

const nextImage = () => {
  if (currentImageIndex.value < images.value.length - 1) {
    selectImage(currentImageIndex.value + 1)
  }
}

const prevImage = () => {
  if (currentImageIndex.value > 0) {
    selectImage(currentImageIndex.value - 1)
  }
}

const loadModels = async () => {
  try {
    const resp = await getModelsList({ page_size: 100 })
    if (resp.code === 0) {
      availableModels.value = resp.data.models || []
    }
  } catch (error) {
    console.error('加载模型列表失败:', error)
  }
}

const autoAnnotate = async () => {
  if (!selectedModelId.value) {
    ElMessage.warning('请先选择一个模型')
    return
  }

  if (!image.value) {
    ElMessage.warning('请先选择一张图片')
    return
  }

  autoAnnotating.value = true
  try {
    const imgPath = images.value[currentImageIndex.value]
    const imageUrl = `${import.meta.env.VITE_APP_SERVER_URL}/api/v1/dataset/${datasetId.value}/images/${encodeURIComponent(imgPath)}`

    // 获取认证token
    const currentUserSource = localStorage.getItem('currentUser')
    let authHeader = ''
    if (currentUserSource) {
      const currentUser = JSON.parse(currentUserSource)
      if (currentUser.access_token && currentUser.token_type) {
        authHeader = `${currentUser.token_type} ${currentUser.access_token}`
      }
    }

    const response = await fetch(imageUrl, {
      headers: {
        'Authorization': authHeader
      }
    })
    const blob = await response.blob()
    const file = new File([blob], imgPath, { type: blob.type })

    const resp = await predictImage(selectedModelId.value, file, {
      conf_threshold: 0.3,
      save_result: false
    })

    if (resp.code === 0 && resp.data.predictions) {
      const predictions = resp.data.predictions
      const newAnnotations = []

      for (const pred of predictions) {
        const className = pred.class_name
        let classId = -1

        if (dataset.value && dataset.value.classes) {
          for (let i = 0; i < dataset.value.classes.length; i++) {
            const cls = dataset.value.classes[i]
            const clsName = typeof cls === 'object' ? cls.english : cls
            if (clsName === className) {
              classId = i
              break
            }
          }
        }

        if (classId >= 0) {
          const bbox = pred.bbox
          const x1 = bbox.x1
          const y1 = bbox.y1
          const x2 = bbox.x2
          const y2 = bbox.y2

          const imgWidth = image.value ? image.value.width : 720
          const imgHeight = image.value ? image.value.height : 1280

          const xCenter = ((x1 + x2) / 2) / imgWidth
          const yCenter = ((y1 + y2) / 2) / imgHeight
          const width = (x2 - x1) / imgWidth
          const height = (y2 - y1) / imgHeight

          newAnnotations.push({
            class_id: classId,
            x: xCenter,
            y: yCenter,
            width: width,
            height: height,
            confidence: pred.confidence
          })
        }
      }

      annotations.value = newAnnotations
      selectedAnnotationIndex.value = -1
      ElMessage.success(`自动标注完成，共识别 ${newAnnotations.length} 个目标`)
      drawImage()
    } else {
      ElMessage.error('自动标注失败')
    }
  } catch (error) {
    console.error('自动标注失败:', error)
    ElMessage.error('自动标注失败：网络或服务器错误')
  } finally {
    autoAnnotating.value = false
  }
}

const goBack = () => {
  saveCurrentAnnotations()
  router.push('/yolo')
}

onMounted(async () => {
  await loadDataset()
  await loadModels()
  await loadImages()
  if (images.value.length > 0) {
    await loadCurrentImage()
    await loadAnnotations()
    drawImage()
  }
})
</script>

<style scoped>
.yolo-annotation {
  height: calc(100vh - 60px);
  display: flex;
  flex-direction: column;
  background: #f9fafb;
}

.annotation-header {
  flex-shrink: 0;
}

.header-card {
  background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
  border-radius: 8px;
}

.header-card :deep(.el-card__body) {
  padding: 8px 12px;
}

.back-btn {
  width: 32px;
  height: 32px;
  border-radius: 6px;
}

.header-title h1 {
  margin: 0;
  font-size: 16px;
}

.header-title p {
  margin: 0;
  font-size: 11px;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 6px;
}

.model-select {
  width: 180px;
}

.action-btn {
  border-radius: 6px;
  font-size: 12px;
}

.annotation-container {
  display: flex;
  flex: 1;
  overflow: hidden;
  gap: 10px;
  margin-top: 10px;
  height: calc(100vh - 200px);
}

.sidebar-left {
  flex: 0 0 28%;
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-width: 380px;
  height: 100%;
  overflow: hidden;
}

.sidebar-right {
  flex: 0 0 35%;
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-width: 400px;
  height: 100%;
  overflow: hidden;
}

.sidebar-card {
  background: white;
  border-radius: 10px;
  padding: 12px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
  display: flex;
  flex-direction: column;
  flex: 1;
  overflow: hidden;
}

.sidebar-title {
  margin: 0 0 10px 0;
  font-size: 13px;
  font-weight: 600;
  color: #374151;
  display: flex;
  align-items: center;
  gap: 6px;
}

.sidebar-title .el-icon {
  font-size: 16px;
  color: #409eff;
}

.split-selector {
  margin-bottom: 12px;
}

.split-selector :deep(.el-radio-button__inner) {
  border-radius: 6px;
  margin: 0 4px;
}

.split-selector :deep(.el-radio-button:first-child .el-radio-button__inner) {
  border-top-left-radius: 6px;
  border-bottom-left-radius: 6px;
}

.split-selector :deep(.el-radio-button:last-child .el-radio-button__inner) {
  border-top-right-radius: 6px;
  border-bottom-right-radius: 6px;
}

.class-selector {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  overflow-y: auto;
  flex: 1;
  padding-right: 5px;
}

.image-item {
  padding: 10px 12px;
  margin-bottom: 8px;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  font-size: 13px;
  gap: 8px;
  transition: all 0.2s;
}

.image-item span {
  flex: 1;
  word-break: break-all;
  overflow-wrap: break-word;
  white-space: normal;
}

.image-item:hover {
  background: #f3f4f6;
  border-color: #d1d5db;
}

.image-item.active {
  background: linear-gradient(135deg, #409eff 0%, #3a8ee6 100%);
  color: white;
  border-color: #409eff;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.3);
}

.class-tag {
  cursor: pointer;
  padding: 8px 14px;
  flex-shrink: 0;
  border-radius: 6px;
  transition: all 0.2s;
}

.class-tag:hover {
  transform: translateY(-1px);
}

.class-tag.active {
  background: linear-gradient(135deg, #67c23a 0%, #5daf34 100%);
  color: white;
  border-color: #67c23a;
  box-shadow: 0 2px 6px rgba(103, 194, 58, 0.3);
}

.canvas-area {
  flex: 0 0 45%;
  display: flex;
  flex-direction: column;
  min-width: 0;
  height: 100%;
}

.canvas-wrapper {
  flex: 1;
  display: flex;
  justify-content: center;
  align-items: center;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: inset 0 2px 10px rgba(0, 0, 0, 0.3);
}

.canvas-wrapper canvas {
  max-width: 100%;
  max-height: 100%;
  display: block;
  cursor: crosshair;
}

.canvas-controls {
  margin-top: 16px;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
}

.control-btn {
  border-radius: 8px;
  min-width: 100px;
}

.image-counter {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: 14px;
  color: #6b7280;
  font-weight: 500;
  background: white;
  padding: 8px 16px;
  border-radius: 8px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
}

.image-counter .current {
  color: #409eff;
  font-weight: 700;
  font-size: 16px;
}

.image-counter .separator {
  color: #d1d5db;
}

.image-counter .total {
  color: #9ca3af;
}

.annotation-item {
  padding: 12px;
  margin-bottom: 8px;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  background: #f9fafb;
  border: 1px solid #e5e7eb;
  transition: all 0.2s;
}

.annotation-item:hover {
  background: #f3f4f6;
  border-color: #d1d5db;
  transform: translateX(2px);
}

.annotation-item.selected {
  background: linear-gradient(135deg, #ecf5ff 0%, #e6f0fa 100%);
  border-color: #409eff;
  box-shadow: 0 2px 6px rgba(64, 158, 255, 0.2);
}

.annotation-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.class-name {
  font-weight: 600;
  color: #374151;
  font-size: 14px;
}

.confidence {
  font-size: 12px;
  color: #9ca3af;
}

.annotation-actions {
  display: flex;
  gap: 6px;
}

.annotation-actions .el-button {
  border-radius: 6px;
}

.label-selector {
  padding: 20px;
}

.label-selector :deep(.el-radio-button) {
  margin: 5px;
}
</style>
