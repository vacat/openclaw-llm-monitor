#!/usr/bin/env python3
"""
OpenClaw LLM Monitor - 简单文件监听模式
实时监控 OpenClaw 的大模型调用情况
"""

import os
import sys
import json
import time
import sqlite3
import argparse
from datetime import datetime, timedelta
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from dataclasses import dataclass
from typing import Optional, List, Dict
from collections import defaultdict

# 配置
DEFAULT_DB_PATH = Path.home() / ".openclaw" / "monitor" / "llm_stats.db"
SESSIONS_DIR = Path.home() / ".openclaw" / "agents" / "main" / "sessions"

# 模型价格配置 (每 1M tokens)
MODEL_PRICING = {
    # OpenAI 模型 (USD)
    'gpt-4o': {
        'input': 2.50, 'output': 10.00, 'cache_read': 1.25, 'cache_write': 2.50,
        'currency': 'USD', 'symbol': '$'
    },
    'gpt-4o-mini': {
        'input': 0.15, 'output': 0.60, 'cache_read': 0.075, 'cache_write': 0.15,
        'currency': 'USD', 'symbol': '$'
    },
    'gpt-4-turbo': {
        'input': 10.00, 'output': 30.00, 'cache_read': 5.00, 'cache_write': 10.00,
        'currency': 'USD', 'symbol': '$'
    },
    'gpt-4': {
        'input': 30.00, 'output': 60.00, 'cache_read': 15.00, 'cache_write': 30.00,
        'currency': 'USD', 'symbol': '$'
    },
    'gpt-3.5-turbo': {
        'input': 0.50, 'output': 1.50, 'cache_read': 0.25, 'cache_write': 0.50,
        'currency': 'USD', 'symbol': '$'
    },
    
    # Anthropic 模型 (USD)
    'claude-3-opus': {
        'input': 15.00, 'output': 75.00, 'cache_read': 1.50, 'cache_write': 15.00,
        'currency': 'USD', 'symbol': '$'
    },
    'claude-3-sonnet': {
        'input': 3.00, 'output': 15.00, 'cache_read': 0.30, 'cache_write': 3.00,
        'currency': 'USD', 'symbol': '$'
    },
    'claude-3-haiku': {
        'input': 0.25, 'output': 1.25, 'cache_read': 0.03, 'cache_write': 0.25,
        'currency': 'USD', 'symbol': '$'
    },
    'claude-3-5-sonnet': {
        'input': 3.00, 'output': 15.00, 'cache_read': 0.30, 'cache_write': 3.00,
        'currency': 'USD', 'symbol': '$'
    },
    
    # Kimi 模型 (月之暗面) - CNY
    'k2.5': {
        'input': 4.00, 'output': 21.00, 'cache_read': 0.70, 'cache_write': 4.00,
        'currency': 'CNY', 'symbol': '¥'
    },
    'k2p5': {
        'input': 4.00, 'output': 21.00, 'cache_read': 0.70, 'cache_write': 4.00,
        'currency': 'CNY', 'symbol': '¥'
    },
    'kimi-k2.5': {
        'input': 4.00, 'output': 21.00, 'cache_read': 0.70, 'cache_write': 4.00,
        'currency': 'CNY', 'symbol': '¥'
    },
    'kimi-k2-thinking': {
        'input': 4.00, 'output': 16.00, 'cache_read': 1.00, 'cache_write': 4.00,
        'currency': 'CNY', 'symbol': '¥'
    },
    'kimi-k2-turbo': {
        'input': 8.00, 'output': 58.00, 'cache_read': 1.00, 'cache_write': 8.00,
        'currency': 'CNY', 'symbol': '¥'
    },
    'moonshot-v1-8k': {
        'input': 2.00, 'output': 10.00, 'cache_read': 0.50, 'cache_write': 2.00,
        'currency': 'CNY', 'symbol': '¥'
    },
    'moonshot-v1-32k': {
        'input': 5.00, 'output': 20.00, 'cache_read': 1.00, 'cache_write': 5.00,
        'currency': 'CNY', 'symbol': '¥'
    },
    'moonshot-v1-128k': {
        'input': 10.00, 'output': 30.00, 'cache_read': 2.00, 'cache_write': 10.00,
        'currency': 'CNY', 'symbol': '¥'
    },
    
    # Google 模型 (USD)
    'gemini-1.5-pro': {
        'input': 1.25, 'output': 5.00, 'cache_read': 0.625, 'cache_write': 1.25,
        'currency': 'USD', 'symbol': '$'
    },
    'gemini-1.5-flash': {
        'input': 0.075, 'output': 0.30, 'cache_read': 0.0375, 'cache_write': 0.075,
        'currency': 'USD', 'symbol': '$'
    },
    
    # 默认价格 (USD)
    'default': {
        'input': 0.50, 'output': 2.00, 'cache_read': 0.10, 'cache_write': 0.50,
        'currency': 'USD', 'symbol': '$'
    }
}

def get_model_pricing(model: str) -> dict:
    """获取模型定价信息"""
    pricing = MODEL_PRICING.get('default')
    for key in MODEL_PRICING:
        if key in model.lower():
            pricing = MODEL_PRICING[key]
            break
    return pricing

def calculate_cost(model: str, input_tokens: int, output_tokens: int, 
                   cache_read_tokens: int = 0, cache_write_tokens: int = 0) -> dict:
    """计算调用费用，返回详细 breakdown"""
    pricing = get_model_pricing(model)
    symbol = pricing.get('symbol', '$')
    currency = pricing.get('currency', 'USD')
    
    # 计算各项费用
    input_cost = (input_tokens / 1_000_000) * pricing['input']
    output_cost = (output_tokens / 1_000_000) * pricing['output']
    cache_read_cost = (cache_read_tokens / 1_000_000) * pricing['cache_read']
    cache_write_cost = (cache_write_tokens / 1_000_000) * pricing['cache_write']
    
    total_cost = input_cost + output_cost + cache_read_cost + cache_write_cost
    
    return {
        'input': input_cost,
        'output': output_cost,
        'cache_read': cache_read_cost,
        'cache_write': cache_write_cost,
        'total': total_cost,
        'currency': currency,
        'symbol': symbol,
        'breakdown': {
            'input_tokens': input_tokens,
            'output_tokens': output_tokens,
            'cache_read_tokens': cache_read_tokens,
            'cache_write_tokens': cache_write_tokens
        }
    }

@dataclass
class LLMCall:
    """单次 LLM 调用记录"""
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
    actual_cost: Optional[float]  # 实际费用（从API返回）
    estimated_cost: float  # 估算费用（总计）
    estimated_cost_breakdown: dict  # 估算费用明细
    latency_ms: Optional[int]
    status: str
    error_msg: Optional[str] = None

class Database:
    """SQLite 数据库管理"""
    
    def __init__(self, db_path: Path = DEFAULT_DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.init_db()
    
    def init_db(self):
        """初始化数据库表结构"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS llm_calls (
                    id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    provider TEXT,
                    model TEXT,
                    input_tokens INTEGER DEFAULT 0,
                    output_tokens INTEGER DEFAULT 0,
                    cache_read_tokens INTEGER DEFAULT 0,
                    cache_write_tokens INTEGER DEFAULT 0,
                    total_tokens INTEGER DEFAULT 0,
                    actual_cost REAL,
                    estimated_cost REAL DEFAULT 0,
                    estimated_cost_input REAL DEFAULT 0,
                    estimated_cost_output REAL DEFAULT 0,
                    estimated_cost_cache_read REAL DEFAULT 0,
                    estimated_cost_cache_write REAL DEFAULT 0,
                    latency_ms INTEGER,
                    status TEXT,
                    error_msg TEXT
                );
                
                CREATE INDEX IF NOT EXISTS idx_calls_session ON llm_calls(session_id);
                CREATE INDEX IF NOT EXISTS idx_calls_time ON llm_calls(timestamp);
                CREATE INDEX IF NOT EXISTS idx_calls_date ON llm_calls(date(timestamp));
                
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    start_time TEXT,
                    end_time TEXT,
                    agent_id TEXT,
                    total_calls INTEGER DEFAULT 0,
                    total_tokens INTEGER DEFAULT 0
                );
            """)
    
    def insert_call(self, call: LLMCall):
        """插入 LLM 调用记录"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO llm_calls 
                (id, timestamp, session_id, provider, model, 
                 input_tokens, output_tokens, cache_read_tokens, cache_write_tokens, total_tokens, 
                 actual_cost, estimated_cost, estimated_cost_input, estimated_cost_output,
                 estimated_cost_cache_read, estimated_cost_cache_write, latency_ms, status, error_msg)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                call.id, call.timestamp.isoformat(), call.session_id,
                call.provider, call.model, call.input_tokens, call.output_tokens,
                call.cache_read_tokens, call.cache_write_tokens, call.total_tokens,
                call.actual_cost, call.estimated_cost,
                call.estimated_cost_breakdown.get('input', 0),
                call.estimated_cost_breakdown.get('output', 0),
                call.estimated_cost_breakdown.get('cache_read', 0),
                call.estimated_cost_breakdown.get('cache_write', 0),
                call.latency_ms, call.status, call.error_msg
            ))
    
    def get_stats(self, date: Optional[str] = None) -> Dict:
        """获取统计信息"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            # 基础统计
            if date:
                row = conn.execute("""
                    SELECT 
                        COUNT(*) as total_calls,
                        SUM(input_tokens) as input_tokens,
                        SUM(output_tokens) as output_tokens,
                        SUM(cache_read_tokens) as cache_read_tokens,
                        SUM(cache_write_tokens) as cache_write_tokens,
                        SUM(total_tokens) as total_tokens,
                        SUM(CASE WHEN actual_cost > 0 THEN actual_cost ELSE 0 END) as actual_cost_total,
                        SUM(estimated_cost) as estimated_cost_total,
                        SUM(estimated_cost_input) as estimated_cost_input,
                        SUM(estimated_cost_output) as estimated_cost_output,
                        SUM(estimated_cost_cache_read) as estimated_cost_cache_read,
                        SUM(estimated_cost_cache_write) as estimated_cost_cache_write,
                        SUM(CASE WHEN actual_cost > 0 THEN 1 ELSE 0 END) as calls_with_actual_cost
                    FROM llm_calls 
                    WHERE date(timestamp) = ?
                """, (date,)).fetchone()
            else:
                row = conn.execute("""
                    SELECT 
                        COUNT(*) as total_calls,
                        SUM(input_tokens) as input_tokens,
                        SUM(output_tokens) as output_tokens,
                        SUM(cache_read_tokens) as cache_read_tokens,
                        SUM(cache_write_tokens) as cache_write_tokens,
                        SUM(total_tokens) as total_tokens,
                        SUM(CASE WHEN actual_cost > 0 THEN actual_cost ELSE 0 END) as actual_cost_total,
                        SUM(estimated_cost) as estimated_cost_total,
                        SUM(estimated_cost_input) as estimated_cost_input,
                        SUM(estimated_cost_output) as estimated_cost_output,
                        SUM(estimated_cost_cache_read) as estimated_cost_cache_read,
                        SUM(estimated_cost_cache_write) as estimated_cost_cache_write,
                        SUM(CASE WHEN actual_cost > 0 THEN 1 ELSE 0 END) as calls_with_actual_cost
                    FROM llm_calls
                """).fetchone()
            
            # 按模型统计
            if date:
                models = conn.execute("""
                    SELECT model, COUNT(*) as calls, SUM(total_tokens) as tokens,
                           SUM(CASE WHEN actual_cost > 0 THEN actual_cost ELSE 0 END) as actual_cost,
                           SUM(estimated_cost) as estimated_cost
                    FROM llm_calls 
                    WHERE date(timestamp) = ?
                    GROUP BY model
                """, (date,)).fetchall()
            else:
                models = conn.execute("""
                    SELECT model, COUNT(*) as calls, SUM(total_tokens) as tokens,
                           SUM(CASE WHEN actual_cost > 0 THEN actual_cost ELSE 0 END) as actual_cost,
                           SUM(estimated_cost) as estimated_cost
                    FROM llm_calls 
                    GROUP BY model
                """).fetchall()
            
            # 按会话统计
            if date:
                sessions = conn.execute("""
                    SELECT session_id, COUNT(*) as calls, SUM(total_tokens) as tokens
                    FROM llm_calls 
                    WHERE date(timestamp) = ?
                    GROUP BY session_id
                    ORDER BY calls DESC
                    LIMIT 10
                """, (date,)).fetchall()
            else:
                sessions = conn.execute("""
                    SELECT session_id, COUNT(*) as calls, SUM(total_tokens) as tokens
                    FROM llm_calls 
                    GROUP BY session_id
                    ORDER BY calls DESC
                    LIMIT 10
                """).fetchall()
            
            return {
                'total_calls': row['total_calls'] or 0,
                'input_tokens': row['input_tokens'] or 0,
                'output_tokens': row['output_tokens'] or 0,
                'cache_read_tokens': row['cache_read_tokens'] or 0,
                'cache_write_tokens': row['cache_write_tokens'] or 0,
                'total_tokens': row['total_tokens'] or 0,
                'actual_cost': row['actual_cost_total'] or 0,
                'estimated_cost': row['estimated_cost_total'] or 0,
                'estimated_cost_input': row['estimated_cost_input'] or 0,
                'estimated_cost_output': row['estimated_cost_output'] or 0,
                'estimated_cost_cache_read': row['estimated_cost_cache_read'] or 0,
                'estimated_cost_cache_write': row['estimated_cost_cache_write'] or 0,
                'calls_with_actual_cost': row['calls_with_actual_cost'] or 0,
                'models': [dict(r) for r in models],
                'sessions': [dict(r) for r in sessions]
            }
    
    def get_model_details(self, date: Optional[str], model: str) -> Dict:
        """获取指定模型的详细 token 分布"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            
            if date:
                row = conn.execute("""
                    SELECT 
                        SUM(input_tokens) as input_tokens,
                        SUM(output_tokens) as output_tokens,
                        SUM(cache_read_tokens) as cache_read_tokens,
                        SUM(cache_write_tokens) as cache_write_tokens
                    FROM llm_calls 
                    WHERE date(timestamp) = ? AND model = ?
                """, (date, model)).fetchone()
            else:
                row = conn.execute("""
                    SELECT 
                        SUM(input_tokens) as input_tokens,
                        SUM(output_tokens) as output_tokens,
                        SUM(cache_read_tokens) as cache_read_tokens,
                        SUM(cache_write_tokens) as cache_write_tokens
                    FROM llm_calls 
                    WHERE model = ?
                """, (model,)).fetchone()
            
            return {
                'input': row['input_tokens'] or 0,
                'output': row['output_tokens'] or 0,
                'cache_read': row['cache_read_tokens'] or 0,
                'cache_write': row['cache_write_tokens'] or 0
            }

class LogParser:
    """解析 OpenClaw 会话日志"""
    
    @staticmethod
    def parse_session_file(file_path: Path) -> List[LLMCall]:
        """解析单个会话文件，提取 LLM 调用记录"""
        calls = []
        session_id = file_path.stem
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    try:
                        event = json.loads(line)
                        call = LogParser._parse_event(event, session_id)
                        if call:
                            calls.append(call)
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            print(f"Error parsing {file_path}: {e}")
        
        return calls
    
    @staticmethod
    def _parse_event(event: dict, session_id: str) -> Optional[LLMCall]:
        """解析单个事件"""
        event_type = event.get('type')
        
        # 模型调用完成事件
        if event_type == 'message' and event.get('message', {}).get('role') == 'assistant':
            msg = event['message']
            
            # 检查是否有 API 调用信息
            api_info = msg.get('api', '')
            if not api_info:
                return None
            
            timestamp = event.get('timestamp', datetime.now().isoformat())
            
            # 提取 token 信息 - OpenClaw 格式: usage.input, usage.output, usage.totalTokens
            usage = msg.get('usage', {})
            input_tokens = usage.get('input', 0)
            output_tokens = usage.get('output', 0)
            total_tokens = usage.get('totalTokens', input_tokens + output_tokens)
            
            # 提取 cache token 信息
            cache_read_tokens = usage.get('cacheRead', 0)
            cache_write_tokens = usage.get('cacheWrite', 0)
            
            # 提取实际费用（如果有）
            cost_info = usage.get('cost', {})
            actual_cost = cost_info.get('total', 0) if cost_info else 0
            
            # 提取模型信息
            model = msg.get('model', 'unknown')
            provider = msg.get('provider', 'unknown')
            
            # 计算估算费用（包含 cache）
            cost_breakdown = calculate_cost(model, input_tokens, output_tokens, 
                                           cache_read_tokens, cache_write_tokens)
            
            # 状态判断
            stop_reason = msg.get('stopReason', '')
            error = msg.get('errorMessage', '')
            status = 'error' if error else ('success' if stop_reason != 'error' else 'error')
            
            # 解析时间戳并转换为本地时间
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            dt_local = dt.astimezone()  # 转换为本地时区
            
            return LLMCall(
                id=event.get('id', f"{session_id}_{timestamp}"),
                timestamp=dt_local,
                session_id=session_id,
                provider=provider,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cache_read_tokens=cache_read_tokens,
                cache_write_tokens=cache_write_tokens,
                total_tokens=total_tokens,
                actual_cost=actual_cost if actual_cost > 0 else None,
                estimated_cost=cost_breakdown['total'],
                estimated_cost_breakdown=cost_breakdown,
                latency_ms=None,  # OpenClaw 日志中可能没有延迟信息
                status=status,
                error_msg=error if error else None
            )
        
        return None

class SessionHandler(FileSystemEventHandler):
    """文件系统事件处理器"""
    
    def __init__(self, db: Database):
        self.db = db
        self.processed_files = set()
    
    def on_modified(self, event):
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        if not file_path.suffix == '.jsonl':
            return
        
        # 避免重复处理
        if file_path in self.processed_files:
            return
        self.processed_files.add(file_path)
        
        # 解析并入库
        calls = LogParser.parse_session_file(file_path)
        for call in calls:
            self.db.insert_call(call)
        
        if calls:
            print(f"[Monitor] Processed {len(calls)} calls from {file_path.name}")

def run_monitor():
    """启动监控服务"""
    print("🚀 OpenClaw LLM Monitor 启动中...")
    print(f"📁 监控目录: {SESSIONS_DIR}")
    print(f"💾 数据库: {DEFAULT_DB_PATH}")
    print("Press Ctrl+C to stop\n")
    
    db = Database()
    handler = SessionHandler(db)
    observer = Observer()
    observer.schedule(handler, str(SESSIONS_DIR), recursive=False)
    observer.start()
    
    # 首次扫描已有文件
    print("🔍 扫描历史文件...")
    for jsonl_file in SESSIONS_DIR.glob("*.jsonl"):
        if '.deleted.' in jsonl_file.name:
            continue
        calls = LogParser.parse_session_file(jsonl_file)
        for call in calls:
            db.insert_call(call)
        if calls:
            print(f"  ✓ {jsonl_file.name}: {len(calls)} calls")
    
    print("\n👀 开始实时监控...")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\n👋 Monitor stopped")
    
    observer.join()

def show_stats(date: Optional[str] = None):
    """显示统计信息"""
    db = Database()
    
    if date is None:
        date = datetime.now().strftime('%Y-%m-%d')
    
    stats = db.get_stats(date)
    
    print(f"\n📊 LLM 调用统计 ({date})")
    print("=" * 60)
    print(f"总调用次数:    {stats['total_calls']}")
    print(f"总 Token:      {stats['total_tokens']:,}")
    print(f"  ├─ Input:    {stats['input_tokens']:,}")
    print(f"  └─ Output:   {stats['output_tokens']:,}")
    
    # 费用展示
    print(f"\n💰 费用统计:")
    if stats['actual_cost'] > 0:
        print(f"  实际费用:    ${stats['actual_cost']:.4f} USD (来自API)")
    
    # 展示估算费用明细（按模型分组显示不同币种）
    if stats['models']:
        print(f"\n  估算费用（按模型定价币种）:")
        
        # 按币种分组
        costs_by_currency = defaultdict(lambda: {'total': 0, 'input': 0, 'output': 0, 
                                                  'cache_read': 0, 'cache_write': 0,
                                                  'input_tokens': 0, 'output_tokens': 0,
                                                  'cache_read_tokens': 0, 'cache_write_tokens': 0})
        
        for m in stats['models']:
            model = m['model']
            pricing = get_model_pricing(model)
            currency = pricing['currency']
            symbol = pricing['symbol']
            
            # 获取该模型的详细费用
            model_details = db.get_model_details(date, model)
            cost_info = calculate_cost(model, model_details['input'], model_details['output'],
                                      model_details.get('cache_read', 0), model_details.get('cache_write', 0))
            
            costs_by_currency[currency]['total'] += cost_info['total']
            costs_by_currency[currency]['input'] += cost_info['input']
            costs_by_currency[currency]['output'] += cost_info['output']
            costs_by_currency[currency]['cache_read'] += cost_info['cache_read']
            costs_by_currency[currency]['cache_write'] += cost_info['cache_write']
            costs_by_currency[currency]['symbol'] = symbol
            costs_by_currency[currency]['input_tokens'] += model_details['input']
            costs_by_currency[currency]['output_tokens'] += model_details['output']
            costs_by_currency[currency]['cache_read_tokens'] += model_details.get('cache_read', 0)
            costs_by_currency[currency]['cache_write_tokens'] += model_details.get('cache_write', 0)
        
        # 按币种显示
        for currency, costs in costs_by_currency.items():
            symbol = costs['symbol']
            print(f"\n    [{currency}]")
            print(f"    实际计费: {symbol}{costs['total']:.4f}")
            print(f"      ├─ Input:       {symbol}{costs['input']:.4f} ({costs['input_tokens']:,} tokens)")
            print(f"      ├─ Output:      {symbol}{costs['output']:.4f} ({costs['output_tokens']:,} tokens)")
            if costs['cache_read_tokens'] > 0 or costs['cache_write_tokens'] > 0:
                print(f"      ├─ Cache Read:  {symbol}{costs['cache_read']:.4f} ({costs['cache_read_tokens']:,} tokens)")
                print(f"      └─ Cache Write: {symbol}{costs['cache_write']:.4f} ({costs['cache_write_tokens']:,} tokens)")
            
            # 计算如果没有 cache 会多花多少（节省费用）
            if costs['cache_read_tokens'] > 0:
                # 获取该币种的模型定价（假设主要使用一个模型）
                sample_model = None
                for m in stats['models']:
                    p = get_model_pricing(m['model'])
                    if p['currency'] == currency:
                        sample_model = m['model']
                        break
                
                if sample_model:
                    pricing = get_model_pricing(sample_model)
                    # 如果没有 cache，cache_read_tokens 会按正常 input 价格计费
                    normal_input_price = pricing['input']  # 正常 input 价格
                    cache_read_price = pricing['cache_read']  # cache read 价格
                    
                    # 计算节省的费用
                    cache_read_tokens = costs['cache_read_tokens']
                    would_be_cost = (cache_read_tokens / 1_000_000) * normal_input_price
                    actual_cache_cost = (cache_read_tokens / 1_000_000) * cache_read_price
                    saved_cost = would_be_cost - actual_cache_cost
                    
                    print(f"\n    💡 Cache 节省分析:")
                    print(f"      如果没有 Cache 需支付: {symbol}{would_be_cost:.4f}")
                    print(f"      Cache Read 实际支付:   {symbol}{actual_cache_cost:.4f}")
                    print(f"      节省费用:              {symbol}{saved_cost:.4f} ({saved_cost/would_be_cost*100:.1f}%)")
    else:
        # 如果没有模型分布，使用默认计算
        default_cost = calculate_cost('default', stats['input_tokens'], stats['output_tokens'],
                                     stats['cache_read_tokens'], stats['cache_write_tokens'])
        symbol = default_cost['symbol']
        print(f"\n  估算费用:    {symbol}{default_cost['total']:.4f} {default_cost['currency']}")
    
    if stats['models']:
        print(f"\n按模型分布:")
        for m in stats['models']:
            model = m['model']
            calls = m['calls']
            tokens = m['tokens']
            
            pricing = get_model_pricing(model)
            symbol = pricing['symbol']
            currency = pricing['currency']
            
            cost_info = ""
            if m.get('actual_cost', 0) > 0:
                cost_info = f", actual: ${m['actual_cost']:.4f}"
            if m.get('estimated_cost', 0) > 0:
                cost_info += f", est: {symbol}{m['estimated_cost']:.4f} {currency}"
            
            print(f"  {model}: {calls} calls ({tokens:,} tokens{cost_info})")
    
    if stats['sessions']:
        print(f"\n按会话分布 (Top 10):")
        for s in stats['sessions']:
            session_name = s['session_id'][:20] + "..." if len(s['session_id']) > 20 else s['session_id']
            print(f"  {session_name}: {s['calls']} calls ({s['tokens']:,} tokens)")
    
    print()

def main():
    parser = argparse.ArgumentParser(description='OpenClaw LLM Monitor')
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # monitor 命令
    monitor_parser = subparsers.add_parser('monitor', help='Start real-time monitoring')
    
    # stats 命令
    stats_parser = subparsers.add_parser('stats', help='Show statistics')
    stats_parser.add_argument('--date', help='Date to show stats for (YYYY-MM-DD)')
    stats_parser.add_argument('--today', action='store_true', help='Show today\'s stats')
    
    args = parser.parse_args()
    
    if args.command == 'monitor':
        run_monitor()
    elif args.command == 'stats':
        date = datetime.now().strftime('%Y-%m-%d') if args.today else args.date
        show_stats(date)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
