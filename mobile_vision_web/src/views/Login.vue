<template>
  <div class="login-container">
    <div class="login-wrapper">
      <!-- 左侧装饰区域 -->
      <div class="login-decoration">
        <div class="decoration-content">
          <div class="logo-placeholder">
            <div class="logo-icon">🎯</div>
          </div>
          <h2 class="title-animation">MobileVision 智能视觉平台</h2>
          <p class="subtitle">移动端UI自动化测试 · 视觉识别 · 智能Agent</p>
          <div class="features">
            <div class="feature-item" v-for="(feature, index) in features" :key="index">
              <i class="feature-icon" :style="{ animationDelay: index * 0.2 + 's' }">{{
                  feature.icon
                }}</i>
              <span>{{ feature.text }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧登录表单区域 -->
      <div class="login-box">
        <div class="login-form-container">
          <!-- 登录/注册切换标签 -->
          <div class="tab-switch">
            <div
              class="tab-item"
              :class="{ active: isLogin }"
              @click="switchTab(true)"
            >
              登录
            </div>
            <div
              class="tab-item"
              :class="{ active: !isLogin }"
              @click="switchTab(false)"
            >
              注册
            </div>
          </div>

          <!-- 登录表单 -->
          <el-form
            v-if="isLogin"
            ref="loginFormRef"
            :model="loginForm"
            :rules="loginRules"
            class="login-form"
            :class="{ 'form-slide-in': formTransition }"
          >
            <div class="form-title">
              <h3>欢迎回来</h3>
              <p>请使用您的账户登录</p>
            </div>

            <el-form-item prop="username">
              <el-input
                v-model="loginForm.username"
                placeholder="请输入用户名"
                prefix-icon="User"
                clearable
                size="large"
                @focus="handleInputFocus"
              />
            </el-form-item>

            <el-form-item prop="password">
              <el-input
                v-model="loginForm.password"
                type="password"
                placeholder="请输入密码"
                prefix-icon="Lock"
                show-password
                size="large"
                @focus="handleInputFocus"
              />
            </el-form-item>

            <div class="form-options">
              <el-checkbox v-model="rememberMe">记住我</el-checkbox>
              <el-link type="primary" underline="never">忘记密码？</el-link>
            </div>

            <el-form-item>
              <el-button
                type="primary"
                class="login-button"
                @click="handleLogin"
                :loading="loading"
                size="large"
                round
              >
                登录
              </el-button>
            </el-form-item>
          </el-form>

          <!-- 注册表单 -->
          <el-form
            v-else
            ref="registerFormRef"
            :model="registerForm"
            :rules="registerRules"
            class="register-form"
            :class="{ 'form-slide-in': formTransition }"
          >
            <div class="form-title">
              <h3>创建账户</h3>
              <p>加入我们开始测试之旅</p>
            </div>

            <el-form-item prop="username">
              <el-input
                v-model="registerForm.username"
                placeholder="用户名，如：yuanfang.li"
                prefix-icon="User"
                clearable
                size="large"
                @focus="handleInputFocus"
              />
            </el-form-item>

            <el-form-item prop="nickname">
              <el-input
                v-model="registerForm.nickname"
                placeholder="姓名，如：李元芳"
                prefix-icon="User"
                size="large"
                @focus="handleInputFocus"
              />
            </el-form-item>

            <el-form-item prop="email">
              <el-input
                v-model="registerForm.email"
                placeholder="邮箱地址"
                prefix-icon="Message"
                type="email"
                size="large"
                @focus="handleInputFocus"
              />
            </el-form-item>

            <el-form-item prop="password">
              <el-input
                v-model="registerForm.password"
                type="password"
                placeholder="密码"
                prefix-icon="Lock"
                show-password
                size="large"
                @focus="handleInputFocus"
              />
            </el-form-item>

            <el-form-item prop="confirmPassword">
              <el-input
                v-model="registerForm.confirmPassword"
                type="password"
                placeholder="确认密码"
                prefix-icon="Lock"
                show-password
                size="large"
                @focus="handleInputFocus"
              />
            </el-form-item>

            <el-form-item>
              <el-button
                type="primary"
                class="register-button"
                @click="handleRegister"
                :loading="loading"
                size="large"
                round
              >
                注册
              </el-button>
            </el-form-item>
          </el-form>
        </div>

        <div class="footer-info">
          <p>© 2025 MobileVision 智能视觉平台. 保留所有权利.</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import {ref, reactive, nextTick, onMounted} from 'vue'
import {useRouter} from 'vue-router'
import {ElMessage, ElCheckbox, ElLink} from 'element-plus'
import {User, Lock, Message} from '@element-plus/icons-vue'
import {register, login} from "@/network/api.js";

// 路由实例
const router = useRouter()

// 组件挂载时自动填充记住的登录信息
onMounted(() => {
  autoFillLoginCredentials()
})

// 自动填充登录凭证
const autoFillLoginCredentials = () => {
  try {
    // 从 localStorage 中读取 currentUser 对象
    const lastLoginUsername = localStorage.getItem('lastLoginUsername')
    if (lastLoginUsername) {
      loginForm.username = lastLoginUsername
      rememberMe.value = true
    }
  } catch (error) {
    console.warn('读取本地存储的登录信息失败:', error)
  }
}

// 登录/注册切换状态
const isLogin = ref(true)
const formTransition = ref(false)

// 记住我
const rememberMe = ref(true)

// 加载状态
const loading = ref(false)

// 登录表单引用
const loginFormRef = ref()

// 注册表单引用
const registerFormRef = ref()

// 功能特性列表
const features = ref([
  {icon: '📱', text: 'Android设备集群管理与ADB自动化'},
  {icon: '🔍', text: 'YOLO视觉识别驱动页面元素感知'},
  {icon: '🤖', text: 'LLM+视觉Agent自主规划与执行'},
  {icon: '📋', text: '测试用例管理 · 多设备并发执行'}
])

// 登录表单数据
const loginForm = reactive({
  username: '',
  password: ''
})

// 注册表单数据
const registerForm = reactive({
  username: '',
  nickname: '',
  email: '',
  password: '',
  confirmPassword: ''
})

// 登录表单验证规则
const loginRules = {
  username: [
    {required: true, message: '请输入用户名', trigger: 'blur'}
  ],
  password: [
    {required: true, message: '请输入密码', trigger: 'blur'},
    {min: 6, message: '密码长度至少6位', trigger: 'blur'}
  ]
}

// 注册表单验证规则
const registerRules = {
  username: [
    {required: true, message: '请输入用户名', trigger: 'blur'}
  ],
  nickname: [
    {required: true, message: '请输入昵称', trigger: 'blur'}
  ],
  email: [
    {required: true, message: '请输入邮箱', trigger: 'blur'},
    {type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur'}
  ],
  password: [
    {required: true, message: '请输入密码', trigger: 'blur'},
    {min: 6, message: '密码长度至少6位', trigger: 'blur'}
  ],
  confirmPassword: [
    {required: true, message: '请确认密码', trigger: 'blur'},
    {
      validator: (rule, value, callback) => {
        if (value !== registerForm.password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

// 切换标签页
const switchTab = (toLogin) => {
  if (isLogin.value !== toLogin) {
    formTransition.value = false
    isLogin.value = toLogin
    nextTick(() => {
      formTransition.value = true
    })
  }
}

// 处理输入框聚焦效果
const handleInputFocus = (event) => {
  event.target.parentElement.classList.add('input-focused')
  setTimeout(() => {
    event.target.parentElement.classList.remove('input-focused')
  }, 1000)
}

// 处理登录
const handleLogin = async () => {
  if (!loginFormRef.value) return

  await loginFormRef.value.validate((valid) => {
    if (valid) {
      loading.value = true

      const loginData = {
        username: loginForm.username,
        password: loginForm.password
      }
      login(loginData).then(res => {
        if (res.code === 0) {
          const currentUser = {
            id: res.data.id,
            username: res.data.username,
            nickname: res.data.nickname,
            email: res.data.email,
            access_token: res.data.access_token,
            token_type: res.data.token_type
          }
          localStorage.setItem('currentUser', JSON.stringify(currentUser))
          if (rememberMe.value === true) {
            // 将用户信息与token存储在 currentUser 对象中
            localStorage.setItem('lastLoginUsername', loginForm.username)
          } else {
            // 如果未选中"记住我"，则清除已保存的凭证
            localStorage.removeItem('lastLoginUsername')
          }
          ElMessage.success('登录成功');

          // 检查是否是环境变量中的超级管理员 (id=0)
          if (currentUser.id === 0) {
            // 环境变量中的超级管理员强制跳转到系统配置页面
            router.push('/system-config');
          } else {
            // 登录成功后检查是否有重定向路径
            const redirectPath = localStorage.getItem('redirectPath');
            if (redirectPath) {
              // 清除重定向路径
              localStorage.removeItem('redirectPath');
              // 跳转到之前访问的页面
              router.push(redirectPath);
            } else {
              // 默认跳转到首页
              router.push('/')
            }
          }
        } else {
          ElMessage.error(res.message)
        }
      }).catch(error => {
        ElMessage.error("登录失败")
      }).finally(() => {
        if (loading) loading.value = false
      })
    }
  })
}

// 处理注册
const handleRegister = async () => {
  if (!registerFormRef.value) return

  await registerFormRef.value.validate((valid) => {
    if (valid) {
      loading.value = true

      const registerData = {
        username: registerForm.username,
        nickname: registerForm.nickname,
        email: registerForm.email,
        password: registerForm.password
      }
      register(registerData).then(res => {
        if (res.code === 0) {
          // 将用户名密码写入loginForm表单
          loginForm.username = registerForm.username
          loginForm.password = registerForm.password
          ElMessage.success('注册成功');
          switchTab(true)
        } else {
          ElMessage.error(res.message)
        }
      }).catch(error => {
        ElMessage.error("注册失败")
      }).finally(() => {
        if (loading) loading.value = false
      })
    }
  })
}
</script>

<style scoped>
.login-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 50%, #cbd5e1 100%);
  padding: 20px;
  position: relative;
  overflow: hidden;
}

/* Decorative background elements */
.login-container::before {
  content: '';
  position: absolute;
  width: 400px;
  height: 400px;
  background: radial-gradient(circle, rgba(59, 130, 246, 0.15) 0%, transparent 70%);
  top: -100px;
  right: -100px;
  pointer-events: none;
}

.login-container::after {
  content: '';
  position: absolute;
  width: 300px;
  height: 300px;
  background: radial-gradient(circle, rgba(168, 85, 247, 0.1) 0%, transparent 70%);
  bottom: -50px;
  left: -50px;
  pointer-events: none;
}

.login-wrapper {
  display: flex;
  width: 100%;
  max-width: 800px;
  height: 500px;
  background: rgba(255, 255, 255, 0.7);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
  border-radius: 24px;
  overflow: hidden;
  box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.5);
  position: relative;
  z-index: 1;
}

@supports not (backdrop-filter: blur(20px)) {
  .login-wrapper {
    background: rgba(255, 255, 255, 0.95);
  }
}

.login-decoration {
  flex: 1;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.8) 0%, rgba(248, 250, 252, 0.9) 100%);
  color: #1e293b;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
  border-right: 1px solid rgba(0, 0, 0, 0.05);
}

.decoration-content {
  text-align: center;
  z-index: 1;
}

.logo-placeholder {
  margin-bottom: 30px;
}

.logo-icon {
  font-size: 60px;
  margin-bottom: 20px;
}

.title-animation {
  font-size: 24px;
  margin-bottom: 10px;
  font-weight: 700;
}

.subtitle {
  font-size: 14px;
  color: #64748b;
  margin-bottom: 40px;
}

.features {
  text-align: left;
}

.feature-item {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
  font-size: 14px;
  color: #64748b;
}

.feature-icon {
  font-size: 20px;
  margin-right: 12px;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.login-box {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  background: transparent;
}

.login-form-container {
  padding: 50px 40px;
}

.tab-switch {
  display: flex;
  border-bottom: 2px solid #f1f5f9;
  margin-bottom: 30px;
}

.tab-item {
  flex: 1;
  text-align: center;
  padding: 12px 0;
  cursor: pointer;
  font-size: 16px;
  color: #64748b;
  transition: all 0.3s;
  font-weight: 500;
  position: relative;
}

.tab-item.active {
  color: #3b82f6;
  font-weight: 600;
}

.tab-item.active::after {
  content: '';
  position: absolute;
  bottom: -2px;
  left: 20%;
  width: 60%;
  height: 2px;
  background: #3b82f6;
  border-radius: 2px;
}

.form-title {
  text-align: center;
  margin-bottom: 30px;
}

.form-title h3 {
  font-size: 24px;
  color: #1e293b;
  margin-bottom: 8px;
  font-weight: 700;
}

.form-title p {
  color: #64748b;
  font-size: 14px;
}

.form-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

:deep(.el-checkbox__input.is-checked .el-checkbox__inner) {
  background-color: #3b82f6;
  border-color: #3b82f6;
}

:deep(.el-checkbox__input.is-indeterminate .el-checkbox__inner) {
  background-color: #3b82f6;
  border-color: #3b82f6;
}

:deep(.el-checkbox__input.is-focus .el-checkbox__inner) {
  border-color: #3b82f6;
}

:deep(.el-checkbox__label) {
  color: #64748b;
}

:deep(.el-link) {
  color: #3b82f6 !important;
}

/* Customize Element Plus inputs */
:deep(.el-input__wrapper) {
  background-color: rgba(255, 255, 255, 0.8) !important;
  border: 2px solid #e2e8f0 !important;
  border-radius: 12px !important;
  box-shadow: none !important;
  transition: all 0.2s !important;
}

:deep(.el-input__wrapper:hover) {
  border-color: #cbd5e1 !important;
}

:deep(.el-input__wrapper.is-focus) {
  border-color: #3b82f6 !important;
  background-color: #fff !important;
}

:deep(.el-input__inner) {
  color: #1e293b !important;
}

:deep(.el-input__inner::placeholder) {
  color: #94a3b8 !important;
}

:deep(.el-input__prefix) {
  color: #64748b !important;
}

.login-button,
.register-button {
  width: 100%;
  margin-top: 10px;
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  border: none;
  transition: all 0.2s;
  color: white;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
}

.login-button:hover,
.register-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 20px rgba(59, 130, 246, 0.35);
}

.form-slide-in {
  animation: fadeIn 0.3s ease-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.input-focused {
  animation: inputFocus 0.5s ease;
}

@keyframes inputFocus {
  0% {
    box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.3);
  }
  70% {
    box-shadow: 0 0 0 10px rgba(59, 130, 246, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(59, 130, 246, 0);
  }
}

.footer-info {
  text-align: center;
  padding: 20px;
  color: #94a3b8;
  font-size: 12px;
  border-top: 1px solid rgba(0, 0, 0, 0.05);
  background: transparent;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .login-wrapper {
    flex-direction: column;
    height: auto;
  }

  .login-decoration {
    padding: 20px;
  }

  .login-form-container {
    padding: 20px;
  }

  .login-container {
    padding: 10px;
  }
}
</style>
