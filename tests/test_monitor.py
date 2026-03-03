#!/usr/bin/env python3
"""
OpenClaw LLM Monitor 单元测试
"""

import unittest
import sys
import os
import json
import tempfile
from pathlib import Path
from datetime import datetime

# 添加项目目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openclaw_monitor import (
    calculate_cost, 
    get_model_pricing,
    LogParser,
    Database,
    MODEL_PRICING
)


class TestModelPricing(unittest.TestCase):
    """测试模型价格配置"""
    
    def test_kimi_pricing(self):
        """测试 Kimi 模型价格"""
        pricing = get_model_pricing('k2.5')
        self.assertEqual(pricing['input'], 4.00)
        self.assertEqual(pricing['output'], 21.00)
        self.assertEqual(pricing['currency'], 'CNY')
        self.assertEqual(pricing['symbol'], '¥')
    
    def test_openai_pricing(self):
        """测试 OpenAI 模型价格"""
        pricing = get_model_pricing('gpt-4o')
        self.assertEqual(pricing['input'], 2.50)
        self.assertEqual(pricing['output'], 10.00)
        self.assertEqual(pricing['currency'], 'USD')
        self.assertEqual(pricing['symbol'], '$')
    
    def test_default_pricing(self):
        """测试默认价格"""
        pricing = get_model_pricing('unknown-model')
        self.assertEqual(pricing['input'], 0.50)
        self.assertEqual(pricing['output'], 2.00)


class TestCostCalculation(unittest.TestCase):
    """测试费用计算"""
    
    def test_kimi_cost_calculation(self):
        """测试 Kimi 费用计算"""
        result = calculate_cost('k2.5', 1000000, 1000000, 0, 0)
        self.assertEqual(result['input'], 4.00)
        self.assertEqual(result['output'], 21.00)
        self.assertEqual(result['total'], 25.00)
        self.assertEqual(result['currency'], 'CNY')
    
    def test_cost_with_cache(self):
        """测试带 Cache 的费用计算"""
        result = calculate_cost('k2.5', 1000000, 1000000, 1000000, 0)
        self.assertEqual(result['input'], 4.00)
        self.assertEqual(result['output'], 21.00)
        self.assertEqual(result['cache_read'], 0.70)
        self.assertEqual(result['total'], 25.70)
    
    def test_openai_cost_calculation(self):
        """测试 OpenAI 费用计算"""
        result = calculate_cost('gpt-4o', 1000000, 1000000, 0, 0)
        self.assertEqual(result['input'], 2.50)
        self.assertEqual(result['output'], 10.00)
        self.assertEqual(result['total'], 12.50)
        self.assertEqual(result['currency'], 'USD')


class TestLogParser(unittest.TestCase):
    """测试日志解析器"""
    
    def setUp(self):
        """创建临时测试文件"""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_file = Path(self.temp_dir.name) / "test_session.jsonl"
    
    def tearDown(self):
        """清理临时文件"""
        self.temp_dir.cleanup()
    
    def test_parse_valid_event(self):
        """测试解析有效事件"""
        event = {
            "type": "message",
            "id": "test-123",
            "timestamp": "2026-03-03T10:00:00Z",
            "message": {
                "role": "assistant",
                "api": "anthropic-messages",
                "provider": "kimi-coding",
                "model": "k2.5",
                "usage": {
                    "input": 1000,
                    "output": 100,
                    "totalTokens": 1100,
                    "cacheRead": 500,
                    "cacheWrite": 0,
                    "cost": {"total": 0}
                },
                "stopReason": "stop"
            }
        }
        
        with open(self.test_file, 'w') as f:
            f.write(json.dumps(event) + '\n')
        
        calls = LogParser.parse_session_file(self.test_file)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0].model, 'k2.5')
        self.assertEqual(calls[0].input_tokens, 1000)
        self.assertEqual(calls[0].output_tokens, 100)
        self.assertEqual(calls[0].cache_read_tokens, 500)
    
    def test_parse_invalid_event(self):
        """测试解析无效事件"""
        event = {
            "type": "message",
            "message": {
                "role": "user"  # 不是 assistant，应该被忽略
            }
        }
        
        with open(self.test_file, 'w') as f:
            f.write(json.dumps(event) + '\n')
        
        calls = LogParser.parse_session_file(self.test_file)
        self.assertEqual(len(calls), 0)
    
    def test_parse_empty_file(self):
        """测试解析空文件"""
        with open(self.test_file, 'w') as f:
            f.write('')
        
        calls = LogParser.parse_session_file(self.test_file)
        self.assertEqual(len(calls), 0)


class TestDatabase(unittest.TestCase):
    """测试数据库操作"""
    
    def setUp(self):
        """创建临时数据库"""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test.db"
        self.db = Database(self.db_path)
    
    def tearDown(self):
        """清理临时数据库"""
        self.temp_dir.cleanup()
    
    def test_database_init(self):
        """测试数据库初始化"""
        self.assertTrue(self.db_path.exists())
    
    def test_insert_and_get_stats(self):
        """测试插入记录和获取统计"""
        from dataclasses import dataclass
        from typing import Optional
        
        @dataclass
        class TestCall:
            id: str
            timestamp: datetime
            session_id: str
            provider: str
            model: str
            input_tokens: int
            output_tokens: int
            cache_read_tokens: int
            cache_write_tokens: int
            total_tokens: int
            actual_cost: Optional[float]
            estimated_cost: float
            estimated_cost_breakdown: dict
            latency_ms: Optional[int]
            status: str
            error_msg: Optional[str] = None
        
        call = TestCall(
            id="test-1",
            timestamp=datetime.now(),
            session_id="session-1",
            provider="kimi-coding",
            model="k2.5",
            input_tokens=1000,
            output_tokens=100,
            cache_read_tokens=500,
            cache_write_tokens=0,
            total_tokens=1600,
            actual_cost=None,
            estimated_cost=4.5,
            estimated_cost_breakdown={'input': 4.0, 'output': 0.5, 'cache_read': 0.35, 'cache_write': 0, 'total': 4.5},
            latency_ms=None,
            status="success"
        )
        
        self.db.insert_call(call)
        
        # 获取今日统计
        today = datetime.now().strftime('%Y-%m-%d')
        stats = self.db.get_stats(today)
        
        self.assertEqual(stats['total_calls'], 1)
        self.assertEqual(stats['input_tokens'], 1000)
        self.assertEqual(stats['output_tokens'], 100)


class TestModelCoverage(unittest.TestCase):
    """测试模型覆盖度"""
    
    def test_all_models_have_required_fields(self):
        """测试所有模型都有必需字段"""
        required_fields = ['input', 'output', 'cache_read', 'cache_write', 'currency', 'symbol']
        
        for model_name, pricing in MODEL_PRICING.items():
            for field in required_fields:
                self.assertIn(field, pricing, f"Model {model_name} missing field: {field}")
    
    def test_price_positive(self):
        """测试价格为正数"""
        for model_name, pricing in MODEL_PRICING.items():
            self.assertGreater(pricing['input'], 0, f"Model {model_name} input price <= 0")
            self.assertGreater(pricing['output'], 0, f"Model {model_name} output price <= 0")


def run_tests():
    """运行所有测试"""
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试类
    suite.addTests(loader.loadTestsFromTestCase(TestModelPricing))
    suite.addTests(loader.loadTestsFromTestCase(TestCostCalculation))
    suite.addTests(loader.loadTestsFromTestCase(TestLogParser))
    suite.addTests(loader.loadTestsFromTestCase(TestDatabase))
    suite.addTests(loader.loadTestsFromTestCase(TestModelCoverage))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 返回测试结果
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)
