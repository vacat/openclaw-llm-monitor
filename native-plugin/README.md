# LLM Monitor Plugin - Native Version

## 🎯 功能特性

- 🔌 **原生集成**: 作为 OpenClaw 插件运行
- 📊 **实时监控**: Hook LLM 调用，实时记录
- 💰 **费用计算**: 支持 50+ 模型，自动计算费用
- 🗄️ **数据存储**: SQLite 数据库，与简单版本兼容
- 🌐 **Web Dashboard**: 可视化监控面板
- 🛠️ **Tools**: 提供 LLM 统计工具
- 💻 **CLI**: 命令行查看统计

## 📁 项目结构

```
llm-monitor/
├── index.ts                 # 主插件代码
├── openclaw.plugin.json     # 插件配置
├── package.json             # 依赖配置
├── tsconfig.json            # TypeScript 配置
├── jest.config.js           # Jest 测试配置
├── dashboard/               # Web Dashboard
│   └── index.html           # 监控面板
├── tests/                   # 单元测试
│   └── index.test.ts
└── DEVELOPMENT.md           # 开发文档
```

## 🚀 快速开始

### 1. 安装依赖

```bash
cd /root/.openclaw/extensions/llm-monitor
npm install
```

### 2. 编译插件

```bash
npm run build
```

### 3. 运行测试

```bash
npm test
```

### 4. 启用插件

在 OpenClaw 配置中启用：

```json
{
  "plugins": {
    "allow": ["llm-monitor"]
  }
}
```

## 📊 使用方法

### Web Dashboard

访问: `http://localhost:18789/llm-monitor`

### CLI 命令

```bash
openclaw llm-monitor              # 查看今日统计
openclaw llm-monitor -d 2026-03-03  # 查看指定日期
```

### Tools

```typescript
// 获取今日统计
const today = await tools.llm_monitor_today();

// 获取指定日期统计
const stats = await tools.llm_monitor_date({ date: "2026-03-03" });
```

## 🔧 配置选项

```json
{
  "llm-monitor": {
    "enabled": true,
    "dbPath": "~/.openclaw/monitor/llm_stats.db",
    "alertThreshold": {
      "dailyTokens": 10000000,
      "dailyCost": 50
    }
  }
}
```

## 📈 Dashboard 功能

- 📊 实时调用统计
- 📈 每小时调用分布图
- 🥧 模型使用分布
- 📋 最近调用记录
- 💰 费用估算
- 💡 Cache 节省分析

## 🧪 测试

```bash
# 运行所有测试
npm test

# 覆盖率报告
npm run test:coverage

# 监视模式
npm run test:watch
```

## 📝 开发计划

- [x] 基础插件框架
- [x] LLM 调用 Hook
- [x] SQLite 数据库
- [x] 费用计算
- [x] Tools 注册
- [x] CLI 命令
- [x] Web Dashboard
- [x] 单元测试
- [ ] 告警系统
- [ ] 数据导出
- [ ] 多用户支持

## 🤝 与简单版本对比

| 特性 | 简单版本 | 原生插件 |
|------|---------|---------|
| 实现 | Python + 文件监听 | TypeScript + Hook API |
| 实时性 | 依赖文件写入 | 实时拦截 |
| 集成度 | 独立运行 | 内嵌 OpenClaw |
| Web UI | ❌ | ✅ Dashboard |
| 工具调用 | CLI | Tools + CLI + Web |
| 告警 | ❌ | 计划中 |

## 📄 License

MIT
