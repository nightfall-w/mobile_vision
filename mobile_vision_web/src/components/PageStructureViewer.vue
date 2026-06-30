<template>
  <div class="page-structure-viewer" v-if="pageData">
    <div class="container" :class="{ 'in-overlay': inOverlay }">
      <canvas ref="canvasRef" @click="openOverlay" @mousemove="onMouseMove" @mouseleave="onMouseLeave"></canvas>
      <div ref="tooltipRef" class="tooltip" :style="tooltipStyle" v-show="tooltipVisible">
        <div class="row"><span class="label">ID</span> <span class="value">{{ tooltipData.id }}</span></div>
        <div class="row"><span class="label">类型</span> <span class="value highlight">{{ tooltipData.type }}</span></div>
        <div class="row"><span class="label">文本</span> <span class="value">{{ tooltipData.text || '（无）' }}</span></div>
        <div class="row"><span class="label">置信度</span> <span class="value">{{ tooltipData.confidence }}%</span></div>
        <div class="row"><span class="label">颜色</span> <span class="value">{{ tooltipData.color || '无' }}</span></div>
      </div>
      <div class="info-panel" v-if="!inOverlay">
        <div class="legend">
          <div v-for="t in typeOrder" :key="t" class="legend-item">
            <div class="legend-color" :style="{ background: getTypeColor(t) }"></div>
            <span>{{ getTypeLabel(t) }}</span>
          </div>
        </div>
        <div class="stats">{{ statsText }}</div>
        <button @click="toggleLabels">{{ showLabels ? '隐藏文字标签' : '显示文字标签' }}</button>
      </div>
    </div>

    <!-- Fullscreen overlay -->
    <Teleport to="body">
      <div v-if="showOverlay" class="overlay-backdrop" @click.self="closeOverlay">
        <div class="overlay-container">
          <button class="overlay-close" @click="closeOverlay">&times;</button>
          <canvas ref="overlayCanvasRef" @mousemove="onOverlayMouseMove" @mouseleave="onOverlayMouseLeave"></canvas>
          <div ref="overlayTooltipRef" class="tooltip" :style="overlayTooltipStyle" v-show="overlayTooltipVisible">
            <div class="row"><span class="label">ID</span> <span class="value">{{ overlayTooltipData.id }}</span></div>
            <div class="row"><span class="label">类型</span> <span class="value highlight">{{ overlayTooltipData.type }}</span></div>
            <div class="row"><span class="label">文本</span> <span class="value">{{ overlayTooltipData.text || '（无）' }}</span></div>
            <div class="row"><span class="label">置信度</span> <span class="value">{{ overlayTooltipData.confidence }}%</span></div>
            <div class="row"><span class="label">颜色</span> <span class="value">{{ overlayTooltipData.color || '无' }}</span></div>
          </div>
          <div class="overlay-footer">
            <div class="legend">
              <div v-for="t in typeOrder" :key="t" class="legend-item">
                <div class="legend-color" :style="{ background: getTypeColor(t) }"></div>
                <span>{{ getTypeLabel(t) }}</span>
              </div>
            </div>
            <div class="stats">{{ statsText }}</div>
            <button @click="toggleLabels">{{ showLabels ? '隐藏文字标签' : '显示文字标签' }}</button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'

const props = defineProps({
  pageData: { type: Object, default: null }
})

const canvasRef = ref(null)
const tooltipRef = ref(null)
const overlayCanvasRef = ref(null)
const overlayTooltipRef = ref(null)
const showLabels = ref(true)
const tooltipVisible = ref(false)
const tooltipData = ref({ id: '', type: '', text: '', confidence: '', color: '' })
const tooltipStyle = ref({ left: '0px', top: '0px' })
const overlayTooltipVisible = ref(false)
const overlayTooltipData = ref({ id: '', type: '', text: '', confidence: '', color: '' })
const overlayTooltipStyle = ref({ left: '0px', top: '0px' })
const showOverlay = ref(false)

const inOverlay = ref(false)

// Track logical canvas dimensions for mouse coordinate mapping
const logicalSize = ref({ w: 1, h: 1 })

function hashCode(str) {
  let hash = 0
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i)
    hash = (hash << 5) - hash + char
    hash |= 0
  }
  return Math.abs(hash)
}

function getTypeColor(type) {
  const hue = hashCode(type || 'unknown') % 360
  const sat = 60 + (hashCode(type + 's') % 20)
  const lig = 50 + (hashCode(type + 'l') % 20)
  return `hsl(${hue}, ${sat}%, ${lig}%)`
}

function getTypeLabel(type) {
  if (!type) return '未知'
  return type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
}

function getTextColor(colorName) {
  if (!colorName) return '#0f172a'
  const map = {
    white: '#ffffff', black: '#000000', dark_gray: '#555555',
    gray: '#888888', light_gray: '#cccccc', light: '#dddddd',
    red: '#e74c3c', blue: '#2980b9', green: '#27ae60', yellow: '#f1c40f'
  }
  return map[colorName.toLowerCase()] || '#0f172a'
}

const flatElements = computed(() => {
  if (!props.pageData?.elements) return []
  const result = []
  const childIds = new Set()

  function flatten(node, parentId) {
    if (!node) return
    const bbox = node.bbox
    if (bbox && bbox.length === 4) {
      result.push({
        id: node.id,
        type: node.type || 'unknown',
        text: node.text || '',
        confidence: node.confidence || 0,
        color: node.color || '',
        x1: bbox[0], y1: bbox[1], x2: bbox[2], y2: bbox[3],
        parentId,
        hasChildren: !!(node.children && node.children.length > 0),
        _child: parentId != null
      })
      if (parentId != null) childIds.add(node.id)
    }
    if (node.children && Array.isArray(node.children)) {
      for (const child of node.children) flatten(child, node.id)
    }
  }

  for (const el of props.pageData.elements) flatten(el, null)
  // mark child status
  for (const el of result) {
    if (childIds.has(el.id)) el._child = true
  }
  return result
})

const typeOrder = computed(() => {
  const set = new Set()
  const order = []
  for (const el of flatElements.value) {
    if (!set.has(el.type)) {
      set.add(el.type)
      order.push(el.type)
    }
  }
  return order
})

const statsText = computed(() => {
  const total = flatElements.value.length
  const textCount = flatElements.value.filter(el => el.type === 'text_block').length
  return `${total} 组件 · ${textCount} 文字`
})

function draw() {
  drawToCanvas(canvasRef.value)
}

function drawToCanvas(canvas) {
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  const els = flatElements.value
  if (!els.length) return

  const { image_width, image_height } = props.pageData
  const PAD = 40
  let maxX = image_width
  let maxY = image_height
  for (const el of els) {
    maxX = Math.max(maxX, el.x2)
    maxY = Math.max(maxY, el.y2)
  }

  const dpr = window.devicePixelRatio || 1
  let cw = Math.ceil(maxX) + PAD
  let ch = Math.ceil(maxY) + PAD

  canvas.width = cw * dpr
  canvas.height = ch * dpr
  ctx.scale(dpr, dpr)

  // Cap display width to 300px for inline view
  if (canvas === canvasRef.value && cw > 300) {
    const ratio = 300 / cw
    canvas.style.width = '300px'
    canvas.style.height = Math.round(ch * ratio) + 'px'
  } else if (canvas === overlayCanvasRef.value) {
    // Overlay: fit within viewport (both dimensions)
    const overlayPad = 160 // footer + container padding + margins
    const maxW = window.innerWidth * 0.85
    const maxH = window.innerHeight - overlayPad
    let ratio = 1
    if (ch > maxH) ratio = Math.min(ratio, maxH / ch)
    if (cw > maxW) ratio = Math.min(ratio, maxW / cw)
    if (ratio < 1) {
      canvas.style.width = Math.round(cw * ratio) + 'px'
      canvas.style.height = Math.round(ch * ratio) + 'px'
    } else {
      canvas.style.width = cw + 'px'
      canvas.style.height = ch + 'px'
    }
  } else {
    canvas.style.width = cw + 'px'
    canvas.style.height = ch + 'px'
  }

  // Save logical size for mouse coordinate mapping
  if (canvas === canvasRef.value) {
    logicalSize.value = { w: cw, h: ch }
  }
  if (canvas === overlayCanvasRef.value) {
    logicalSize.value = { w: cw, h: ch }
  }

  // Background
  ctx.fillStyle = '#f8f9fc'
  ctx.fillRect(0, 0, cw, ch)

  // Grid
  ctx.save()
  ctx.strokeStyle = '#e2e8f0'
  ctx.lineWidth = 0.5
  for (let i = 0; i < cw; i += 50) {
    ctx.beginPath(); ctx.moveTo(i, 0); ctx.lineTo(i, ch); ctx.stroke()
    ctx.beginPath(); ctx.moveTo(0, i); ctx.lineTo(cw, i); ctx.stroke()
  }
  ctx.restore()

  // Draw elements
  for (const el of els) {
    const color = getTypeColor(el.type)
    const w = el.x2 - el.x1
    const h = el.y2 - el.y1

    // Fill
    ctx.save()
    ctx.globalAlpha = 0.25
    ctx.fillStyle = color
    ctx.fillRect(el.x1, el.y1, w, h)
    ctx.restore()

    // Border
    ctx.save()
    if (el._child) {
      ctx.setLineDash([4, 5])
      ctx.lineWidth = 1.8
    } else if (el.hasChildren) {
      ctx.setLineDash([6, 4])
      ctx.lineWidth = 2.2
    } else {
      ctx.setLineDash([])
      ctx.lineWidth = 1.8
    }
    ctx.strokeStyle = color
    ctx.strokeRect(el.x1, el.y1, w, h)
    ctx.restore()

    // Type abbreviation
    ctx.save()
    ctx.font = "bold 11px 'Segoe UI', sans-serif"
    ctx.fillStyle = '#2d3748'
    const short = el.type ? el.type.substring(0, 3).toUpperCase() : '???'
    ctx.fillText(short, el.x1 + 4, el.y1 + 16)
    ctx.restore()

    // Low confidence
    if (el.confidence > 0 && el.confidence < 0.5) {
      ctx.save()
      ctx.setLineDash([3, 4])
      ctx.strokeStyle = '#ef4444'
      ctx.lineWidth = 1.2
      ctx.strokeRect(el.x1, el.y1, w, h)
      ctx.font = "10px monospace"
      ctx.fillStyle = '#ef4444'
      ctx.fillText(`conf:${(el.confidence * 100).toFixed(1)}%`, el.x1 + 2, el.y2 - 4)
      ctx.restore()
    }
  }

  // Text labels
  if (showLabels.value) {
    for (const el of els) {
      let label = el.text || getTypeLabel(el.type)
      if (!label) continue
      const cx = (el.x1 + el.x2) / 2
      const cy = (el.y1 + el.y2) / 2
      ctx.save()
      ctx.font = "bold 14px 'Segoe UI', 'PingFang SC', 'Microsoft YaHei', sans-serif"
      const metrics = ctx.measureText(label)
      const tw = metrics.width
      const th = 20

      ctx.fillStyle = 'rgba(255,255,240,0.9)'
      ctx.shadowColor = 'rgba(0,0,0,0.1)'
      ctx.shadowBlur = 6
      ctx.fillRect(cx - tw / 2 - 6, cy - th / 2 - 4, tw + 12, th + 8)
      ctx.shadowBlur = 0

      ctx.fillStyle = getTextColor(el.color)
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.fillText(label, cx, cy + 1)
      ctx.restore()
    }
  }

  // Dimension label
  ctx.save()
  ctx.font = "11px monospace"
  ctx.fillStyle = 'rgba(0,0,0,0.2)'
  ctx.textAlign = 'right'
  ctx.textBaseline = 'bottom'
  ctx.fillText(`${image_width} × ${image_height}`, cw - 10, ch - 6)
  ctx.restore()
}

// Hover tooltip
function onMouseMove(e) {
  const canvas = canvasRef.value
  if (!canvas) return
  const rect = canvas.getBoundingClientRect()
  const scaleX = logicalSize.value.w / rect.width
  const scaleY = logicalSize.value.h / rect.height
  const mouseX = (e.clientX - rect.left) * scaleX
  const mouseY = (e.clientY - rect.top) * scaleY

  const els = flatElements.value
  let found = null
  // 从后往前遍历，子元素（更小、更上层）优先匹配
  for (let i = els.length - 1; i >= 0; i--) {
    const el = els[i]
    if (mouseX >= el.x1 && mouseX <= el.x2 && mouseY >= el.y1 && mouseY <= el.y2) {
      found = el
      break
    }
  }

  if (found) {
    tooltipData.value = {
      id: found.id || '无ID',
      type: found.type,
      text: found.text || '（无文本）',
      confidence: (found.confidence * 100).toFixed(1),
      color: found.color || '无'
    }
    let left = e.clientX + 15
    let top = e.clientY + 15
    if (left + 300 > window.innerWidth) left = e.clientX - 300 - 15
    if (top + 150 > window.innerHeight) top = e.clientY - 150 - 15
    if (left < 10) left = 10
    if (top < 10) top = 10
    tooltipStyle.value = { left: left + 'px', top: top + 'px' }
    tooltipVisible.value = true
    canvas.style.cursor = 'pointer'
  } else {
    tooltipVisible.value = false
    canvas.style.cursor = 'crosshair'
  }
}

function onMouseLeave() {
  tooltipVisible.value = false
}

function onOverlayMouseMove(e) {
  const canvas = overlayCanvasRef.value
  if (!canvas) return
  const rect = canvas.getBoundingClientRect()
  const scaleX = logicalSize.value.w / rect.width
  const scaleY = logicalSize.value.h / rect.height
  const mouseX = (e.clientX - rect.left) * scaleX
  const mouseY = (e.clientY - rect.top) * scaleY

  const els = flatElements.value
  let found = null
  // 从后往前遍历，子元素（更小、更上层）优先匹配
  for (let i = els.length - 1; i >= 0; i--) {
    const el = els[i]
    if (mouseX >= el.x1 && mouseX <= el.x2 && mouseY >= el.y1 && mouseY <= el.y2) {
      found = el
      break
    }
  }

  if (found) {
    overlayTooltipData.value = {
      id: found.id || '无ID',
      type: found.type,
      text: found.text || '（无文本）',
      confidence: (found.confidence * 100).toFixed(1),
      color: found.color || '无'
    }
    let left = e.clientX + 15
    let top = e.clientY + 15
    if (left + 300 > window.innerWidth) left = e.clientX - 300 - 15
    if (top + 150 > window.innerHeight) top = e.clientY - 150 - 15
    if (left < 10) left = 10
    if (top < 10) top = 10
    overlayTooltipStyle.value = { left: left + 'px', top: top + 'px' }
    overlayTooltipVisible.value = true
    canvas.style.cursor = 'pointer'
  } else {
    overlayTooltipVisible.value = false
    canvas.style.cursor = 'crosshair'
  }
}

function onOverlayMouseLeave() {
  overlayTooltipVisible.value = false
}

function toggleLabels() {
  showLabels.value = !showLabels.value
  requestAnimationFrame(() => {
    draw()
    if (overlayCanvasRef.value) drawToCanvas(overlayCanvasRef.value)
  })
}

function openOverlay() {
  showOverlay.value = true
  inOverlay.value = true
  // Wait for DOM, then draw on overlay canvas
  requestAnimationFrame(() => {
    const canvas = overlayCanvasRef.value
    if (!canvas) return
    drawToCanvas(canvas)
  })
}

function closeOverlay() {
  showOverlay.value = false
  inOverlay.value = false
}

onMounted(() => {
  draw()
})

watch(() => props.pageData, () => {
  draw()
}, { deep: true })
</script>

<style scoped>
.page-structure-viewer {
  margin-top: 8px;
  display: flex;
  justify-content: center;
}

.container {
  background: #fff;
  border-radius: 24px;
  box-shadow: 0 20px 35px rgba(0, 0, 0, 0.5);
  padding: 16px;
  overflow-x: auto;
  overflow-y: auto;
  max-width: 300px;
  max-height: 96vh;
  position: relative;
}

canvas {
  display: block;
  margin: 0 auto;
  border-radius: 16px;
  background-color: #f8f9fc;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  cursor: crosshair;
}


.tooltip {
  position: fixed;
  pointer-events: none;
  background: rgba(30, 30, 50, 0.92);
  color: #eee;
  padding: 12px 16px;
  border-radius: 12px;
  font-size: 13px;
  line-height: 1.6;
  font-family: 'Segoe UI', 'PingFang SC', sans-serif;
  box-shadow: 0 8px 30px rgba(0, 0, 0, 0.6);
  border: 1px solid rgba(255, 255, 255, 0.15);
  max-width: 360px;
  backdrop-filter: blur(4px);
  z-index: 9999;
  transition: opacity 0.1s;
}

.tooltip .label {
  color: #99aabb;
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.tooltip .value {
  color: #fff;
  font-weight: 500;
  word-break: break-all;
}

.tooltip .row {
  margin: 4px 0;
}

.tooltip .highlight {
  color: #ffd866;
}

.info-panel {
  margin-top: 16px;
  background: #f1f3f7;
  border-radius: 20px;
  padding: 12px 20px;
  font-size: 14px;
  color: #1e2a3a;
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  align-items: center;
  justify-content: space-between;
}

.legend {
  display: flex;
  gap: 18px;
  flex-wrap: wrap;
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
}

.legend-color {
  width: 18px;
  height: 18px;
  border-radius: 4px;
  border: 1px solid rgba(0, 0, 0, 0.1);
  flex-shrink: 0;
}

.stats {
  font-family: monospace;
  background: #e9ecef;
  padding: 6px 16px;
  border-radius: 40px;
  font-size: 13px;
  white-space: nowrap;
}

button {
  background: #2c7be5;
  border: none;
  color: white;
  padding: 6px 16px;
  border-radius: 30px;
  cursor: pointer;
  font-weight: 500;
  transition: 0.2s;
  font-size: 13px;
}

button:hover {
  background: #1f5faf;
}

@media (max-width: 760px) {
  .info-panel {
    flex-direction: column;
    align-items: flex-start;
  }
}

/* Overlay backdrop */
.overlay-backdrop {
  position: fixed;
  top: 0;
  left: 0;
  width: 100vw;
  height: 100vh;
  background: rgba(0, 0, 0, 0.75);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10000;
}

.overlay-container {
  background: #fff;
  border-radius: 24px;
  padding: 24px;
  max-width: 95vw;
  max-height: 95vh;
  overflow: auto;
  position: relative;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
  display: flex;
  flex-direction: column;
  align-items: center;
}

.overlay-close {
  position: absolute;
  top: 8px;
  right: 16px;
  background: none;
  border: none;
  font-size: 32px;
  color: #666;
  cursor: pointer;
  z-index: 10;
  line-height: 1;
  padding: 0 8px;
}

.overlay-close:hover {
  color: #000;
}

.overlay-footer {
  margin-top: 16px;
  background: #f1f3f7;
  border-radius: 20px;
  padding: 12px 20px;
  font-size: 14px;
  color: #1e2a3a;
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  align-items: center;
  justify-content: space-between;
}
</style>
