<template>
  <div class="tc-page">
    <!-- Header -->
    <header class="tc-header">
      <div class="tc-header-inner">
        <div class="tc-header-left">
          <el-button class="tc-back-btn" @click="goBack">
            <el-icon><ArrowLeft /></el-icon>
            <span>返回</span>
          </el-button>
          <div class="tc-header-info">
            <h1 class="tc-title">{{ isEdit ? '编辑用例' : '新建用例' }}</h1>
            <p class="tc-subtitle">{{ isEdit ? '修改已有的测试用例信息' : '创建新的测试用例' }}</p>
          </div>
        </div>
        <div class="tc-header-right">
          <el-button type="primary" class="tc-save-btn" @click="saveCase">
            <el-icon><Check /></el-icon>
            <span>{{ isEdit ? '保存修改' : '创建用例' }}</span>
          </el-button>
        </div>
      </div>
    </header>

    <div class="tc-body">
      <!-- 基本信息卡片 -->
      <section class="tc-card">
        <div class="tc-card-header">
          <div class="tc-card-header-left">
            <span class="tc-card-icon">
              <el-icon><Document /></el-icon>
            </span>
            <div>
              <h2 class="tc-card-title">基本信息</h2>
              <p class="tc-card-desc">配置用例的名称、优先级和状态</p>
            </div>
          </div>
          <div v-if="isEdit" class="tc-card-meta">
            <span class="tc-meta-tag">创建 {{ formatTime(form.create_time) }}</span>
            <span class="tc-meta-tag">更新 {{ formatTime(form.update_time) }}</span>
          </div>
        </div>
        <div class="tc-card-body">
          <div class="tc-field-row">
            <div class="tc-field tc-field--grow">
              <label class="tc-label">
                <span class="tc-label-text">用例名称</span>
              </label>
              <el-input v-model="form.case_name" placeholder="例如：登录功能验证" class="tc-input" />
            </div>
            <div class="tc-field">
              <label class="tc-label">
                <span class="tc-label-text">优先级</span>
              </label>
              <el-select v-model="form.level" class="tc-select" :class="'tc-level--' + form.level.toLowerCase()">
                <el-option label="P0 - 关键" value="P0" />
                <el-option label="P1 - 重要" value="P1" />
                <el-option label="P2 - 一般" value="P2" />
                <el-option label="P3 - 建议" value="P3" />
              </el-select>
            </div>
            <div class="tc-field">
              <label class="tc-label">
                <span class="tc-label-text">状态</span>
              </label>
              <el-select v-model="form.status" class="tc-select">
                <el-option label="调试中" value="debugging" />
                <el-option label="已完成" value="completed" />
                <el-option label="已禁用" value="disabled" />
              </el-select>
            </div>
          </div>
        </div>
      </section>

      <!-- 正文编辑卡片 -->
      <section class="tc-card tc-card--editor">
        <div class="tc-card-header">
          <div class="tc-card-header-left">
            <span class="tc-card-icon tc-card-icon--editor">
              <el-icon><Edit /></el-icon>
            </span>
            <div>
              <h2 class="tc-card-title">{{ activeTab === 'content' ? '测试任务正文' : 'APP 使用说明' }}</h2>
              <p class="tc-card-desc">{{ activeTab === 'content' ? '描述测试步骤和预期结果' : '告诉大模型如何使用这个应用' }}</p>
            </div>
          </div>
          <div class="tc-editor-actions">
            <button
              v-for="tab in tabs"
              :key="tab.name"
              :class="['tc-tab', { active: activeTab === tab.name }]"
              @click="activeTab = tab.name"
            >
              {{ tab.label }}
            </button>
          </div>
        </div>
        <div class="tc-card-body tc-card-body--editor">
          <div class="tc-textarea-wrap">
            <textarea
              v-model="currentEditorContent"
              class="tc-textarea"
              :placeholder="activeTab === 'content' ? '输入测试任务内容，支持 Markdown 格式...' : '描述 APP 的使用方法，帮助大模型理解如何操作...'"
            ></textarea>
          </div>
          <div class="tc-textarea-footer">
            <span class="tc-char-count">{{ currentEditorContent.length }} 字符</span>
            <span class="tc-format-hint">支持 Markdown</span>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script>
import { ref, reactive, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Check, Document, Edit } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { createTestCase, updateTestCase, getTestCaseDetail } from '@/network/api.js'

export default {
  name: 'TestCaseForm',
  components: {
    ArrowLeft,
    Check,
    Document,
    Edit
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
/* ===== Reset ===== */
.tc-page {
  height: 100%;
  display: flex;
  flex-direction: column;
  background: #f3f4f6;
}

/* ===== Header ===== */
.tc-header {
  background: #ffffff;
  border-bottom: 1px solid #e5e7eb;
  flex-shrink: 0;
}

.tc-header-inner {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 16px 16px;
  width: 100%;
  box-sizing: border-box;
}

.tc-header-left {
  display: flex;
  align-items: center;
  gap: 20px;
}

.tc-back-btn {
  border: none;
  background: #f3f4f6;
  font-size: 13px;
  font-weight: 500;
  color: #374151;
  padding: 8px 14px;
  border-radius: 8px;
  transition: background 0.15s ease;
}

.tc-back-btn:hover {
  background: #e5e7eb;
  color: #111827;
}

.tc-header-info {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.tc-title {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: #111827;
  letter-spacing: -0.3px;
}

.tc-subtitle {
  margin: 0;
  font-size: 12.5px;
  color: #6b7280;
}

.tc-save-btn {
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  padding: 9px 22px;
  background: #2563eb;
  border-color: #2563eb;
  box-shadow: 0 1px 3px rgba(37, 99, 235, 0.3);
  transition: all 0.15s ease;
}

.tc-save-btn:hover {
  background: #1d4ed8;
  border-color: #1d4ed8;
  box-shadow: 0 2px 6px rgba(37, 99, 235, 0.4);
}

/* ===== Body ===== */
.tc-body {
  flex: 1;
  padding: 16px 16px;
  width: 100%;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
  gap: 16px;
  overflow-y: auto;
  min-height: 0;
}

/* ===== Card ===== */
.tc-card {
  background: #ffffff;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
  overflow: hidden;
  flex-shrink: 0;
}

.tc-card--editor {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
  flex-shrink: 1;
}

.tc-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 18px 16px;
  border-bottom: 1px solid #f3f4f6;
  gap: 16px;
}

.tc-card-header-left {
  display: flex;
  align-items: center;
  gap: 14px;
}

.tc-card-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  background: #eff6ff;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #2563eb;
  font-size: 16px;
  flex-shrink: 0;
}

.tc-card-icon--editor {
  background: #f5f3ff;
  color: #7c3aed;
}

.tc-card-title {
  margin: 0;
  font-size: 15px;
  font-weight: 600;
  color: #111827;
}

.tc-card-desc {
  margin: 2px 0 0;
  font-size: 12px;
  color: #9ca3af;
}

.tc-card-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}

.tc-meta-tag {
  font-size: 11px;
  color: #9ca3af;
  background: #f9fafb;
  padding: 3px 10px;
  border-radius: 10px;
  border: 1px solid #f3f4f6;
  white-space: nowrap;
}

.tc-card-body {
  padding: 20px 16px;
}

.tc-card-body--editor {
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 16px 16px 20px;
  min-height: 0;
}

/* ===== Fields ===== */
.tc-field-row {
  display: flex;
  gap: 20px;
  align-items: flex-start;
}

.tc-field {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 8px;
  min-width: 0;
  flex-shrink: 0;
}

.tc-field--grow {
  flex: 1;
  min-width: 0;
}

.tc-label {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 6px;
  flex-shrink: 0;
  width: 70px;
}

.tc-label-text {
  font-size: 12.5px;
  font-weight: 500;
  color: #374151;
  white-space: nowrap;
}

.tc-input {
  width: 100%;
}

.tc-input .el-input__wrapper {
  border-radius: 8px;
  box-shadow: 0 0 0 1px #d1d5db inset;
  background: #f9fafb;
  transition: box-shadow 0.15s ease, background 0.15s ease;
}

.tc-input .el-input__wrapper:hover {
  box-shadow: 0 0 0 1px #9ca3af inset;
}

.tc-input .el-input.is-focus .el-input__wrapper {
  box-shadow: 0 0 0 2px #2563eb inset;
  background: #ffffff;
}

.tc-input .el-input__inner {
  height: 38px;
  font-size: 14px;
}

.tc-input .el-input__inner::placeholder {
  color: #9ca3af;
}

.tc-select {
  width: 150px;
}

.tc-select .el-input__wrapper {
  border-radius: 8px;
  box-shadow: 0 0 0 1px #d1d5db inset;
  background: #f9fafb;
  transition: box-shadow 0.15s ease, background 0.15s ease;
}

.tc-select .el-input__wrapper:hover {
  box-shadow: 0 0 0 1px #9ca3af inset;
}

.tc-select .el-input.is-focus .el-input__wrapper {
  box-shadow: 0 0 0 2px #2563eb inset;
  background: #ffffff;
}

.tc-select .el-input__inner {
  height: 38px;
  font-size: 14px;
}

/* ===== Editor tabs ===== */
.tc-editor-actions {
  display: flex;
  gap: 2px;
  background: #f3f4f6;
  padding: 3px;
  border-radius: 8px;
  flex-shrink: 0;
}

.tc-tab {
  padding: 6px 14px;
  border: none;
  background: transparent;
  border-radius: 6px;
  font-size: 12.5px;
  font-weight: 500;
  color: #6b7280;
  cursor: pointer;
  transition: all 0.15s ease;
  white-space: nowrap;
}

.tc-tab:hover {
  color: #374151;
}

.tc-tab.active {
  background: #ffffff;
  color: #111827;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
}

/* ===== Textarea ===== */
.tc-textarea-wrap {
  flex: 1;
  position: relative;
  min-height: 0;
}

.tc-textarea {
  width: 100%;
  height: 100%;
  min-height: 180px;
  padding: 18px 20px;
  background: #fafafa;
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  font-family: 'SF Mono', 'Monaco', 'Menlo', 'Consolas', monospace;
  font-size: 14px;
  line-height: 1.75;
  color: #111827;
  resize: none;
  transition: border-color 0.15s ease, box-shadow 0.15s ease, background 0.15s ease;
  box-sizing: border-box;
}

.tc-textarea:focus {
  outline: none;
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
  background: #ffffff;
}

.tc-textarea::placeholder {
  color: #9ca3af;
}

.tc-textarea-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 10px;
  flex-shrink: 0;
}

.tc-char-count {
  font-size: 11.5px;
  color: #9ca3af;
}

.tc-format-hint {
  font-size: 11.5px;
  color: #9ca3af;
  background: #f3f4f6;
  padding: 2px 10px;
  border-radius: 8px;
}

@media (max-width: 900px) {
  .tc-header-inner {
    padding: 14px 16px;
  }

  .tc-body {
    padding: 16px 16px;
  }

  .tc-field-row {
    flex-direction: column;
  }

  .tc-field--grow {
    min-width: 0;
  }

  .tc-select {
    width: 100%;
  }

  .tc-card-header {
    flex-direction: column;
    align-items: flex-start;
  }
}

@media (max-width: 640px) {
  .tc-field {
    flex-direction: column;
    align-items: stretch;
  }

  .tc-label {
    width: auto;
  }
}
</style>