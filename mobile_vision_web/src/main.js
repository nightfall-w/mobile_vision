// src/main.js
import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css' // 确保导入了 Element Plus 样式
import * as ElementPlusIconsVue from '@element-plus/icons-vue'
import "@/assets/main.css";

// 👇 prismjs 和 vue-prism-component 引入
import VuePrismComponent from 'vue-prism-component'
import 'prismjs/themes/prism.css'
import {setRouter} from "@/network/axios.js";

const app = createApp(App)

// 注册 Element Plus Icons
for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
    app.component(key, component)
}

// 注册 <prism> 组件为全局组件
app.component('prism', VuePrismComponent)
setRouter(router)
app.use(router)
app.use(ElementPlus)
app.mount('#app')
