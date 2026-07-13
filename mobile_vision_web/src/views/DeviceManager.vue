<template>
  <div class="device-manager">
    <!-- 固定区域：标题卡片 -->
    <div class="sticky-header">
      <div class="dm-header-card">
        <div class="dm-header-inner">
          <div class="dm-title-group">
            <div class="dm-icon-wrap"><el-icon :size="18"><Monitor /></el-icon></div>
            <div>
              <h1 class="dm-title">设备管理</h1>
              <p class="dm-subtitle">管理连接的移动设备</p>
            </div>
          </div>
          <div class="dm-header-actions">
            <button class="dm-btn dm-btn-ghost" @click="loadDevices" :disabled="loading">
              <el-icon :size="14"><Refresh /></el-icon> 刷新列表
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 滚动内容区域 -->
    <div class="scroll-content">
      <div class="device-grid">
        <div
          v-for="device in devices"
          :key="device.id"
          class="device-card bg-white rounded-2xl shadow-sm hover:shadow-lg transition-all duration-300 border border-gray-100 overflow-hidden"
        >
          <!-- 设备截图区域 -->
          <div class="screenshot-area relative" :class="{ 'is-connected': device.status === 'connected' }">
            <!-- 截图展示 -->
            <div class="screenshot-wrapper" @click="previewScreenshot(device)">
              <div v-if="device.screenshotLoading" class="screenshot-loading flex flex-col items-center justify-center">
                <el-icon class="is-loading text-white mb-2" :size="28"><Loading /></el-icon>
                <span class="text-white/70 text-xs">正在截取屏幕...</span>
              </div>
              <img
                v-else-if="device.screenshot"
                :src="device.screenshot"
                :alt="`${device.brand} ${device.model}`"
                class="screenshot-image cursor-pointer"
                @error="handleImageError(device)"
              />
              <div v-else class="screenshot-empty flex flex-col items-center justify-center">
                <el-icon :size="32" class="text-white/50 mb-2"><Monitor /></el-icon>
                <span class="text-white/50 text-xs">暂无屏幕截图</span>
              </div>
            </div>

            <!-- 状态标签 -->
            <div class="status-badge absolute top-3 right-3" :class="getStatusClass(device.status)">
              <span class="status-dot"></span>
              {{ getStatusText(device.status) }}
            </div>

            <!-- 刷新按钮 -->
            <el-button
              v-if="device.status === 'connected'"
              circle
              size="small"
              class="refresh-btn absolute top-3 left-3"
              @click.stop="refreshSingleScreenshot(device)"
            >
              <el-icon><Refresh /></el-icon>
            </el-button>
          </div>

          <!-- 设备信息区域 -->
          <div class="device-info-area p-4">
            <div class="device-title flex items-center mb-3">
              <div class="device-icon w-10 h-10 rounded-xl flex items-center justify-center mr-3" :style="{ background: getDeviceGradient(device.brand) }">
                <el-icon :size="20" class="text-white"><Iphone /></el-icon>
              </div>
              <div class="flex-1 min-w-0">
                <h3 class="font-bold text-gray-800 truncate">{{ device.brand }} {{ device.model }}</h3>
                <p class="text-xs text-gray-400 font-mono truncate">{{ device.id }}</p>
              </div>
            </div>

            <div class="info-grid">
              <div class="info-item">
                <div class="info-icon">
                  <el-icon><Cpu /></el-icon>
                </div>
                <div class="info-content">
                  <span class="info-label">{{ (device.system_type || 'android').charAt(0).toUpperCase() + (device.system_type || 'android').slice(1) }} 版本</span>
                  <span class="info-value">{{ device.android_version || '-' }}</span>
                </div>
              </div>
              <div class="info-item">
                <div class="info-icon">
                  <el-icon><FullScreen /></el-icon>
                </div>
                <div class="info-content">
                  <span class="info-label">分辨率</span>
                  <span class="info-value">{{ device.resolution || '-' }}</span>
                </div>
              </div>
              <div class="info-item info-item-full">
                <div class="info-icon">
                  <el-icon><Key /></el-icon>
                </div>
                <div class="info-content">
                  <span class="info-label">Android ID</span>
                  <span class="info-value font-mono truncate">{{ device.android_id || '-' }}</span>
                </div>
              </div>
            </div>

            <div class="device-actions mt-3">
              <el-button
                type="primary"
                size="small"
                @click="refreshDeviceInfo(device)"
                class="w-full action-btn"
                :loading="device.refreshing"
              >
                <el-icon><Refresh /></el-icon> 刷新设备信息
              </el-button>
            </div>
          </div>
        </div>

        <!-- 空状态 -->
        <div v-if="devices.length === 0 && !loading" class="empty-state bg-white rounded-xl p-12 text-center border border-gray-100">
          <div class="w-20 h-20 mx-auto mb-4 rounded-full bg-gray-100 flex items-center justify-center">
            <el-icon :size="40" class="text-gray-300">
              <Monitor />
            </el-icon>
          </div>
          <h3 class="text-gray-700 font-medium mb-2">未检测到设备</h3>
          <p class="text-gray-500 mb-4 text-sm">请确保设备已连接并开启USB调试模式</p>
          <el-button type="primary" @click="loadDevices">
            <el-icon><Refresh /></el-icon> 重试
          </el-button>
        </div>
      </div>
    </div>

    <!-- 图片预览组件 -->
    <div v-if="showImageViewer" class="image-viewer-mask" @click="closePreview">
      <el-image-viewer
        :url-list="[previewImage]"
        @close="closePreview"
        initial-index="0"
        @click.stop
      />
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import { ElMessage } from 'element-plus';
import { Refresh, Monitor, Loading, Iphone, Cpu, FullScreen, Key } from '@element-plus/icons-vue';
import {
  getDeviceList,
  refreshDevice as refreshDeviceApi
} from '@/network/api.js';
import axios from 'axios';

const devices = ref([]);
const loading = ref(false);
let refreshInterval = null;

const previewImage = ref('');
const showImageViewer = ref(false);

// 状态文本映射
const getStatusText = (status) => {
  const statusMap = {
    'connected': '已连接',
    'offline': '离线',
    'disconnected': '未连接'
  };
  return statusMap[status] || status;
};

// 状态样式类映射
const getStatusClass = (status) => {
  const classMap = {
    'connected': 'status-connected',
    'offline': 'status-offline',
    'disconnected': 'status-disconnected'
  };
  return classMap[status] || 'status-disconnected';
};

// 设备品牌渐变色映射
const getDeviceGradient = (brand) => {
  const gradientMap = {
    'Xiaomi': 'linear-gradient(135deg, #ff6b35 0%, #f7931a 100%)',
    'Redmi': 'linear-gradient(135deg, #ff6b35 0%, #f7931a 100%)',
    'POCO': 'linear-gradient(135deg, #ff6b35 0%, #f7931a 100%)',
    'Samsung': 'linear-gradient(135deg, #1428a0 0%, #3d84e8 100%)',
    'Huawei': 'linear-gradient(135deg, #cf0a2c 0%, #ff4500 100%)',
    'OPPO': 'linear-gradient(135deg, #00b9f2 0%, #007bff 100%)',
    'vivo': 'linear-gradient(135deg, #1a1a1a 0%, #4a4a4a 100%)',
    'OnePlus': 'linear-gradient(135deg, #f5010c 0%, #e60012 100%)',
    'Realme': 'linear-gradient(135deg, #f9b208 0%, #f96b0a 100%)',
    'Meizu': 'linear-gradient(135deg, #00a1e0 0%, #0070c0 100%)',
    'Sony': 'linear-gradient(135deg, #000000 0%, #4a4a4a 100%)',
    'Google': 'linear-gradient(135deg, #4285f4 0%, #34a853 100%)',
    'default': 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)'
  };
  return gradientMap[brand] || gradientMap['default'];
};

// 加载设备列表
const loadDevices = async () => {
  if (loading.value) return;
  loading.value = true;
  try {
    const resp = await getDeviceList();
    if (resp.code === 0) {
      // 保留已有设备的截图 URL，避免闪烁
      const existingScreenshots = {};
      devices.value.forEach(d => {
        if (d.screenshot) {
          existingScreenshots[d.id] = d.screenshot;
        }
      });

      // 映射新数据
      const newDevices = resp.data.map(device => ({
        ...device,
        screenshot: existingScreenshots[device.id] || null,
        screenshotLoading: false,
        refreshing: false
      }));

      devices.value = newDevices;

      // 为所有已连接且没有截图的设备自动获取截图
      for (const device of devices.value) {
        if (device.status === 'connected' && !device.screenshot) {
          // 异步执行，不阻塞列表加载
          refreshSingleScreenshot(device);
        }
      }
    } else {
      ElMessage.error(resp.msg || '获取设备列表失败');
    }
  } catch (error) {
    console.error('加载设备列表异常:', error);
    ElMessage.error('网络请求失败');
  } finally {
    loading.value = false;
  }
};

// 刷新单个设备信息
const refreshDeviceInfo = async (device) => {
  const index = devices.value.findIndex(d => d.id === device.id);
  if (index === -1) return;

  // 设置加载状态
  devices.value[index].refreshing = true;

  try {
    const resp = await refreshDeviceApi(device.id);
    if (resp.code === 0) {
      // 更新设备信息，保留截图
      devices.value[index] = {
        ...resp.data,
        screenshot: devices.value[index].screenshot,
        screenshotLoading: false,
        refreshing: false
      };
      ElMessage.success('设备信息已更新');

      // 顺便刷新截图
      await refreshSingleScreenshot(devices.value[index]);
    } else {
      throw new Error(resp.msg || '刷新失败');
    }
  } catch (error) {
    console.error('刷新设备信息失败:', error);
    ElMessage.error('刷新设备信息失败');
    devices.value[index].refreshing = false;
  }
};

// 刷新单个截图
const refreshSingleScreenshot = async (device) => {
  const index = devices.value.findIndex(d => d.id === device.id);
  if (index === -1) return;

  devices.value[index].screenshotLoading = true;

  try {
    const serverUrl = import.meta.env.VITE_APP_SERVER_URL;
    const token = JSON.parse(localStorage.getItem('currentUser') || '{}');
    const authHeader = token.token_type + ' ' + token.access_token;

    const response = await axios.get(
      `${serverUrl}/api/v1/device/screenshot/${device.id}`,
      {
        responseType: 'arraybuffer',
        headers: {
          'Authorization': authHeader,
          'Accept': 'image/png, image/jpeg, */*'
        }
      }
    );

    const arrayBuffer = response.data;
    if (!(arrayBuffer instanceof ArrayBuffer)) {
      throw new Error("响应不是 ArrayBuffer 类型");
    }

    const blob = new Blob([arrayBuffer], { type: 'image/png' });
    const url = URL.createObjectURL(blob);
    const currentDevice = devices.value[index];

    if (currentDevice.screenshot && currentDevice.screenshot.startsWith('blob:')) {
      URL.revokeObjectURL(currentDevice.screenshot);
    }

    devices.value[index] = {
      ...currentDevice,
      screenshot: url,
      screenshotLoading: false
    };

  } catch (error) {
    console.error('[截图失败]', error);
    if (devices.value[index]) {
      devices.value[index].screenshotLoading = false;
    }
  }
};

// 预览截图
const previewScreenshot = (device) => {
  if (device.screenshot && !device.screenshotLoading) {
    previewImage.value = device.screenshot;
    showImageViewer.value = true;
  }
};

// 关闭预览
const closePreview = () => {
  showImageViewer.value = false;
};

// ESC键关闭预览
const handleKeydown = (e) => {
  if (e.key === 'Escape' && showImageViewer.value) {
    closePreview();
  }
};

// 图片加载错误处理
const handleImageError = (device) => {
  console.warn(`[图片加载失败] 设备 ${device.id} 的截图 URL 无效`);
  // 可以选择清除无效 URL
  const index = devices.value.findIndex(d => d.id === device.id);
  if (index !== -1) {
     if (devices.value[index].screenshot?.startsWith('blob:')) {
        URL.revokeObjectURL(devices.value[index].screenshot);
     }
     devices.value[index].screenshot = null;
  }
};

// 生命周期钩子
onMounted(() => {
  loadDevices();
  // 每 5 秒刷新一次设备列表状态（频率降低以减少性能消耗）
  refreshInterval = setInterval(() => {
    loadDevices();
  }, 5000);
  // 监听ESC键关闭预览
  document.addEventListener('keydown', handleKeydown);
});

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval);
  }
  // 清理所有 Blob URL
  devices.value.forEach(device => {
    if (device.screenshot && device.screenshot.startsWith('blob:')) {
      URL.revokeObjectURL(device.screenshot);
    }
  });
  // 移除ESC键监听
  document.removeEventListener('keydown', handleKeydown);
});
</script>

<style scoped>
.device-manager {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  background-color: transparent;
}

.sticky-header {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 16px;
  position: sticky;
  top: 0;
  z-index: 100;
  background-color: #f5f5f5;
  padding-bottom: 16px;
}

.scroll-content {
  flex: 1;
  overflow-y: auto;
}

.page-container {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* 页面标题卡片样式 */
.dm-header-card { background: #fff; border-radius: 12px; border: 1px solid #e8e8e8; }
.dm-header-inner { display: flex; justify-content: space-between; align-items: center; padding: 14px 18px; }
.dm-title-group { display: flex; align-items: center; gap: 12px; }
.dm-icon-wrap { width: 36px; height: 36px; border-radius: 10px; background: #eef2ff; color: #5b6ef7; display: flex; align-items: center; justify-content: center; flex-shrink: 0; }
.dm-title { margin: 0; font-size: 17px; font-weight: 700; color: #1d1d1f; }
.dm-subtitle { margin: 2px 0 0; font-size: 12px; color: #8e8e93; }
.dm-header-actions { display: flex; gap: 8px; }

.dm-btn { display: inline-flex; align-items: center; gap: 5px; border: none; border-radius: 8px; font-size: 13px; font-weight: 500; cursor: pointer; padding: 7px 14px; transition: all 0.15s ease; }
.dm-btn-ghost { background: transparent; color: #505050; border: 1px solid #d1d5db; }
.dm-btn-ghost:hover { background: #f0f0f0; }
.dm-btn:disabled { opacity: 0.5; cursor: not-allowed; }

.device-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
  flex: 1;
  overflow-y: auto;
  padding: 4px;
}

/* 设备卡片 */
.device-card {
  display: flex;
  flex-direction: column;
  background: white;
  align-self: flex-start;
}

/* 截图区域 */
.screenshot-area {
  position: relative;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
}

.screenshot-area.is-connected {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
}

/* 截图容器 */
.screenshot-wrapper {
  width: 100%;
  height: 280px;
  background: #000;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
}

.screenshot-image {
  width: 100%;
  height: 100%;
  object-fit: contain;
}

.screenshot-loading,
.screenshot-empty {
  width: 100%;
  height: 100%;
  background: #000;
}

/* 状态徽章 */
.status-badge {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 20px;
  font-size: 11px;
  font-weight: 600;
  backdrop-filter: blur(10px);
  gap: 5px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.status-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.status-badge.status-connected {
  background: rgba(34, 197, 94, 0.9);
  color: white;
}

.status-badge.status-connected .status-dot {
  background: white;
}

.status-badge.status-offline {
  background: rgba(239, 68, 68, 0.9);
  color: white;
}

.status-badge.status-offline .status-dot {
  background: white;
}

.status-badge.status-disconnected {
  background: rgba(156, 163, 175, 0.9);
  color: white;
}

.status-badge.status-disconnected .status-dot {
  background: white;
  animation: none;
}

/* 刷新按钮 */
.refresh-btn {
  background: rgba(255, 255, 255, 0.2) !important;
  border: none !important;
  backdrop-filter: blur(10px);
  color: white !important;
  width: 36px !important;
  height: 36px !important;
  min-width: 36px !important;
  padding: 0 !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  flex-shrink: 0 !important;
  margin: 0 !important;
}

.refresh-btn:hover {
  background: rgba(255, 255, 255, 0.3) !important;
}

.refresh-btn .el-icon {
  line-height: 1;
}

/* 设备信息区域 */
.device-info-area {
  padding: 12px 12px 8px;
  background: white;
}

/* 设备标题 */
.device-title {
  margin-bottom: 16px;
}

.device-icon {
  flex-shrink: 0;
}

/* 信息网格 */
.info-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

.info-item {
  display: flex;
  align-items: center;
  padding: 8px 10px;
  background: #f8f9fa;
  border-radius: 8px;
  gap: 8px;
}

.info-item-full {
  grid-column: 1 / -1;
}

.info-icon {
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: white;
  border-radius: 6px;
  color: #667eea;
  font-size: 14px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.08);
}

.info-content {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
}

.info-label {
  font-size: 10px;
  color: #9ca3af;
  text-transform: uppercase;
  letter-spacing: 0.3px;
}

.info-value {
  font-size: 12px;
  font-weight: 600;
  color: #374151;
}

/* 操作按钮 */
.action-btn {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
  border: none !important;
  font-weight: 500;
}

.action-btn:hover {
  background: linear-gradient(135deg, #5a6fd6 0%, #6a4190 100%) !important;
}

/* 图片预览遮罩 */
.image-viewer-mask {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.9);
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.image-viewer-mask :deep(.el-image-viewer__wrapper) {
  cursor: default;
}

/* 隐藏底部操作按钮 */
.image-viewer-mask :deep(.el-image-viewer__actions) {
  display: none !important;
}

/* 关闭按钮样式 - 白色背景形成反差 */
.image-viewer-mask :deep(.el-image-viewer__close) {
  width: 56px !important;
  height: 56px !important;
  border-radius: 50% !important;
  background: #fff !important;
  color: #333 !important;
  font-size: 24px !important;
  font-weight: bold !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  transition: all 0.3s ease !important;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3) !important;
}

.image-viewer-mask :deep(.el-image-viewer__close:hover) {
  background: #f5f5f5 !important;
  transform: scale(1.1);
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.4) !important;
}

/* 空状态 */
.empty-state {
  grid-column: 1 / -1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: white;
}
</style>
