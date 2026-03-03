# LLM Monitor Plugin - 开发文档

## 项目结构

```
llm-monitor/
├── index.ts              # 主插件代码
├── openclaw.plugin.json  # 插件配置
├── package.json          # 依赖配置
├── tsconfig.json         # TypeScript 配置
├── jest.config.js        # Jest 测试配置
├── tests/                # 测试目录
│   └── index.test.ts     # 单元测试
└── README.md             # 项目文档
```

## 开发命令

```bash
# 安装依赖
npm install

# 编译 TypeScript
npm run build

# 运行测试
npm test

# 运行测试（监视模式）
npm run test:watch

# 生成测试覆盖率报告
npm run test:coverage

# 代码检查
npm run lint

# 清理编译输出
npm run clean
```

## 测试覆盖

### 已测试功能

- ✅ 费用计算（含 Cache）
- ✅ 数据库操作（插入、查询）
- ✅ 模型价格配置完整性
- ✅ 多记录统计

### 运行测试

```bash
# 所有测试
npm test

# 预期输出
PASS  tests/index.test.ts
  LLM Monitor Plugin
    Cost Calculation
      ✓ should calculate Kimi k2.5 cost correctly
      ✓ should calculate cost with cache
      ✓ should use default pricing for unknown model
      ✓ should calculate OpenAI gpt-4o cost correctly
    Database Operations
      ✓ should insert and retrieve call record
      ✓ should calculate daily stats correctly
      ✓ should handle multiple calls
    Model Pricing
      ✓ should have all required fields for each model
      ✓ should have positive prices

Test Suites: 1 passed, 1 total
Tests:       10 passed, 10 total
```

## 插件架构

### 核心组件

1. **MonitorDatabase**: SQLite 数据库管理
2. **calculateCost**: 费用计算函数
3. **llmMonitorPlugin**: 主插件对象

### 生命周期

```
onInit → register tools/cli → onLlmCall (多次) → onDispose
```

### Hook 点

- `api.onInit`: 初始化数据库
- `api.onLlmCall`: 拦截 LLM 调用
- `api.onDispose`: 清理资源

## 扩展开发

### 添加新模型

在 `MODEL_PRICING` 中添加：

```typescript
"new-model": {
  input: 1.0,
  output: 2.0,
  cacheRead: 0.5,
  cacheWrite: 1.0,
  currency: "CNY",
  symbol: "¥"
}
```

### 添加新工具

```typescript
api.registerTool(
  (ctx) => [
    api.runtime.tools.createTool({
      name: "my_tool",
      description: "My tool description",
      parameters: z.object({}),
      handler: async () => ({ result: "ok" })
    })
  ],
  { names: ["my_tool"] }
);
```

## 调试

```bash
# 开启详细日志
DEBUG=llm-monitor npm test
```
