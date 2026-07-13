// src/router/index.js
import {createRouter, createWebHistory} from 'vue-router'
import Home from '@/views/Home.vue';
import Login from '@/views/Login.vue';
import WorkspaceDetail from '@/views/WorkspaceDetail.vue';
import UnifiedLayout from '@/components/UnifiedLayout.vue';
import SystemConfig from '@/views/SystemConfig.vue'

import TestCaseManagement from '@/views/TestCaseManagement.vue'
import TestCaseForm from '@/views/TestCaseForm.vue'

import YoloDatasets from '@/views/YoloDatasets.vue'
import YoloTraining from '@/views/YoloTraining.vue'
import YoloAnnotation from '@/views/YoloAnnotation.vue'
import DeviceManager from '@/views/DeviceManager.vue'
import LLMCredential from '@/views/LLMCredential.vue'
import TaskExecutionMonitor from '@/views/TaskExecutionMonitor.vue'
import TestPlanManagement from '@/views/TestPlanManagement.vue'
import TestTaskList from '@/views/TestTaskList.vue'
import JobMonitor from '@/views/JobMonitor.vue'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: Login
  },
  {
    path: '/',
    redirect: '/home'
  },
  {
    path: '/home',
    component: UnifiedLayout,
    children: [
      {
        path: '',
        name: 'Home',
        component: Home,
        meta: {requiresAuth: true}
      }
    ]
  },
  {
    path: '/system-config',
    component: UnifiedLayout,
    children: [
      {
        path: '',
        name: 'SystemConfig',
        component: SystemConfig,
        meta: {requiresAuth: true}
      }
    ]
  },
  {
    path: '/yolo',
    component: UnifiedLayout,
    children: [
      {
        path: '',
        name: 'YoloDatasets',
        component: YoloDatasets,
        meta: {requiresAuth: true}
      }
    ]
  },
  {
    path: '/yolo/training',
    component: UnifiedLayout,
    children: [
      {
        path: '',
        name: 'YoloTraining',
        component: YoloTraining,
        meta: {requiresAuth: true}
      }
    ]
  },
  {
    path: '/yolo/models',
    redirect: '/yolo/training?tab=models'
  },
  {
    path: '/yolo/annotation/:datasetId',
    component: UnifiedLayout,
    children: [
      {
        path: '',
        name: 'YoloAnnotation',
        component: YoloAnnotation,
        meta: {requiresAuth: true},
        props: true
      }
    ]
  },
  {
    path: '/devices',
    component: UnifiedLayout,
    children: [
      {
        path: '',
        name: 'DeviceManager',
        component: DeviceManager,
        meta: {requiresAuth: true}
      }
    ]
  },
  {
    path: '/llm/credential',
    component: UnifiedLayout,
    children: [
      {
        path: '',
        name: 'LLMCredential',
        component: LLMCredential,
        meta: {requiresAuth: true}
      }
    ]
  },
  {
    path: '/workspace/:id',
    component: UnifiedLayout,
    children: [
      {
        path: '',
        name: 'WorkspaceDetail',
        component: WorkspaceDetail,
        meta: {requiresAuth: true},
        props: true
      },

      {
        path: 'testcases',
        name: 'TestCaseManagement',
        component: TestCaseManagement,
        meta: {requiresAuth: true},
        props: true
      },
      {
        path: 'testcases/create',
        name: 'TestCaseCreate',
        component: TestCaseForm,
        meta: {requiresAuth: true},
        props: true
      },
      {
        path: 'testcases/:caseId/edit',
        name: 'TestCaseEdit',
        component: TestCaseForm,
        meta: {requiresAuth: true},
        props: true
      },
      {
        path: 'testplans',
        name: 'TestPlanManagement',
        component: TestPlanManagement,
        meta: {requiresAuth: true},
        props: true
      },
      {
        path: 'testtasks',
        name: 'TestTaskList',
        component: TestTaskList,
        meta: {requiresAuth: true},
        props: true
      }
    ]
  },
  {
    path: '/testtasks/:taskId/monitor',
    name: 'TaskExecutionMonitor',
    component: TaskExecutionMonitor,
    meta: {requiresAuth: true},
    props: true
  },
  {
    path: '/testjobs/:jobId/monitor',
    name: 'JobMonitor',
    component: JobMonitor,
    meta: {requiresAuth: true},
    props: true
  }
]

// 创建路由实例
const router = createRouter({
  history: createWebHistory(),
  routes
})

// 添加路由守卫
router.beforeEach((to, from, next) => {
  if (to.meta.requiresAuth) {
    const currentUserJson = localStorage.getItem('currentUser')
    if (currentUserJson) {
      try {
        const currentUser = JSON.parse(currentUserJson)
        if (currentUser.id === 0) {
          const allowedPaths = ['/system-config', '/', '/home', '/llm/credential']
          if (!allowedPaths.includes(to.path)) {
            next('/system-config')
            return
          }
        }
        next()
      } catch (e) {
        next('/login')
      }
    } else {
      if (to.path !== '/login') {
        localStorage.setItem('redirectPath', to.fullPath);
      }
      next('/login')
    }
  } else {
    next()
  }
})

export default router
