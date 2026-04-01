# Visit Steven Desk5090

Web-based system monitoring and terminal access dashboard.

## 启动方式

**后端:**
```bash
cd backend
source .venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000
```

**前端:**
```bash
cd frontend
npm install

# 默认使用 http://localhost:8000
npm run dev

# 或指定后端地址（IP 变化时使用）
BACKEND_URL=http://192.168.101.21:8000 npm run dev
```

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `BACKEND_URL` | http://localhost:8000 | 后端 API 地址 |

## IP/网段变化处理

当机器 IP 或网段变化时：

1. 检查后端是否仍在运行：`curl http://localhost:8000/api/health`
2. 修改前端启动命令中的 `BACKEND_URL` 为新的后端地址
3. 重启前端服务

**注意：此应用需要收集宿主机硬件信息（温度、功耗、进程等），必须在本地运行，不支持 Docker。**
