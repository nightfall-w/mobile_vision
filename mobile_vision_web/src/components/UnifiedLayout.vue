<template>
  <div class="layout-root">
    <Header/>

    <div class="layout-body">
      <el-aside class="bg-white shadow-md layout-aside" :width="isCollapse ? '54px' : '160px'">
        <div class="menu-container">
            <el-menu
              :default-active="currentMenuIndex"
              class="el-menu-vertical-demo"
              :collapse="isCollapse"
              router
              background-color="#ffffff"
              text-color="#333333"
              active-text-color="#165DFF"
              :collapse-transition="false"
            >
            <template v-if="isInWorkspace">
              <el-menu-item :index="'/workspace/' + workspaceId">
                <el-icon class="text-lg">
                  <House/>
                </el-icon>
                <span v-if="!isCollapse">概览</span>
              </el-menu-item>

              <el-menu-item :index="'/workspace/' + workspaceId + '/testcases'">
                <el-icon class="text-lg">
                  <Document/>
                </el-icon>
                <span v-if="!isCollapse">用例管理</span>
              </el-menu-item>

              <el-menu-item :index="'/workspace/' + workspaceId + '/testplans'">
              <el-icon class="text-lg">
                <List/>
              </el-icon>
              <span v-if="!isCollapse">测试计划</span>
            </el-menu-item>

            <el-menu-item :index="'/workspace/' + workspaceId + '/testtasks'">
              <el-icon class="text-lg">
                <Expand/>
              </el-icon>
              <span v-if="!isCollapse">测试任务</span>
            </el-menu-item>


            </template>

            <template v-else>
              <el-menu-item index="/home">
                <el-icon class="text-lg">
                  <House/>
                </el-icon>
                <span v-if="!isCollapse">工作空间</span>
              </el-menu-item>

              <el-sub-menu index="yolo">
                <template #title>
                  <el-icon class="text-lg">
                    <Collection/>
                  </el-icon>
                  <span>YOLO训练</span>
                </template>
                <el-menu-item index="/yolo">
                  <el-icon class="text-lg"><FolderOpened/></el-icon>
                  <span>数据集</span>
                </el-menu-item>
                <el-menu-item index="/yolo/training">
                  <el-icon class="text-lg"><TrendCharts/></el-icon>
                  <span>训练任务</span>
                </el-menu-item>
                <el-menu-item index="/yolo/models">
                  <el-icon class="text-lg"><Cpu/></el-icon>
                  <span>模型管理</span>
                </el-menu-item>
              </el-sub-menu>

              <el-menu-item index="/devices">
                <el-icon class="text-lg">
                  <Monitor/>
                </el-icon>
                <span v-if="!isCollapse">设备管理</span>
              </el-menu-item>

              <el-menu-item index="/llm/credential">
                <el-icon class="text-lg">
                  <Collection/>
                </el-icon>
                <span v-if="!isCollapse">LLM凭证</span>
              </el-menu-item>

              <el-menu-item index="/system-config" v-if="isAdmin">
                <el-icon class="text-lg">
                  <Setting/>
                </el-icon>
                <span v-if="!isCollapse">系统设置</span>
              </el-menu-item>
            </template>
          </el-menu>
          </div>

        <div class="collapse-toggle" :class="{ 'collapsed': isCollapse }" @click="toggleCollapse">
          <el-icon :size="16">
            <Fold v-if="!isCollapse"/>
            <Expand v-else/>
          </el-icon>
          <span v-if="!isCollapse" class="collapse-text">收起侧边栏</span>
        </div>
        </el-aside>

        <el-main class="main-content">
          <div class="router-wrap">
            <router-view/>
          </div>
        </el-main>
    </div>
  </div>
</template>

<script setup>
import {ref, computed, onMounted, watch} from 'vue'
import {useRouter, useRoute} from 'vue-router'
import {
  House,
  Collection,
  Setting,
  Expand,
  Fold,
  Monitor,
  Document,
  List,
  FolderOpened,
  TrendCharts,
  Cpu
} from '@element-plus/icons-vue'
import Header from '@/components/Header.vue'


const isCollapse = ref(localStorage.getItem('sidebarCollapsed') === 'true')
const route = useRoute()
const router = useRouter()
const workspaceId = computed(() => {
  return route.params.id
})

const isAdmin = computed(() => {
  try {
    const currentUserJson = localStorage.getItem('currentUser')
    if (currentUserJson) {
      const currentUser = JSON.parse(currentUserJson)
      return currentUser.id === 0
    }
    return false
  } catch (e) {
    return false
  }
})

const isInWorkspace = computed(() => {
  return route.path.startsWith('/workspace/')
})

const currentMenuIndex = computed(() => {
  if (isInWorkspace.value) {
    return route.path
  }
  if (route.path === '/home' || route.path === '/') {
    return '/home'
  }
  return route.path
})

const toggleCollapse = () => {
  isCollapse.value = !isCollapse.value
  localStorage.setItem('sidebarCollapsed', isCollapse.value)
}
</script>

<style scoped>
.layout-root {
  height: 100vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.layout-body {
  flex: 1;
  display: flex;
  overflow: hidden;
  height: calc(100vh - 40px);
  padding-top: 40px;
  box-sizing: border-box;
}

.layout-aside {
  height: 100%;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  transition: width 0.2s ease;
}

.menu-container {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.el-menu-vertical-demo {
  width: 100%;
  flex: 1;
  border: none;
  overflow: hidden !important;
}

.el-menu-vertical-demo :deep(.el-scrollbar__wrap),
.el-menu-vertical-demo :deep(.el-scrollbar__view) {
  overflow: hidden !important;
}

.el-menu-vertical-demo :deep(.el-menu) {
  overflow: hidden !important;
}

.el-menu-vertical-demo .el-menu-item,
.el-menu-vertical-demo .el-sub-menu__title {
  font-size: 12px;
  height: 40px;
  line-height: 40px;
}

.el-menu-vertical-demo .el-menu-item .el-icon,
.el-menu-vertical-demo .el-sub-menu__title .el-icon {
  font-size: 14px;
}

.main-content {
  padding: 12px;
  background-color: #f5f5f5;
  overflow: hidden;
  height: 100%;
  flex: 1;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
}

.router-wrap {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.collapse-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  height: 44px;
  cursor: pointer;
  border-top: 1px solid #e8e8e8;
  flex-shrink: 0;
  color: #666;
  font-size: 13px;
  transition: background-color 0.15s;
}

.collapse-toggle:hover {
  background-color: #f0f2f5;
  color: #333;
}

.collapse-toggle.collapsed {
  flex-direction: column;
  gap: 0;
}

.el-menu--collapse .el-sub-menu__title span,
.el-menu--collapse .el-menu-item span {
  display: none;
}

.el-menu--collapse .el-sub-menu__title,
.el-menu--collapse .el-menu-item {
  text-align: center;
}

.el-menu--collapse .el-sub-menu__title .el-icon,
.el-menu--collapse .el-menu-item .el-icon {
  margin: 0 auto;
  width: 100%;
}
</style>
