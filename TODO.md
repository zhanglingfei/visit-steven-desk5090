# 项目待办事项

## 待完成

### 高优先级

- [ ] **重启后端服务以应用所有修复** (2026-03-29)
  - 修改内容：
    1. `device_service.py` - 设备指纹移除 IP 和浏览器版本
    2. `auth.py` `/me` 端点 - 修复 2FA 状态总是显示为未启用的问题
    3. `auth.py` `/devices` 端点 - 修复设备限制开关状态不正确的问题
  - 重启命令：
    ```bash
    cd /home/steven-desk5090/visit-steven-desk5090/backend && pkill -f "uvicorn main:app" && sleep 2 && source .venv/bin/activate && uvicorn main:app --host 0.0.0.0 --port 8000 &
    ```
  - 注意事项：
    - 已注册设备可能需要重新注册（指纹算法变更）
    - 重启后 Settings 页面应正确显示 2FA 状态和设备限制开关状态

## 已完成

- [x] 修复设备指纹包含 IP 和浏览器版本的问题 (2026-03-29)
- [x] 修复 Settings 页面 2FA 状态显示不正确的问题 (2026-03-29)
- [x] 修复 Settings 页面设备限制开关状态不正确的问题 (2026-03-29)
