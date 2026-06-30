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
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
  animation: gradientShift 10s ease infinite;
  background-size: 400% 400%;
}

@keyframes gradientShift {
  0% {
    background-position: 0% 50%;
  }
  50% {
    background-position: 100% 50%;
  }
  100% {
    background-position: 0% 50%;
  }
}

.login-wrapper {
  display: flex;
  width: 100%;
  max-width: 900px;
  height: 600px;
  background: white;
  border-radius: 20px;
  overflow: hidden;
  box-shadow: 0 25px 50px rgba(0, 0, 0, 0.2);
  animation: float 6s ease-in-out infinite;
}

@keyframes float {
  0% {
    transform: translateY(0px);
  }
  50% {
    transform: translateY(-10px);
  }
  100% {
    transform: translateY(0px);
  }
}

.login-decoration {
  flex: 1;
  background: linear-gradient(135deg, #4b6ef7 0%, #69c0ff 100%);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px;
  position: relative;
  overflow: hidden;
}

.login-decoration::before {
  content: '';
  position: absolute;
  top: -50%;
  left: -50%;
  width: 200%;
  height: 200%;
  background: radial-gradient(circle, rgba(255, 255, 255, 0.1) 0%, transparent 70%);
  animation: rotate 20s linear infinite;
}

@keyframes rotate {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.decoration-content {
  text-align: center;
  z-index: 1;
}

.logo-placeholder {
  margin-bottom: 30px;
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.1);
  }
  100% {
    transform: scale(1);
  }
}

.logo-icon {
  font-size: 60px;
  margin-bottom: 20px;
  filter: drop-shadow(0 0 10px rgba(255, 255, 255, 0.5));
}

.title-animation {
  font-size: 28px;
  margin-bottom: 10px;
  font-weight: 600;
  animation: fadeInUp 1s ease-out;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.subtitle {
  font-size: 16px;
  opacity: 0.9;
  margin-bottom: 40px;
  animation: fadeInUp 1s ease-out 0.2s both;
}

.features {
  text-align: left;
  animation: fadeInUp 1s ease-out 0.4s both;
}

.feature-item {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
  font-size: 14px;
  opacity: 0;
  animation: slideInRight 0.5s ease-out forwards;
}

@keyframes slideInRight {
  from {
    opacity: 0;
    transform: translateX(-20px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.feature-icon {
  font-size: 20px;
  margin-right: 12px;
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  animation: bounce 2s infinite;
}

@keyframes bounce {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-5px);
  }
}

.login-box {
  flex: 1;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  background: #fafafa;
}

.login-form-container {
  padding: 40px;
}

.tab-switch {
  display: flex;
  border-bottom: 2px solid #e0e0e0;
  margin-bottom: 30px;
}

.tab-item {
  flex: 1;
  text-align: center;
  padding: 15px 0;
  cursor: pointer;
  font-size: 16px;
  color: #666;
  transition: all 0.3s;
  font-weight: 500;
  position: relative;
}

.tab-item.active {
  color: #4b6ef7;
  font-weight: 600;
}

.tab-item.active::after {
  content: '';
  position: absolute;
  bottom: -2px;
  left: 20%;
  width: 60%;
  height: 3px;
  background: #4b6ef7;
  border-radius: 3px;
  animation: tabLine 0.3s ease-out;
}

@keyframes tabLine {
  from {
    width: 0;
    left: 50%;
  }
  to {
    width: 60%;
    left: 20%;
  }
}

.form-title {
  text-align: center;
  margin-bottom: 30px;
}

.form-title h3 {
  font-size: 24px;
  color: #333;
  margin-bottom: 8px;
}

.form-title p {
  color: #666;
  font-size: 14px;
}

.form-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.login-button,
.register-button {
  width: 100%;
  margin-top: 10px;
  background: linear-gradient(135deg, #4b6ef7 0%, #69c0ff 100%);
  border: none;
  transition: all 0.3s;
  color: white;
}

.login-button:hover,
.register-button:hover {
  transform: translateY(-2px);
  box-shadow: 0 5px 15px rgba(75, 110, 247, 0.3);
}

.form-slide-in {
  animation: slideIn 0.5s ease-out;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateX(20px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.input-focused {
  animation: inputFocus 0.5s ease;
}

@keyframes inputFocus {
  0% {
    box-shadow: 0 0 0 0 rgba(75, 110, 247, 0.3);
  }
  70% {
    box-shadow: 0 0 0 10px rgba(75, 110, 247, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(75, 110, 247, 0);
  }
}

.footer-info {
  text-align: center;
  padding: 20px;
  color: #999;
  font-size: 12px;
  border-top: 1px solid #eee;
  background: #fafafa;
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
