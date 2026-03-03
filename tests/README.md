# OpenClaw LLM Monitor 测试

## 运行测试

### 运行所有测试
```bash
cd /root/.openclaw/monitor
python3 tests/test_monitor.py
```

### 使用 pytest 运行
```bash
cd /root/.openclaw/monitor
pytest tests/ -v
```

## 测试覆盖

### 1. 模型价格测试 (TestModelPricing)
- ✅ Kimi 模型价格
- ✅ OpenAI 模型价格
- ✅ 默认价格

### 2. 费用计算测试 (TestCostCalculation)
- ✅ 基础费用计算
- ✅ 带 Cache 的费用计算
- ✅ OpenAI 费用计算

### 3. 日志解析测试 (TestLogParser)
- ✅ 解析有效事件
- ✅ 解析无效事件
- ✅ 解析空文件

### 4. 数据库测试 (TestDatabase)
- ✅ 数据库初始化
- ✅ 插入记录
- ✅ 获取统计

### 5. 模型覆盖度测试 (TestModelCoverage)
- ✅ 所有模型字段完整性
- ✅ 价格正数检查

## 添加新测试

在 `tests/test_monitor.py` 中添加新的测试类：

```python
class TestNewFeature(unittest.TestCase):
    def test_something(self):
        self.assertEqual(1 + 1, 2)
```
