# OpenClaw LLM Monitor

实时监控 OpenClaw 的大模型调用情况，包括调用次数、token 使用量、费用估算（支持多币种和 Cache 节省分析）。

## 功能特性

- 📊 **实时监控**: 监听 OpenClaw 会话日志，自动采集 LLM 调用数据
- 💰 **多币种计费**: 支持 USD/CNY 等不同模型定价币种
- 💾 **Cache 分析**: 单独计算 Cache Read/Write 费用，展示节省效果
- 📈 **历史统计**: 按天、模型、会话多维度分析
- 🗄️ **本地存储**: SQLite 数据库，支持自定义查询

## 支持的模型价格

### 国际模型 (USD)

| 厂商 | 模型 | Input | Output | Cache Read | 来源 |
|------|------|-------|--------|------------|------|
| **OpenAI** | gpt-4o | $2.50 | $10.00 | $1.25 | Official |
| **OpenAI** | gpt-4o-mini | $0.15 | $0.60 | $0.075 | Official |
| **Anthropic** | claude-3-opus | $15.00 | $75.00 | $1.50 | Official |
| **Anthropic** | claude-3-sonnet | $3.00 | $15.00 | $0.30 | Official |
| **Anthropic** | claude-3-haiku | $0.25 | $1.25 | $0.03 | Official |
| **Google** | gemini-1.5-pro | $1.25 | $5.00 | $0.625 | Official |
| **Google** | gemini-1.5-flash | $0.075 | $0.30 | $0.0375 | Official |

### 国内模型 (CNY)

| 厂商 | 模型 | Input | Output | Cache Read | 来源 |
|------|------|-------|--------|------------|------|
| **Kimi** | k2.5 | ¥4.00 | ¥21.00 | ¥0.70 | Official |
| **Kimi** | moonshot-v1-8k | ¥2.00 | ¥10.00 | ¥0.50 | Official |
| **Kimi** | moonshot-v1-32k | ¥5.00 | ¥20.00 | ¥1.00 | Official |
| **Kimi** | moonshot-v1-128k | ¥10.00 | ¥30.00 | ¥2.00 | Official |
| **阿里云** | qwen-max | ¥2.00 | ¥6.00 | ¥1.00 | Official |
| **阿里云** | qwen-plus | ¥0.80 | ¥2.00 | ¥0.40 | Official |
| **阿里云** | qwen-turbo | ¥0.30 | ¥0.60 | ¥0.15 | Official |
| **阿里云** | qwen2.5-72b | ¥0.50 | ¥1.00 | ¥0.25 | Official |
| **阿里云** | qwen2.5-7b | ¥0.10 | ¥0.20 | ¥0.05 | Official |
| **DeepSeek** | deepseek-chat | ¥1.00 | ¥2.00 | ¥0.50 | Official |
| **DeepSeek** | deepseek-v3 | ¥2.00 | ¥8.00 | ¥1.00 | Official |
| **DeepSeek** | deepseek-r1 | ¥4.00 | ¥16.00 | ¥2.00 | Official |
| **智谱** | glm-4 | ¥0.50 | ¥1.00 | ¥0.25 | Estimated |
| **智谱** | glm-4-flash | ¥0.01 | ¥0.02 | ¥0.005 | Estimated |
| **MiniMax** | abab6.5 | ¥10.00 | ¥20.00 | ¥5.00 | Estimated |
| **百度** | ernie-4.0 | ¥3.00 | ¥9.00 | ¥1.50 | Estimated |
| **百度** | ernie-lite | ¥0.01 | ¥0.01 | ¥0.005 | Estimated |
| **字节** | doubao-pro | ¥2.00 | ¥5.00 | ¥1.00 | Estimated |
| **腾讯** | hunyuan-pro | ¥3.00 | ¥6.00 | ¥1.50 | Estimated |
| **商汤** | sensechat-5 | ¥5.00 | ¥10.00 | ¥2.50 | Estimated |
| **零一万物** | yi-large | ¥2.00 | ¥4.00 | ¥1.00 | Estimated |
| **百川** | baichuan4 | ¥2.00 | ¥4.00 | ¥1.00 | Estimated |
| **阶跃星辰** | step-2 | ¥5.00 | ¥10.00 | ¥2.50 | Estimated |

> **注意**: 
> - **Official**: 官方公开定价
> - **Estimated**: 估算价格（基于市场行情）
> - 价格仅供参考，请以官方最新定价为准

## 安装

```bash
pip install watchdog
```

## 使用方法

### 命令概览

```bash
# 查看帮助
python openclaw_monitor.py --help
python openclaw_monitor.py monitor --help
python openclaw_monitor.py stats --help
```

### 1. 启动实时监控

**监控默认 main agent：**
```bash
python openclaw_monitor.py monitor
```

**监控多个 agent：**
```bash
python openclaw_monitor.py monitor --agents main,agent2,agent3
# 或简写
python openclaw_monitor.py monitor -a main,agent2
```

**监控所有 agent：**
```bash
python openclaw_monitor.py monitor --agents all
# 或简写
python openclaw_monitor.py monitor -a all
```

**监控指定目录：**
```bash
python openclaw_monitor.py monitor --dir /path/to/sessions
# 或简写
python openclaw_monitor.py monitor -d /path/to/sessions
```

### 2. 查看统计信息

**查看今日统计：**
```bash
python openclaw_monitor.py stats --today
```

**查看指定日期：**
```bash
python openclaw_monitor.py stats --date 2026-03-03
```

## 输出示例

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
```

## 数据存储

- 数据库: `~/.openclaw/monitor/llm_stats.db`
- 可直接使用 SQLite 工具查询

## 自定义查询示例

```sql
-- 查看最近 10 次调用
SELECT * FROM llm_calls ORDER BY timestamp DESC LIMIT 10;

-- 按小时统计今天的调用
SELECT strftime('%H', timestamp) as hour, 
       COUNT(*) as calls, 
       SUM(total_tokens) as tokens
FROM llm_calls 
WHERE date(timestamp) = date('now')
GROUP BY hour;

-- 查看错误调用
SELECT * FROM llm_calls WHERE status = 'error';
```

## 项目结构

```
.
├── openclaw_monitor.py  # 主程序
├── README.md            # 说明文档
├── llm_stats.db         # SQLite 数据库 (自动生成)
└── .gitignore          # Git 忽略文件
```

## License

MIT
