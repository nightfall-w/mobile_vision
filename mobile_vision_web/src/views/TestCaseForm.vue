<template>
  <div class="testcase-form-wrapper">
    <div class="page-header">
      <div class="header-left">
        <button class="back-button" @click="goBack">
          <el-icon class="icon">
            <ArrowLeft />
          </el-icon>
          <span>返回</span>
        </button>
        <div class="title-group">
          <h1 class="page-title">{{ isEdit ? '编辑用例' : '新建用例' }}</h1>
          <p class="page-subtitle">{{ isEdit ? '修改已有的测试用例信息' : '创建新的测试用例' }}</p>
        </div>
      </div>
      <div class="header-right">
        <button class="save-button" @click="saveCase">
          <el-icon class="icon">
            <Check />
          </el-icon>
          <span>{{ isEdit ? '保存修改' : '创建用例' }}</span>
        </button>
      </div>
    </div>

    <div class="content-container">
      <aside class="sidebar">
        <div class="panel">
          <div class="panel-header">
            <h2 class="panel-title">基本信息</h2>
          </div>
          <div class="panel-body">
            <div class="form-group">
              <label class="form-label">用例名称</label>
              <input
                v-model="form.case_name"
                type="text"
                class="form-input"
                placeholder="请输入用例名称"
              />
            </div>
            
            <div class="form-group">
              <label class="form-label">优先级</label>
              <select v-model="form.level" class="form-select">
                <option value="P0">P0</option>
                <option value="P1">P1</option>
                <option value="P2">P2</option>
                <option value="P3">P3</option>
              </select>
            </div>
            
            <div class="form-group">
              <label class="form-label">状态</label>
              <select v-model="form.status" class="form-select">
                <option value="debugging">调试中</option>
                <option value="completed">已完成</option>
                <option value="disabled">禁用</option>
              </select>
            </div>
          </div>
        </div>

        <div class="panel" v-if="isEdit">
          <div class="panel-header">
            <h2 class="panel-title">时间信息</h2>
          </div>
          <div class="panel-body">
            <div class="form-group">
              <label class="form-label">创建时间</label>
              <input
                :value="formatTime(form.create_time)"
                type="text"
                class="form-input disabled"
                disabled
              />
            </div>
            <div class="form-group">
              <label class="form-label">更新时间</label>
              <input
                :value="formatTime(form.update_time)"
                type="text"
                class="form-input disabled"
                disabled
              />
            </div>
          </div>
        </div>
      </aside>

      <section class="editor-area">
        <div class="editor-card">
          <div class="tabs-wrapper">
            <button
              v-for="tab in tabs"
              :key="tab.name"
              :class="['tab-button', { active: activeTab === tab.name }]"
              @click="activeTab = tab.name"
            >
              {{ tab.label }}
              <span class="tab-indicator" v-if="activeTab === tab.name"></span>
            </button>
          </div>
          
          <div class="editor-content">
            <textarea
              v-model="currentEditorContent"
              class="editor-textarea"
              :placeholder="activeTab === 'content' ? '请输入测试任务内容...' : '请输入 APP 使用说明，告诉大模型如何使用这个应用...'"
            ></textarea>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script>
import { ref, reactive, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Check } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { createTestCase, updateTestCase, getTestCaseDetail } from '@/network/api.js'

export default {
  name: 'TestCaseForm',
  components: {
    ArrowLeft,
    Check
  },
  setup() {
    const route = useRoute()
    const router = useRouter()
    const workspaceId = route.params.id
    const caseId = route.params.caseId

    const isEdit = computed(() => !!caseId)
    const activeTab = ref('content')
    
    const tabs = [
      { name: 'content', label: '测试任务正文' },
      { name: 'usage', label: 'APP使用说明' }
    ]

    const form = reactive({
      case_id: null,
      case_name: '',
      content: '',
      usage_instructions: '',
      level: 'P2',
      status: 'debugging',
      create_time: '',
      update_time: ''
    })

    const currentEditorContent = computed({
      get() {
        return activeTab.value === 'content' ? form.content : form.usage_instructions
      },
      set(value) {
        if (activeTab.value === 'content') {
          form.content = value
        } else {
          form.usage_instructions = value
        }
      }
    })

    const goBack = () => {
      router.push(`/workspace/${workspaceId}/testcases`)
    }

    const saveCase = async () => {
      if (!form.case_name.trim()) {
        ElMessage.warning('请输入用例名称')
        return
      }

      try {
        let res
        if (isEdit.value) {
          res = await updateTestCase({
            case_id: form.case_id,
            case_name: form.case_name,
            content: form.content,
            usage_instructions: form.usage_instructions,
            level: form.level,
            status: form.status
          })
        } else {
          res = await createTestCase({
            workspace_id: parseInt(workspaceId),
            case_name: form.case_name,
            content: form.content,
            usage_instructions: form.usage_instructions,
            level: form.level,
            status: form.status
          })
        }

        if (res.code === 0) {
          ElMessage.success(isEdit.value ? '修改成功' : '创建成功')
          goBack()
        } else {
          ElMessage.error(res.message || (isEdit.value ? '修改失败' : '创建失败'))
        }
      } catch (error) {
        console.error('保存用例失败:', error)
        ElMessage.error(isEdit.value ? '修改失败' : '创建失败')
      }
    }

    const formatTime = (timeString) => {
      if (!timeString) return ''
      return timeString.replace('T', ' ')
    }

    const loadCaseDetail = async () => {
      if (!caseId) return

      try {
        const res = await getTestCaseDetail(caseId)
        if (res.code === 0) {
          const data = res.data
          form.case_id = data.case_id
          form.case_name = data.case_name
          form.content = data.content || ''
          form.usage_instructions = data.usage_instructions || ''
          form.level = data.level
          form.status = data.status
          form.create_time = data.create_time || ''
          form.update_time = data.update_time || ''
        }
      } catch (error) {
        console.error('获取用例详情失败:', error)
      }
    }

    onMounted(() => {
      loadCaseDetail()
    })

    return {
      isEdit,
      activeTab,
      tabs,
      form,
      currentEditorContent,
      goBack,
      saveCase,
      formatTime
    }
  }
}
</script>

<style scoped>
:root {
  --primary-color: #4080ff;
  --primary-hover: #366fc9;
  --text-primary: #1f2d3d;
  --text-secondary: #646a73;
  --border-color: #e8eef3;
  --shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.04);
  --shadow-md: 0 4px 16px rgba(0, 0, 0, 0.06);
  --shadow-lg: 0 8px 24px rgba(0, 0, 0, 0.08);
}

.testcase-form-wrapper {
  min-height: 100%;
  background: #f5f5f5;
  padding: 0;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 24px;
  background: #ffffff;
  border-radius: 12px;
  box-shadow: var(--shadow-sm);
  margin-bottom: 20px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 16px;
}

.back-button {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: #f5f7fa;
  border: 1px solid #e4e8ec;
  border-radius: 8px;
  color: #646a73;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.back-button:hover {
  background: #e8eef3;
  border-color: #d0d5d9;
}

.back-button .icon {
  width: 16px;
  height: 16px;
}

.title-group {
  display: flex;
  flex-direction: column;
}

.page-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--text-primary);
}

.page-subtitle {
  margin: 2px 0 0;
  font-size: 12px;
  color: var(--text-secondary);
}

.header-right {
  display: flex;
  gap: 12px;
}

.save-button {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 24px;
  background: #4080ff;
  border: none;
  border-radius: 8px;
  color: #ffffff;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(64, 128, 255, 0.3);
  transition: all 0.3s ease;
}

.save-button:hover {
  background: #366fc9;
  box-shadow: 0 6px 16px rgba(64, 128, 255, 0.4);
  transform: translateY(-1px);
}

.save-button .icon {
  width: 16px;
  height: 16px;
  color: #ffffff;
}

.content-container {
  display: flex;
  gap: 24px;
}

.sidebar {
  width: 320px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.panel {
  background: #ffffff;
  border-radius: 16px;
  box-shadow: var(--shadow-md);
  overflow: hidden;
  transition: all 0.3s ease;
}

.panel:hover {
  box-shadow: var(--shadow-lg);
}

.panel-header {
  padding: 16px 20px;
  border-bottom: 1px solid #f0f2f5;
  background: linear-gradient(180deg, #fafbfc 0%, #ffffff 100%);
}

.panel-title {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
}

.panel-body {
  padding: 20px;
}

.form-group {
  margin-bottom: 20px;
}

.form-group:last-child {
  margin-bottom: 0;
}

.form-label {
  display: block;
  margin-bottom: 8px;
  font-size: 14px;
  font-weight: 500;
  color: #475669;
}

.form-input {
  width: 100%;
  height: 44px;
  padding: 0 14px;
  background: #fafbfc;
  border: 1px solid #d9dde3;
  border-radius: 10px;
  font-size: 14px;
  color: var(--text-primary);
  transition: all 0.3s ease;
  box-sizing: border-box;
}

.form-input:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px rgba(64, 128, 255, 0.1);
}

.form-input::placeholder {
  color: #8f959e;
}

.form-input.disabled {
  background: #f5f7fa;
  color: #8f959e;
  cursor: not-allowed;
}

.form-select {
  width: 100%;
  height: 44px;
  padding: 0 14px;
  background: #fafbfc;
  border: 1px solid #d9dde3;
  border-radius: 10px;
  font-size: 14px;
  color: var(--text-primary);
  cursor: pointer;
  transition: all 0.3s ease;
  box-sizing: border-box;
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='16' height='16' viewBox='0 0 24 24' fill='none' stroke='%23646a73' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'%3E%3C/polyline%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 14px center;
}

.form-select:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px rgba(64, 128, 255, 0.1);
}

.editor-area {
  flex: 1;
  min-width: 0;
}

.editor-card {
  background: #ffffff;
  border-radius: 16px;
  box-shadow: var(--shadow-md);
  overflow: hidden;
  height: calc(100vh - 200px);
  display: flex;
  flex-direction: column;
  transition: all 0.3s ease;
}

.editor-card:hover {
  box-shadow: var(--shadow-lg);
}

.tabs-wrapper {
  display: flex;
  border-bottom: 1px solid #f0f2f5;
  background: #fafbfc;
}

.tab-button {
  position: relative;
  padding: 16px 32px;
  background: transparent;
  border: none;
  font-size: 14px;
  font-weight: 500;
  color: #646a73;
  cursor: pointer;
  transition: all 0.3s ease;
}

.tab-button:hover {
  color: var(--primary-color);
  background: rgba(64, 128, 255, 0.05);
}

.tab-button.active {
  color: var(--primary-color);
  background: #ffffff;
}

.tab-indicator {
  position: absolute;
  bottom: 0;
  left: 24px;
  right: 24px;
  height: 2px;
  background: var(--primary-color);
  border-radius: 1px;
}

.editor-content {
  flex: 1;
  padding: 20px;
  overflow: hidden;
}

.editor-textarea {
  width: 100%;
  height: 100%;
  min-height: 300px;
  padding: 16px;
  background: #f8fafc;
  border: 1px solid #e8eef3;
  border-radius: 12px;
  font-family: 'Monaco', 'Menlo', 'Consolas', monospace;
  font-size: 14px;
  line-height: 1.6;
  color: var(--text-primary);
  resize: none;
  transition: all 0.3s ease;
  box-sizing: border-box;
}

.editor-textarea:focus {
  outline: none;
  border-color: var(--primary-color);
  box-shadow: 0 0 0 3px rgba(64, 128, 255, 0.1);
}

.editor-textarea::placeholder {
  color: #8f959e;
}

@media (max-width: 1200px) {
  .sidebar {
    width: 280px;
  }
}

@media (max-width: 768px) {
  .content-container {
    flex-direction: column;
  }
  
  .sidebar {
    width: 100%;
  }
  
  .editor-card {
    height: 400px;
  }
  
  .page-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }
  
  .header-right {
    width: 100%;
    justify-content: flex-end;
  }
  
  .back-button span {
    display: none;
  }
  
  .save-button span {
    display: none;
  }
}
</style>
