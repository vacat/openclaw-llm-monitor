import type { OpenClawPluginApi, OpenClawPluginConfig } from "openclaw";
import { z } from "zod";
import * as sqlite3 from "sqlite3";
import { promises as fs } from "fs";
import * as path from "path";
import * as os from "os";

// 模型价格配置
const MODEL_PRICING: Record<string, {
  input: number;
  output: number;
  cacheRead: number;
  cacheWrite: number;
  currency: string;
  symbol: string;
}> = {
  "k2.5": { input: 4.0, output: 21.0, cacheRead: 0.7, cacheWrite: 4.0, currency: "CNY", symbol: "¥" },
  "gpt-4o": { input: 2.5, output: 10.0, cacheRead: 1.25, cacheWrite: 2.5, currency: "USD", symbol: "$" },
  "claude-3-sonnet": { input: 3.0, output: 15.0, cacheRead: 0.3, cacheWrite: 3.0, currency: "USD", symbol: "$" },
  "default": { input: 0.5, output: 2.0, cacheRead: 0.1, cacheWrite: 0.5, currency: "USD", symbol: "$" },
};

// LLM 调用记录接口
interface LLMCall {
  id: string;
  timestamp: string;
  sessionId: string;
  provider: string;
  model: string;
  inputTokens: number;
  outputTokens: number;
  cacheReadTokens: number;
  cacheWriteTokens: number;
  totalTokens: number;
  actualCost?: number;
  estimatedCost: number;
  status: string;
}

// 数据库管理类
class MonitorDatabase {
  private db: sqlite3.Database;
  private dbPath: string;

  constructor(dbPath: string) {
    // 展开 ~ 为 home 目录
    this.dbPath = dbPath.replace(/^~/, os.homedir());
    this.db = new sqlite3.Database(this.dbPath);
    this.init();
  }

  private init() {
    this.db.exec(`
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
        status TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
      );
      
      CREATE INDEX IF NOT EXISTS idx_calls_session ON llm_calls(session_id);
      CREATE INDEX IF NOT EXISTS idx_calls_time ON llm_calls(timestamp);
      CREATE INDEX IF NOT EXISTS idx_calls_date ON llm_calls(date(timestamp));
    `);
  }

  insertCall(call: LLMCall): Promise<void> {
    return new Promise((resolve, reject) => {
      this.db.run(
        `INSERT OR REPLACE INTO llm_calls 
         (id, timestamp, session_id, provider, model, input_tokens, output_tokens, 
          cache_read_tokens, cache_write_tokens, total_tokens, actual_cost, estimated_cost, status)
         VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
        [
          call.id, call.timestamp, call.sessionId, call.provider, call.model,
          call.inputTokens, call.outputTokens, call.cacheReadTokens, call.cacheWriteTokens,
          call.totalTokens, call.actualCost, call.estimatedCost, call.status
        ],
        (err) => {
          if (err) reject(err);
          else resolve();
        }
      );
    });
  }

  getStats(date?: string): Promise<any> {
    return new Promise((resolve, reject) => {
      const dateFilter = date ? `WHERE date(timestamp) = '${date}'` : "";
      
      this.db.get(
        `SELECT 
          COUNT(*) as total_calls,
          SUM(input_tokens) as input_tokens,
          SUM(output_tokens) as output_tokens,
          SUM(cache_read_tokens) as cache_read_tokens,
          SUM(total_tokens) as total_tokens,
          SUM(estimated_cost) as estimated_cost
        FROM llm_calls ${dateFilter}`,
        (err, row) => {
          if (err) reject(err);
          else resolve(row);
        }
      );
    });
  }

  close(): Promise<void> {
    return new Promise((resolve) => {
      this.db.close(() => resolve());
    });
  }

  getHourlyStats(date: string): Promise<any[]> {
    return new Promise((resolve, reject) => {
      this.db.all(
        `SELECT 
          strftime('%H', timestamp) as hour,
          COUNT(*) as calls
        FROM llm_calls 
        WHERE date(timestamp) = ?
        GROUP BY hour
        ORDER BY hour`,
        [date],
        (err, rows) => {
          if (err) reject(err);
          else resolve(rows || []);
        }
      );
    });
  }

  getModelStats(date: string): Promise<any[]> {
    return new Promise((resolve, reject) => {
      this.db.all(
        `SELECT 
          model,
          COUNT(*) as calls
        FROM llm_calls 
        WHERE date(timestamp) = ?
        GROUP BY model
        ORDER BY calls DESC`,
        [date],
        (err, rows) => {
          if (err) reject(err);
          else resolve(rows || []);
        }
      );
    });
  }

  getRecentCalls(limit: number = 10): Promise<any[]> {
    return new Promise((resolve, reject) => {
      this.db.all(
        `SELECT 
          datetime(timestamp) as time,
          model,
          total_tokens as tokens,
          estimated_cost as cost,
          status
        FROM llm_calls 
        ORDER BY timestamp DESC
        LIMIT ?`,
        [limit],
        (err, rows) => {
          if (err) reject(err);
          else resolve(rows || []);
        }
      );
    });
  }
}

// 计算 Cache 节省
function calculateCacheSavings(stats: any): number {
  if (!stats || !stats.cache_read_tokens) return 0;
  
  // 假设正常 input 价格是 cache read 的 5 倍（典型值）
  const normalPrice = 4.0;  // ¥/1M tokens
  const cachePrice = 0.7;   // ¥/1M tokens
  
  const cacheTokens = stats.cache_read_tokens;
  const wouldBeCost = (cacheTokens / 1_000_000) * normalPrice;
  const actualCost = (cacheTokens / 1_000_000) * cachePrice;
  
  return wouldBeCost - actualCost;
}

// 费用计算
function calculateCost(model: string, input: number, output: number, cacheRead: number): number {
  const pricing = MODEL_PRICING[model] || MODEL_PRICING["default"];
  const inputCost = (input / 1_000_000) * pricing.input;
  const outputCost = (output / 1_000_000) * pricing.output;
  const cacheCost = (cacheRead / 1_000_000) * pricing.cacheRead;
  return inputCost + outputCost + cacheCost;
}

// 主插件
const llmMonitorPlugin = {
  id: "llm-monitor",
  name: "LLM Monitor",
  description: "Monitor LLM calls, token usage, and cost estimation",
  kind: "tool" as const,
  configSchema: z.object({
    enabled: z.boolean().default(true),
    dbPath: z.string().default("~/.openclaw/monitor/llm_stats.db"),
    alertThreshold: z.object({
      dailyTokens: z.number().default(10_000_000),
      dailyCost: z.number().default(50),
    }).optional(),
  }),

  register(api: OpenClawPluginApi) {
    let db: MonitorDatabase | null = null;

    // 初始化数据库
    api.onInit(async (config) => {
      if (!config.enabled) return;
      
      const dbDir = path.dirname(config.dbPath.replace(/^~/, os.homedir()));
      await fs.mkdir(dbDir, { recursive: true });
      db = new MonitorDatabase(config.dbPath);
      
      api.logger.info("[LLM Monitor] Database initialized");
    });

    // Hook LLM 调用
    api.onLlmCall(async (call, config) => {
      if (!config.enabled || !db) return;

      try {
        // 提取调用信息
        const model = call.model || "unknown";
        const usage = call.usage || {};
        
        const inputTokens = usage.input || 0;
        const outputTokens = usage.output || 0;
        const cacheReadTokens = usage.cacheRead || 0;
        const cacheWriteTokens = usage.cacheWrite || 0;
        const totalTokens = usage.totalTokens || (inputTokens + outputTokens);
        
        // 计算费用
        const estimatedCost = calculateCost(model, inputTokens, outputTokens, cacheReadTokens);
        
        // 构造记录
        const record: LLMCall = {
          id: call.id || `${Date.now()}_${Math.random()}`,
          timestamp: new Date().toISOString(),
          sessionId: call.sessionId || "unknown",
          provider: call.provider || "unknown",
          model: model,
          inputTokens,
          outputTokens,
          cacheReadTokens,
          cacheWriteTokens,
          totalTokens,
          actualCost: usage.cost?.total,
          estimatedCost,
          status: call.error ? "error" : "success",
        };

        // 保存到数据库
        await db.insertCall(record);
        
        api.logger.debug(`[LLM Monitor] Recorded call: ${model}, ${totalTokens} tokens`);
      } catch (err) {
        api.logger.error("[LLM Monitor] Failed to record call:", err);
      }
    });

    // 注册 Dashboard 路由
    api.registerHttpRoute(
      "/llm-monitor",
      async (req, res) => {
        // 返回 Dashboard HTML
        const dashboardPath = path.join(__dirname, "dashboard", "index.html");
        try {
          const html = await fs.readFile(dashboardPath, "utf-8");
          res.setHeader("Content-Type", "text/html");
          res.end(html);
        } catch (err) {
          res.statusCode = 500;
          res.end("Dashboard not found");
        }
      },
      { method: "GET" }
    );

    // 注册 API 路由
    api.registerHttpRoute(
      "/api/llm-monitor/stats",
      async (req, res) => {
        if (!db) {
          res.statusCode = 500;
          res.end(JSON.stringify({ error: "Database not initialized" }));
          return;
        }

        const url = new URL(req.url || "", `http://${req.headers.host}`);
        const date = url.searchParams.get("date") || new Date().toISOString().split("T")[0];

        try {
          const stats = await db.getStats(date);
          const hourly = await db.getHourlyStats(date);
          const models = await db.getModelStats(date);
          const recentCalls = await db.getRecentCalls(10);

          // 计算 Cache 节省
          const cacheSavings = calculateCacheSavings(stats);

          res.setHeader("Content-Type", "application/json");
          res.end(JSON.stringify({
            date,
            calls: stats?.total_calls || 0,
            tokens: {
              input: stats?.input_tokens || 0,
              output: stats?.output_tokens || 0,
              cacheRead: stats?.cache_read_tokens || 0,
              total: stats?.total_tokens || 0,
            },
            estimatedCost: stats?.estimated_cost || 0,
            cacheSavings,
            hourly,
            models,
            recentCalls,
          }));
        } catch (err) {
          res.statusCode = 500;
          res.end(JSON.stringify({ error: String(err) }));
        }
      },
      { method: "GET" }
    );

    // 注册监控工具
    api.registerTool(
      (ctx) => {
        return [
          // 获取今日统计
          api.runtime.tools.createTool({
            name: "llm_monitor_today",
            description: "Get today's LLM usage statistics",
            parameters: z.object({}),
            handler: async () => {
              if (!db) return { error: "Database not initialized" };
              
              const today = new Date().toISOString().split("T")[0];
              const stats = await db.getStats(today);
              
              return {
                date: today,
                calls: stats?.total_calls || 0,
                tokens: {
                  input: stats?.input_tokens || 0,
                  output: stats?.output_tokens || 0,
                  cacheRead: stats?.cache_read_tokens || 0,
                  total: stats?.total_tokens || 0,
                },
                estimatedCost: stats?.estimated_cost || 0,
              };
            },
          }),
          
          // 获取指定日期统计
          api.runtime.tools.createTool({
            name: "llm_monitor_date",
            description: "Get LLM usage statistics for a specific date",
            parameters: z.object({
              date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/).describe("Date in YYYY-MM-DD format"),
            }),
            handler: async ({ date }) => {
              if (!db) return { error: "Database not initialized" };
              
              const stats = await db.getStats(date);
              
              return {
                date,
                calls: stats?.total_calls || 0,
                tokens: {
                  input: stats?.input_tokens || 0,
                  output: stats?.output_tokens || 0,
                  cacheRead: stats?.cache_read_tokens || 0,
                  total: stats?.total_tokens || 0,
                },
                estimatedCost: stats?.estimated_cost || 0,
              };
            },
          }),
        ];
      },
      { names: ["llm_monitor_today", "llm_monitor_date"] }
    );

    // 注册 CLI 命令
    api.registerCli(
      ({ program }) => {
        program
          .command("llm-monitor")
          .description("Show LLM usage statistics")
          .option("-d, --date <date>", "Specific date (YYYY-MM-DD)")
          .action(async (options) => {
            if (!db) {
              console.log("Database not initialized");
              return;
            }
            
            const date = options.date || new Date().toISOString().split("T")[0];
            const stats = await db.getStats(date);
            
            console.log(`\n📊 LLM 调用统计 (${date})`);
            console.log("=".repeat(50));
            console.log(`总调用次数: ${stats?.total_calls || 0}`);
            console.log(`总 Token: ${stats?.total_tokens || 0}`);
            console.log(`  ├─ Input: ${stats?.input_tokens || 0}`);
            console.log(`  └─ Output: ${stats?.output_tokens || 0}`);
            console.log(`估算费用: ¥${(stats?.estimated_cost || 0).toFixed(4)}`);
            console.log();
          });
      },
      { commands: ["llm-monitor"] }
    );

    // 清理
    api.onDispose(async () => {
      if (db) {
        await db.close();
        api.logger.info("[LLM Monitor] Database closed");
      }
    });
  },
};

export default llmMonitorPlugin;
