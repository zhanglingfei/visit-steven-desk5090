# Ngrok 安全部署指南

## 已实施的安全加固

### 1. JWT 密钥 (✅ 已完成)
- 使用 `openssl rand -hex 32` 生成强密钥
- 存储在 `.env` 文件中

### 2. Terminal 安全加固 (✅ 已完成)
新增 `terminal_security.py` 提供：
- IP 白名单检查
- 速率限制 (每5分钟最多10次连接)
- 命令黑名单 (阻止危险命令)
- 敏感文件访问阻止
- 会话日志记录

### 3. CORS 限制 (✅ 已完成)
- 从 `allow_origins=["*"]` 改为特定域名列表
- 通过环境变量 `ALLOWED_ORIGINS` 配置

### 4. 安全响应头 (✅ 已完成)
- X-Content-Type-Options: nosniff
- X-Frame-Options: DENY
- X-XSS-Protection: 1; mode=block
- Strict-Transport-Security (HSTS)
- Content-Security-Policy

### 5. HTTPS 重定向 (✅ 已完成)
- 检测 `X-Forwarded-Proto` 头
- HTTP 请求自动重定向到 HTTPS

### 6. 路径遍历防护 (✅ 已完成)
- 前端文件服务使用 `resolve()` 和 `relative_to()` 检查
- 阻止访问 `../../../etc/passwd` 等路径

---

## 部署步骤

### 1. 配置环境变量

编辑 `.env` 文件：

```bash
# 1. 设置强 JWT 密钥 (已设置)
JWT_SECRET_KEY=4c72cb21afa05823288d9274187dcb6ea2135e14cf74d5ff0326a18e3085fb8b

# 2. 配置 ngrok 域名 (启动 ngrok 后获得)
ALLOWED_ORIGINS=https://xxxx-xx-xx-xxx-xx.ngrok-free.app,http://localhost:5173

# 3. 配置 Terminal IP 白名单 (强烈推荐)
# 你的家庭/办公室公网 IP
ALLOWED_TERMINAL_IPS=203.0.113.1,198.51.100.2
```

### 2. 获取你的公网 IP

```bash
# 方法1: 使用 curl
curl ifconfig.me

# 方法2: 使用 ipinfo.io
curl ipinfo.io/ip
```

### 3. 启动服务

```bash
# 1. 确保在后端目录
cd /home/steven-desk5090/visit-steven-desk5090/backend

# 2. 激活虚拟环境
source .venv/bin/activate

# 3. 启动后端
uvicorn main:app --host 0.0.0.0 --port 8765
```

在另一个终端：

```bash
# 4. 启动 ngrok
ngrok http 8765
```

### 4. 更新 CORS 配置

ngrok 启动后会显示类似：
```
Forwarding  https://abcd-123-45-67-89.ngrok-free.app -> http://localhost:8765
```

更新 `.env`：
```bash
ALLOWED_ORIGINS=https://abcd-123-45-67-89.ngrok-free.app
```

然后重启后端服务。

---

## Terminal IP 白名单配置

### 为什么需要？
Terminal 是最危险的组件。IP 白名单确保只有特定网络可以访问。

### 配置方法

1. **获取你的 IP**：
   ```bash
   curl ifconfig.me
   # 输出: 203.0.113.45
   ```

2. **更新 .env**：
   ```bash
   ALLOWED_TERMINAL_IPS=203.0.113.45
   ```

3. **多个 IP**：
   ```bash
   ALLOWED_TERMINAL_IPS=203.0.113.45,198.51.100.10
   ```

4. **重启服务生效**

### 如果 IP 变化？
- 使用动态 DNS 服务
- 或使用 VPN (Tailscale/WireGuard) 替代 ngrok

---

## 监控和日志

### Terminal 日志位置
```
backend/logs/terminal.log          # 实时日志
backend/logs/session_*.json        # 会话命令记录
```

### 查看日志
```bash
# 实时查看
tail -f backend/logs/terminal.log

# 查看会话记录
cat backend/logs/session_xxxx_1234567890.json
```

### 日志内容示例
```json
[
  {
    "timestamp": "2026-03-26T10:30:00+00:00",
    "session_id": "uuid-here",
    "username": "admin",
    "command": "ls -la"
  }
]
```

---

## 安全命令黑名单

已阻止的危险命令模式：
- `rm -rf /` - 删除整个系统
- `dd if=... of=/dev/...` - 直接磁盘写入
- `mkfs.*` - 格式化文件系统
- `fdisk /dev/...` - 分区操作
- `wget ... | bash` / `curl ... | bash` - 管道到 shell
- `nc -l` / `netcat -l` / `ncat -l` - 网络监听
- `python -m http.server` - 启动 HTTP 服务器
- `ssh ...@...` / `scp ...:` - SSH 连接

---

## 应急响应

### 发现可疑活动

1. **立即阻止 IP**：
   ```python
   # 在 Python 控制台
   from app.services.terminal_security import terminal_security
   terminal_security.block_ip("可疑IP地址")
   ```

2. **查看活跃会话**：
   ```bash
   ps aux | grep bash
   ```

3. **终止所有 Terminal 会话**：
   ```python
   from app.services.terminal_service import terminal_manager
   import asyncio
   asyncio.run(terminal_manager.cleanup_all())
   ```

4. **检查系统完整性**：
   ```bash
   # 检查新用户
   cat /etc/passwd | grep -v nologin

   # 检查 SSH 密钥
   cat ~/.ssh/authorized_keys

   # 检查计划任务
   crontab -l
   ls /etc/cron.d/
   ```

---

## 替代方案

如果觉得 Terminal 风险太高，考虑：

### 方案 1: VPN 替代
使用 Tailscale/WireGuard，不公开暴露任何端口。

### 方案 2: 只读仪表板
移除 Terminal 功能，只保留监控数据查看。

### 方案 3: 跳转主机
使用一个专门的 VPS 作为跳转主机，不直接暴露生产机器。

---

## 检查清单

部署前确认：
- [ ] JWT_SECRET_KEY 已更改为强密钥
- [ ] ALLOWED_ORIGINS 包含正确的 ngrok 域名
- [ ] ALLOWED_TERMINAL_IPS 已配置你的 IP
- [ ] 测试 Terminal 连接正常
- [ ] 测试命令黑名单生效
- [ ] 检查日志文件生成正常
- [ ] 确认 HTTPS 重定向工作

---

## 故障排除

### CORS 错误
```
Access to fetch at '...' from origin '...' has been blocked
```
**解决**: 更新 `ALLOWED_ORIGINS` 包含前端域名

### Terminal 连接被拒绝
```
WebSocket connection failed: IP not allowed
```
**解决**: 将你的 IP 添加到 `ALLOWED_TERMINAL_IPS`

### 命令被阻止
```
[SECURITY] Command pattern not allowed
```
**正常**: 这是安全功能在工作，检查 `terminal_security.py` 中的 `BLOCKED_PATTERNS`
