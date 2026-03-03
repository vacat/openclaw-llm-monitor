# LLM Monitor 插件调试指南

## 🔍 查看日志

### 1. 实时查看日志

```bash
# 查看所有日志（实时）
openclaw logs --follow

# 只看 LLM Monitor 相关日志
openclaw logs -f | grep -i "llm-monitor"

# 保存到文件
openclaw logs -f > monitor.log 2>&1 &
```

### 2. 查看日志文件

```bash
# 默认日志位置
cat /tmp/openclaw/openclaw-$(date +%Y-%m-%d).log

# 查看最近 100 行
tail -100 /tmp/openclaw/openclaw-$(date +%Y-%m-%d).log

# 搜索错误
grep -i "error\|fail\|exception" /tmp/openclaw/openclaw-*.log
```

### 3. 调整日志级别

编辑 `~/.openclaw/config.json`：

```json
{
  "logging": {
    "level": "debug",
    "consoleLevel": "debug",
    "file": "/tmp/openclaw/openclaw.log"
  }
}
```

日志级别：`trace` > `debug` > `info` > `warn` > `error`

## 🐛 插件调试

### 1. 检查插件是否加载

```bash
# 查看 OpenClaw 状态
openclaw status

# 查看加载的扩展
openclaw gateway status
```

### 2. 手动测试插件

```bash
# 进入插件目录
cd /usr/lib/node_modules/openclaw/extensions/llm-monitor

# 检查文件权限
ls -la index.ts openclaw.plugin.json

# 验证 JSON 配置
cat openclaw.plugin.json | python3 -m json.tool
```

### 3. 测试数据库连接

```bash
# 检查数据库文件
ls -la ~/.openclaw/monitor/llm_stats.db

# 使用 sqlite3 查看数据
sqlite3 ~/.openclaw/monitor/llm_stats.db ".tables"
sqlite3 ~/.openclaw/monitor/llm_stats.db "SELECT COUNT(*) FROM llm_calls;"
```

### 4. 测试 Dashboard

```bash
# 检查端口监听
netstat -tlnp | grep 18789

# 测试 HTTP 接口
curl http://localhost:18789/llm-monitor
curl http://localhost:18789/api/llm-monitor/stats
```

## 🚨 常见问题排查

### 问题 1: 插件未加载

**症状**: `openclaw llm-monitor` 提示命令不存在

**排查步骤**:
```bash
# 1. 检查插件目录
ls /usr/lib/node_modules/openclaw/extensions/llm-monitor/

# 2. 检查配置文件
cat ~/.openclaw/config.json | grep -A5 llm-monitor

# 3. 重启 gateway
openclaw gateway restart

# 4. 查看启动日志
openclaw logs -f | grep -i "llm-monitor\|plugin"
```

### 问题 2: 数据库错误

**症状**: 日志中出现 `SQLITE_ERROR` 或 `database is locked`

**解决方案**:
```bash
# 1. 检查数据库权限
ls -la ~/.openclaw/monitor/

# 2. 修复数据库
sqlite3 ~/.openclaw/monitor/llm_stats.db ".recover" | sqlite3 ~/.openclaw/monitor/llm_stats.db.fixed
mv ~/.openclaw/monitor/llm_stats.db ~/.openclaw/monitor/llm_stats.db.bak
mv ~/.openclaw/monitor/llm_stats.db.fixed ~/.openclaw/monitor/llm_stats.db

# 3. 或者删除重建
rm ~/.openclaw/monitor/llm_stats.db
```

### 问题 3: Dashboard 无法访问

**症状**: 浏览器访问 `http://localhost:18789/llm-monitor` 报错

**排查步骤**:
```bash
# 1. 检查路由是否注册
curl -I http://localhost:18789/llm-monitor

# 2. 检查 dashboard 文件
ls -la /usr/lib/node_modules/openclaw/extensions/llm-monitor/dashboard/

# 3. 查看 HTTP 错误日志
openclaw logs -f | grep -i "http\|route\|dashboard"
```

### 问题 4: LLM 调用未被记录

**症状**: 有 LLM 调用但数据库为空

**排查步骤**:
```bash
# 1. 检查 onLlmCall 是否触发
openclaw logs -f | grep -i "recorded call\|llm call"

# 2. 检查配置是否启用
cat ~/.openclaw/config.json | jq '.extensions."llm-monitor".enabled'

# 3. 手动测试插入
cat > /tmp/test_insert.js << 'EOF'
const sqlite3 = require('sqlite3');
const db = new sqlite3.Database(process.env.HOME + '/.openclaw/monitor/llm_stats.db');
db.run("INSERT INTO llm_calls (id, timestamp, session_id, model, total_tokens) VALUES (?, ?, ?, ?, ?)", 
  ['test', new Date().toISOString(), 'test', 'k2.5', 100],
  (err) => { console.log(err || 'OK'); db.close(); }
);
EOF
node /tmp/test_insert.js
```

## 📝 调试技巧

### 1. 添加自定义日志

在 `index.ts` 中添加：

```typescript
// 在关键位置添加日志
api.logger.debug("[LLM Monitor] Debug: something happened", { data });
api.logger.info("[LLM Monitor] Info: normal operation");
api.logger.error("[LLM Monitor] Error: something failed", error);
```

### 2. 使用 console 调试

```typescript
// 临时添加 console 输出
console.log("[DEBUG] Call data:", call);
console.error("[DEBUG] Error:", err);
```

### 3. 启用 Verbose 模式

```bash
# 启动 gateway 时启用详细日志
openclaw gateway --verbose

# 或者
openclaw gateway --ws-log full
```

### 4. 使用调试工具

```bash
# 使用 strace 跟踪系统调用（高级）
strace -f -e trace=file,network openclaw gateway 2>&1 | grep llm-monitor

# 使用 lsof 查看打开的文件
lsof -p $(pgrep -f "openclaw gateway") | grep monitor
```

## 🔧 验证脚本

使用项目自带的验证脚本：

```bash
cd /usr/lib/node_modules/openclaw/extensions/llm-monitor
./verify.sh
```

## 📊 监控指标

```bash
# 查看实时调用数
watch -n 1 'sqlite3 ~/.openclaw/monitor/llm_stats.db "SELECT COUNT(*) FROM llm_calls WHERE date(timestamp) = date(\"now\");"'

# 查看今日费用
sqlite3 ~/.openclaw/monitor/llm_stats.db "SELECT SUM(estimated_cost) FROM llm_calls WHERE date(timestamp) = date('now');"
```
