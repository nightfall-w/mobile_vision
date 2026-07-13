<!-- src/components/Header.vue -->
<template>
  <el-header class="custom-header">
    <div class="header-container flex items-center justify-between">
      <!-- 左侧 Logo + 系统名称 -->
      <div class="flex items-center space-x-4">
        <!-- Logo 区域，建议用 200x50 尺寸更协调 -->
<!--        <el-image-->
<!--          :src=logo-->
<!--          alt="智能视觉平台"-->
<!--          :style="{ width: '160px', height: '40px' }"-->
<!--          class="cursor-pointer"-->
<!--          @click="goHome"-->
<!--        />-->
        <div class="system-title flex flex-col" @click="goHome">
          <span class="text-lg font-bold text-white">
            MobileVision
            <span class="text-yellow-300">智能视觉平台</span>
          </span>
          <span class="text-xs text-gray-300 mt-0.5">
            YOLO视觉识别 · 移动端UI自动化测试 · 智能Agent执行
          </span>
        </div>
      </div>

      <!-- 右侧用户操作区 -->
      <div class="flex items-center space-x-6 text-white">
        <!-- 用户信息 -->
        <div class="flex items-center space-x-2">
          <el-icon>
            <User/>
          </el-icon>
          <div class="flex flex-col">
            <span class="text-base font-medium">
              {{ username }}
            </span>
          </div>

          <!-- 下拉菜单 -->
          <el-dropdown
            trigger="click"
            @command="handleCommand"
            class="cursor-pointer"
            popper-class="user-dropdown-popper"
          >
            <el-icon class="text-xl" style="padding-right: 20px">
              <ArrowDown/>
            </el-icon>
            <template #dropdown>
              <el-dropdown-menu class="user-dropdown-menu">
                <div class="user-card">
                  <div class="user-avatar">
                    <el-icon :size="40">
                      <User/>
                    </el-icon>
                  </div>
                  <div class="user-info">
                    <div class="user-name">
                      {{ currentUser.nickname || currentUser.username || '未设置昵称' }}
                    </div>
                    <div class="user-username">@{{ currentUser.username || '未登录' }}</div>
                  </div>
                </div>
                <div class="user-details">
                  <div class="detail-item">
                    <el-icon>
                      <User/>
                    </el-icon>
                    <span>用户ID: {{ currentUser.id || '未获取' }}</span>
                  </div>
                  <div class="detail-item">
                    <el-icon>
                      <Message/>
                    </el-icon>
                    <span>{{ currentUser.email || '未设置邮箱' }}</span>
                  </div>
                  <div class="detail-item">
                    <el-icon>
                      <User/>
                    </el-icon>
                    <span>昵称: {{ currentUser.nickname || '未设置' }}</span>
                  </div>
                </div>
                <el-dropdown-item command="logout" divided>
                  <div class="logout-item">
                    <el-icon>
                      <SwitchButton/>
                    </el-icon>
                    <span>退出登录</span>
                  </div>
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>
    </div>
  </el-header>
</template>

<script setup>
import {ElImage, ElHeader, ElIcon} from 'element-plus'
import {ArrowDown, User, Message, SwitchButton} from '@element-plus/icons-vue'
import {onMounted, ref, reactive} from 'vue'
import router from "@/router"
import logo from '@/assets/logo.png'

// 用户名显示
const username = ref('未登录')

// 当前用户详细信息
const currentUser = reactive({
  id: '',
  username: '',
  nickname: '',
  email: ''
})

// 组件挂载时读取用户信息
onMounted(() => {
  loadUserInfo()
})

// 从 localStorage 加载用户信息
const loadUserInfo = () => {
  try {
    const currentUserJson = localStorage.getItem('currentUser')
    if (currentUserJson) {
      const user = JSON.parse(currentUserJson)
      // 更新 currentUser 对象
      Object.assign(currentUser, user)
      // 更新显示的用户名（优先显示昵称）
      username.value = user.nickname || user.username || '未登录'
    }
  } catch (error) {
    console.warn('读取用户信息失败:', error)
    username.value = '未登录'
  }
}

// 跳转首页
const goHome = () => {
  router.push('/')
}

// 处理下拉菜单事件
const handleCommand = (command) => {
  switch (command) {
    case 'logout':
      // 清除用户信息
      localStorage.removeItem('currentUser')
      // 重置用户信息
      Object.assign(currentUser, {
        id: '',
        username: '',
        nickname: '',
        email: ''
      })
      username.value = '未登录'
      // 跳转到登录页
      router.push('/login')
      break
  }
}

</script>

<style scoped>
.el-header {
  padding: 0 !important;
  height: 40px !important;
}

.custom-header {
  background: linear-gradient(120deg, #4b6ef7, #69c0ff);
  padding: 0;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 999;
}

.header-container {
  height: 40px;
}

.system-title {
  display: flex;
  flex-direction: column;
  justify-content: center;
  gap: 2px;
  height: 40px;
  margin-left: 10px;
}

.system-title span:first-child {
  font-size: 16px;
  letter-spacing: 1px;
  line-height: 1.3;
}

.system-title span:last-child {
  font-size: 10px;
  font-weight: 300;
  opacity: 0.9;
  line-height: 1.3;
  margin-top: 0 !important;
}

/* 用户下拉菜单样式 */
.user-dropdown-menu {
  padding: 0 !important;
  min-width: 280px !important;
  border-radius: 12px !important;
  overflow: hidden;
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.15) !important;
  border: none !important;
  animation: dropdownFadeIn 0.3s ease-out;
}

.user-card {
  padding: 15px;
  background: linear-gradient(120deg, #4b6ef7, #69c0ff);
  color: white;
  display: flex;
  align-items: center;
}

.user-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-right: 12px;
  flex-shrink: 0;
}

.user-info {
  flex: 1;
  overflow: hidden;
}

.user-name {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 4px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.user-username {
  font-size: 12px;
  opacity: 0.9;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.user-details {
  padding: 15px 20px;
}

.detail-item {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
  font-size: 13px;
  color: #666;
}

.detail-item:last-child {
  margin-bottom: 0;
}

.detail-item .el-icon {
  margin-right: 10px;
  font-size: 14px;
  color: #4b6ef7;
  flex-shrink: 0;
}

.detail-item span {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.logout-item {
  display: flex;
  align-items: center;
  color: #f56c6c;
}

.logout-item .el-icon {
  margin-right: 8px;
  flex-shrink: 0;
}

/* 下拉动画 */
.user-dropdown-popper {
  transform-origin: top right !important;
}

.user-dropdown-popper[x-placement^='bottom'] .el-popper__arrow {
  display: none;
}

/* 响应式优化 */
@media (max-width: 768px) {
  .system-title span:first-child {
    font-size: 0.875rem;
  }

  .system-title span:last-child {
    font-size: 0.625rem;
  }

  .user-dropdown-menu {
    min-width: 250px !important;
  }

  .el-header {
    height: 50px !important;
  }

  .header-container {
    height: 50px;
  }
}

/* 动画关键帧 */
@keyframes dropdownFadeIn {
  from {
    opacity: 0;
    transform: translateY(-10px) scale(0.95);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}
</style>
