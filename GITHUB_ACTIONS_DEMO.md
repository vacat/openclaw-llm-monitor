# GitHub Actions 真实使用演示

## 📍 访问地址

打开浏览器访问：
```
https://github.com/vacat/openclaw-llm-monitor/actions
```

---

## 🖥️ 界面说明

### 1. Actions 主页面

```
┌─────────────────────────────────────────────────────────┐
│  openclaw-llm-monitor / Actions                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  📊 Daily LLM Stats Report    │  🚨 Alert on High Usage │
│  ──────────────────────────   │  ─────────────────────  │
│  Scheduled · workflow file    │  Scheduled · workflow   │
│  Runs every day at 00:00 UTC  │  Runs every 6 hours     │
│                                                         │
│  [Run workflow ▼]             │  [Run workflow ▼]       │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 2. 点击 "Run workflow" 后

```
┌─────────────────────────────────┐
│  Run workflow                   │
├─────────────────────────────────┤
│  Use workflow from              │
│  [ main ▼]                      │
│                                 │
│  [Run workflow] [Cancel]        │
└─────────────────────────────────┘
```

### 3. 工作流执行中

```
┌─────────────────────────────────────────────────────────┐
│  📊 Daily LLM Stats Report #1                           │
├─────────────────────────────────────────────────────────┤
│  Status: 🟡 In progress                                 │
│  Started: 2 minutes ago                                 │
│                                                         │
│  Jobs:                                                  │
│  ├─ generate-report (running)                           │
│  │   ├─ 🟢 Checkout repository          2s              │
│  │   ├─ 🟢 Set up Python                5s              │
│  │   ├─ 🟢 Install dependencies         8s              │
│  │   ├─ 🟡 Generate daily report        running...      │
│  │   ├─ ⬜ Upload report                 pending        │
│  │   └─ ⬜ Create Issue with report      pending        │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

### 4. 执行完成

```
┌─────────────────────────────────────────────────────────┐
│  📊 Daily LLM Stats Report #1                           │
├─────────────────────────────────────────────────────────┤
│  Status: 🟢 Success                                     │
│  Duration: 1m 23s                                       │
│                                                         │
│  Jobs:                                                  │
│  ├─ generate-report                                     │
│  │   ├─ 🟢 Checkout repository          2s              │
│  │   ├─ 🟢 Set up Python                5s              │
│  │   ├─ 🟢 Install dependencies         8s              │
│  │   ├─ 🟢 Generate daily report        45s             │
│  │   ├─ 🟢 Upload report                 3s              │
│  │   └─ 🟢 Create Issue with report      20s             │
│                                                         │
│  Artifacts (1):                                         │
│  📦 daily-report-123456789                              │
│     [Download]                                          │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 📋 生成的 GitHub Issue

工作流会自动创建一个 Issue，效果如下：

```
┌─────────────────────────────────────────────────────────┐
│  📊 Daily LLM Stats - 2026-03-03                        │
│  Labels: daily-report, automated                        │
├─────────────────────────────────────────────────────────┤
│  ## Daily Report                                        │
│                                                         │
│  ```                                                    │
│  📊 LLM 调用统计 (2026-03-03)                           │
│  ====================================================   │
│  总调用次数:    131                                     │
│  总 Token:      8,760,420                               │
│    ├─ Input:    1,359,655                               │
│    └─ Output:   44,605                                  │
│                                                         │
│  💰 费用统计:                                           │
│    [CNY]                                                │
│    实际计费: ¥11.5246                                   │
│      ├─ Input:       ¥5.4386                            │
│      ├─ Output:      ¥0.9367                            │
│      ├─ Cache Read:  ¥5.1493                            │
│      └─ Cache Write: ¥0.0000                            │
│                                                         │
│    💡 Cache 节省分析:                                   │
│      如果没有 Cache 需支付: ¥29.4246                    │
│      Cache Read 实际支付:   ¥5.1493                     │
│      节省费用:              ¥24.2753 (82.5%)            │
│  ```                                                    │
│                                                         │
│  Generated at: 2026-03-03T00:00:00Z                     │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 🔄 触发方式对比

| 触发方式 | 频率 | 用途 |
|---------|------|------|
| **Scheduled** | 每天 00:00 UTC | 自动生成日报 |
| **Manual** | 随时 | 测试或紧急生成报表 |
| **Push** | 代码推送时 | CI/CD 流程 |
| **API** | 按需 | 外部系统集成 |

---

## 📝 工作流文件详解

```yaml
name: Daily LLM Stats Report      # 工作流名称

on:                               # 触发条件
  schedule:                       # 定时触发
    - cron: '0 0 * * *'          # 每天 UTC 00:00
  workflow_dispatch:              # 允许手动触发

jobs:                             # 任务定义
  generate-report:                # 任务名称
    runs-on: ubuntu-latest        # 运行环境
    
    steps:                        # 执行步骤
      - name: Checkout            # 步骤1: 检出代码
        uses: actions/checkout@v4
        
      - name: Setup Python        # 步骤2: 设置 Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'
        
      - name: Install deps        # 步骤3: 安装依赖
        run: pip install watchdog
        
      - name: Generate report     # 步骤4: 生成报告
        run: python openclaw_monitor.py stats --today
        
      - name: Upload artifact     # 步骤5: 上传产物
        uses: actions/upload-artifact@v4
        
      - name: Create Issue        # 步骤6: 创建 Issue
        uses: actions/github-script@v7
```

---

## 🎯 实际操作建议

由于网络问题无法直接演示，你可以：

1. **等待网络恢复后**，访问 https://github.com/vacat/openclaw-llm-monitor/actions
2. 点击 **"Daily LLM Stats Report"**
3. 点击 **"Run workflow"** → **"Run workflow"**
4. 等待执行完成，查看生成的 Issue

或者使用 GitHub CLI（如果已配置）：
```bash
gh workflow run daily-report.yml --repo vacat/openclaw-llm-monitor
```
