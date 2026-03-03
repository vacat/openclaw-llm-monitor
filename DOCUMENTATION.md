# OpenClaw LLM Monitor - 简单版本文档

## 📖 项目简介

OpenClaw LLM Monitor 是一个轻量级的 Python 工具，用于实时监控 OpenClaw 的大模型调用情况，包括：

- 📊 调用次数统计
- 💰 Token 使用量和费用估算
- 💾 Cache 命中分析
- 📈 多维度数据展示

## 🎯 核心特性

| 特性 | 说明 |
|------|------|
| **实时监控** | 监听 OpenClaw 会话日志，自动采集数据 |
| **多 Agent 支持** | 可同时监控多个 agent 的调用情况 |
| **多币种计费** | 支持 USD/CNY，自动识别模型定价币种 |
| **Cache 分析** | 单独计算 Cache Read/Write 费用，展示节省效果 |
| **50+ 模型** | 覆盖国内外主流大模型 |
| **本地存储** | SQLite 数据库，数据完全本地保存 |

## 📦 安装

### 一键安装

```bash
curl -sSL https://raw.githubusercontent.com/vacat/openclaw-llm-monitor/main/install.sh | bash
```

### 手动安装

```bash
# 克隆仓库
git clone https://github.com/vacat/openclaw-llm-monitor.git
cd openclaw-llm-monitor

# 安装依赖
pip install watchdog

# 运行测试
python3 tests/test_monitor.py
```

## 🚀 快速开始

### 1. 启动监控

```bash
# 监控默认 main agent
openclaw-monitor monitor

# 监控多个 agent
openclaw-monitor monitor -a main,agent2

# 监控所有 agent
openclaw-monitor monitor -a all

# 监控指定目录
openclaw-monitor monitor -d /path/to/sessions
```

### 2. 查看统计

```bash
# 查看今日统计
openclaw-monitor stats

# 查看指定日期
openclaw-monitor stats --date 2026-03-03
```

### 3. 查看帮助

```bash
openclaw-monitor --help
openclaw-monitor monitor --help
openclaw-monitor stats --help
```

## 📊 输出示例

```
📊 LLM 调用统计 (2026-03-03)
============================================================
总调用次数:    131
总 Token:      8,760,420
  ├─ Input:    1,359,655
  └─ Output:   44,605

💰 费用统计:

  估算费用（按模型定价币种）:

    [CNY]
    实际计费: ¥11.5246
      ├─ Input:       ¥5.4386 (1,359,655 tokens)
      ├─ Output:      ¥0.9367 (44,605 tokens)
      ├─ Cache Read:  ¥5.1493 (7,356,160 tokens)
      └─ Cache Write: ¥0.0000 (0 tokens)

    💡 Cache 节省分析:
      如果没有 Cache 需支付: ¥29.4246
      Cache Read 实际支付:   ¥5.1493
      节省费用:              ¥24.2753 (82.5%)

按模型分布:
  k2p5: 131 calls (8,760,420 tokens, est: ¥11.5246 CNY)

按会话分布 (Top 10):
  e69f0739-2b88-43a0-a...: 124 calls (8,721,313 tokens)
```

## 💰 支持的模型价格

### 国际模型 (USD)

| 厂商 | 模型 | Input | Output | Cache Read |
|------|------|-------|--------|------------|
| OpenAI | gpt-4o | $2.50 | $10.00 | $1.25 |
| Anthropic | claude-3-opus | $15.00 | $75.00 | $1.50 |
| Google | gemini-1.5-pro | $1.25 | $5.00 | $0.625 |

### 国内模型 (CNY)

| 厂商 | 模型 | Input | Output | Cache Read |
|------|------|-------|--------|------------|
| Kimi | k2.5 | ¥4.00 | ¥21.00 | ¥0.70 |
| 阿里云 | qwen-max | ¥2.00 | ¥6.00 | ¥1.00 |
| DeepSeek | deepseek-v3 | ¥2.00 | ¥8.00 | ¥1.00 |

> 完整列表见 [MODELS.md](MODELS.md)

## 🏗️ 项目结构

```
openclaw-llm-monitor/
├── openclaw_monitor.py      # 主程序
├── install.sh               # 一键安装脚本
├── README.md                # 项目文档
├── MODELS.md                # 模型价格表
├── USAGE.md                 # 使用指南
├── tests/                   # 单元测试
│   ├── test_monitor.py
│   └── README.md
└── .github/workflows/       # GitHub Actions
    ├── daily-report.yml
    └── alert.yml
```

## 🧪 测试

```bash
# 运行所有测试
python3 tests/test_monitor.py

# 预期输出
Ran 13 tests in 0.021s
OK
```

## 🔧 高级用法

### 自定义查询

```sql
-- 查看最近 10 次调用
SELECT * FROM llm_calls ORDER BY timestamp DESC LIMIT 10;

-- 按小时统计
SELECT strftime('%H', timestamp) as hour, 
       COUNT(*) as calls, 
       SUM(total_tokens) as tokens
FROM llm_calls 
WHERE date(timestamp) = date('now')
GROUP BY hour;
```

### 数据备份

```bash
# 数据库位置
~/.openclaw/monitor/llm_stats.db

# 备份
cp ~/.openclaw/monitor/llm_stats.db ~/backup/
```

## 📝 配置说明

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `OPENCLAW_MONITOR_DB` | 数据库路径 | `~/.openclaw/monitor/llm_stats.db` |
| `OPENCLAW_MONITOR_LOG` | 日志级别 | `INFO` |

### 价格配置

如需更新模型价格，编辑 `openclaw_monitor.py` 中的 `MODEL_PRICING` 字典。

## 🐛 故障排查

### 常见问题

**Q: 监控启动后没有数据？**
A: 检查 OpenClaw 会话目录是否存在 `.jsonl` 文件

**Q: 费用计算不准确？**
A: 模型价格可能已更新，请检查 `MODEL_PRICING` 配置

**Q: 如何监控多个 agent？**
A: 使用 `-a all` 或 `-a agent1,agent2`

## 🗺️ 路线图

### 简单版本（当前）
- ✅ 基础监控功能
- ✅ 多 agent 支持
- ✅ 费用计算
- ✅ 单元测试

### 原生插件版本（计划中）
- ⏳ OpenClaw Extension API 集成
- ⏳ Web Dashboard UI
- ⏳ 实时告警系统
- ⏳ 更精确的调用拦截

## 🤝 贡献

欢迎提交 Issue 和 PR！

## 📄 License

MIT
