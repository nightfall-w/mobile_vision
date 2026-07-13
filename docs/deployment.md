# 源码部署指南

## 环境要求

| 组件 | 版本要求 |
|------|----------|
| Python | 3.10+ |
| Node.js | 20+ |
| MySQL | 8.0+ |
| Redis | 6.x+（可选，任务队列用） |
| ADB | 最新版（Android 设备控制） |

---

## 1. 克隆与安装

```bash
git clone git@github.com:nightfall-w/mobile_vision.git
cd mobile_vision

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

---

## 2. 数据库准备

```bash
# 创建数据库
mysql -u root -p
CREATE DATABASE IF NOT EXISTS mobile_vision DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
exit

# 初始化表结构
mysql -u root -p mobile_vision < scripts/init_database.sql
```

---

## 3. 后端部署

### 3.1 配置环境变量

```bash
cp .env.example .env
```

按需修改 `.env`：

```ini
# 数据库配置
DB_USER=root
DB_PASSWORD=your_password
DB_HOST=127.0.0.1
DB_PORT=3306
DB_NAME=mobile_vision

# Redis 配置
REDIS_HOST=127.0.0.1
REDIS_PORT=6379
REDIS_PASSWORD=

# 访问令牌有效期（分钟）
ACCESS_TOKEN_EXPIRE_MINUTES=1440

```

### 3.2 启动服务

```bash
# 终端 1：API 服务（推荐 4 workers）
uvicorn main:app --host 0.0.0.0 --port 8080 --workers 4

# 终端 2：后台任务消费者（处理测试任务和 YOLO 训练任务）
python funboost_cli_user.py consume all
```

验证服务是否启动：

```bash
curl http://127.0.0.1:8080/api/v1/health
# 应返回 {"code": 0, "data": "ok"}
```

---

## 3. 前端部署

### 3.1 构建

```bash
cd mobile_vision_web

# 安装依赖
npm install

# 构建生产版本
npm run build
```

构建产物在 `mobile_vision_web/dist/` 目录。

### 3.2 配置 API 地址

编辑 `mobile_vision_web/.env.production`：

```ini
# 后端 API 地址（生产环境改为实际服务器地址）
VITE_APP_SERVER_URL = "http://your-server-ip:8080"
```

如果前端和后端部署在同一台服务器，也可以保持 `127.0.0.1`，然后通过 Nginx 对外提供服务。

### 3.3 使用 Nginx 部署

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    root /path/to/mobile_vision/mobile_vision_web/dist;
    index index.html;

    # API 反向代理
    location /api/ {
        proxy_pass http://127.0.0.1:8080/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }

    # WebSocket 代理（执行监控）
    location /ws/ {
        proxy_pass http://127.0.0.1:8080/ws/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }

    # 静态资源（测试报告截图、YOLO 预测结果等）
    location /storage/ {
        proxy_pass http://127.0.0.1:8080/storage/;
    }

    # SPA 路由：所有非文件请求返回 index.html
    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

---

## 4. 安卓设备连接

### 4.1 有线连接

```bash
# 连接真机（开启开发者选项和 USB 调试）
adb devices
# 应看到设备 serial number，状态为 device
```

### 4.2 无线 ADB 连接

```bash
# 1. 确保设备和电脑在同一局域网
# 2. 设备通过 USB 连接后，设置端口
adb tcpip 5555

# 3. 拔掉 USB，通过网络连接
adb connect <设备IP>:5555

# 4. 确认连接
adb devices
```

### 4.3 模拟器连接

Android Studio 自带模拟器会自动连接 ADB，无需额外配置。

```bash
adb devices
# 应看到类似 emulator-5554 的设备
```

---

## 5. 验证部署

1. 打开 `http://your-server-ip`（或 Nginx 配置的域名）
2. 使用 `.env` 中配置的管理员账号登录
3. 进入 **设备管理** 页面确认设备在线
4. 进入 **LLM 配置** 页面添加大模型 API Key
5. 创建一个简单的测试用例并执行，验证端到端流程

---

## 6. 进程管理（推荐）

使用 supervisor 管理后端进程，确保服务持续运行：

```ini
# /etc/supervisor/conf.d/mobile_vision_api.conf
[program:mobile_vision_api]
command=/path/to/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8080 --workers 4
directory=/path/to/mobile_vision
user=deploy
autostart=true
autorestart=true
stdout_logfile=/var/log/mobile_vision_api.log
stderr_logfile=/var/log/mobile_vision_api.err
```

```ini
# /etc/supervisor/conf.d/mobile_vision_consumer.conf
[program:mobile_vision_consumer]
command=/path/to/venv/bin/python funboost_cli_user.py consume all
directory=/path/to/mobile_vision
user=deploy
autostart=true
autorestart=true
stdout_logfile=/var/log/mobile_vision_consumer.log
stderr_logfile=/var/log/mobile_vision_consumer.err
```

---

## 7. 常见问题

**Q: MySQL 连接报错 `Authentication plugin 'caching_sha2_password'`**

确保 MySQL 8.0+ 使用原生密码认证，或在 `.env` 中配置正确的连接参数。

**Q: ADB 报错 `device unauthorized`**

检查 Android 设备上是否已授权 USB 调试，重新插拔并确认授权弹窗。

**Q: 前端页面空白/API 请求 404**

检查 Nginx 反向代理配置是否正确，尤其 `location /api/` 的 `proxy_pass` 结尾是否有 `/`。

**Q: 任务队列不消费**

确认 Redis 已启动，且 `funboost_cli_user.py` 已运行。检查日志中是否有 Redis 连接错误。
