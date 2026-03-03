import { describe, it, expect, beforeEach, afterEach } from "@jest/globals";
import * as sqlite3 from "sqlite3";
import * as path from "path";
import * as os from "os";
import * as fs from "fs/promises";

// 模拟 OpenClaw Plugin SDK
jest.mock("@openclaw/plugin-sdk", () => ({
  z: {
    object: () => ({
      boolean: () => ({ default: (v: boolean) => ({}) }),
      string: () => ({ default: (v: string) => ({}) }),
      number: () => ({ default: (v: number) => ({}) }),
      optional: () => ({}),
    }),
  },
}));

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
  "default": { input: 0.5, output: 2.0, cacheRead: 0.1, cacheWrite: 0.5, currency: "USD", symbol: "$" },
};

// 费用计算函数
function calculateCost(model: string, input: number, output: number, cacheRead: number): number {
  const pricing = MODEL_PRICING[model] || MODEL_PRICING["default"];
  const inputCost = (input / 1_000_000) * pricing.input;
  const outputCost = (output / 1_000_000) * pricing.output;
  const cacheCost = (cacheRead / 1_000_000) * pricing.cacheRead;
  return inputCost + outputCost + cacheCost;
}

// 数据库类（简化版用于测试）
class TestDatabase {
  private db: sqlite3.Database;
  private dbPath: string;

  constructor(dbPath: string) {
    this.dbPath = dbPath;
    this.db = new sqlite3.Database(dbPath);
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
        status TEXT
      )
    `);
  }

  insertCall(call: any): Promise<void> {
    return new Promise((resolve, reject) => {
      this.db.run(
        `INSERT INTO llm_calls 
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
}

describe("LLM Monitor Plugin", () => {
  describe("Cost Calculation", () => {
    it("should calculate Kimi k2.5 cost correctly", () => {
      const cost = calculateCost("k2.5", 1_000_000, 1_000_000, 0);
      expect(cost).toBe(25.0); // 4 + 21
    });

    it("should calculate cost with cache", () => {
      const cost = calculateCost("k2.5", 1_000_000, 1_000_000, 1_000_000);
      expect(cost).toBe(25.7); // 4 + 21 + 0.7
    });

    it("should use default pricing for unknown model", () => {
      const cost = calculateCost("unknown-model", 1_000_000, 1_000_000, 0);
      expect(cost).toBe(2.5); // 0.5 + 2.0
    });

    it("should calculate OpenAI gpt-4o cost correctly", () => {
      const cost = calculateCost("gpt-4o", 1_000_000, 1_000_000, 0);
      expect(cost).toBe(12.5); // 2.5 + 10
    });
  });

  describe("Database Operations", () => {
    let db: TestDatabase;
    let tempDir: string;
    let dbPath: string;

    beforeEach(async () => {
      tempDir = await fs.mkdtemp(path.join(os.tmpdir(), "llm-monitor-test-"));
      dbPath = path.join(tempDir, "test.db");
      db = new TestDatabase(dbPath);
    });

    afterEach(async () => {
      await db.close();
      await fs.rm(tempDir, { recursive: true });
    });

    it("should insert and retrieve call record", async () => {
      const call = {
        id: "test-1",
        timestamp: new Date().toISOString(),
        sessionId: "session-1",
        provider: "kimi-coding",
        model: "k2.5",
        inputTokens: 1000,
        outputTokens: 100,
        cacheReadTokens: 500,
        cacheWriteTokens: 0,
        totalTokens: 1600,
        actualCost: null,
        estimatedCost: 4.5,
        status: "success"
      };

      await db.insertCall(call);
      
      const stats = await db.getStats();
      expect(stats.total_calls).toBe(1);
      expect(stats.total_tokens).toBe(1600);
    });

    it("should calculate daily stats correctly", async () => {
      const today = new Date().toISOString().split("T")[0];
      
      // 插入今天的记录
      await db.insertCall({
        id: "today-1",
        timestamp: new Date().toISOString(),
        sessionId: "session-1",
        provider: "kimi-coding",
        model: "k2.5",
        inputTokens: 1000,
        outputTokens: 100,
        cacheReadTokens: 0,
        cacheWriteTokens: 0,
        totalTokens: 1100,
        actualCost: null,
        estimatedCost: 4.0,
        status: "success"
      });

      const stats = await db.getStats(today);
      expect(stats.total_calls).toBe(1);
      expect(stats.input_tokens).toBe(1000);
    });

    it("should handle multiple calls", async () => {
      for (let i = 0; i < 5; i++) {
        await db.insertCall({
          id: `call-${i}`,
          timestamp: new Date().toISOString(),
          sessionId: `session-${i}`,
          provider: "kimi-coding",
          model: "k2.5",
          inputTokens: 1000,
          outputTokens: 100,
          cacheReadTokens: 0,
          cacheWriteTokens: 0,
          totalTokens: 1100,
          actualCost: null,
          estimatedCost: 4.0,
          status: "success"
        });
      }

      const stats = await db.getStats();
      expect(stats.total_calls).toBe(5);
      expect(stats.total_tokens).toBe(5500);
    });
  });

  describe("Model Pricing", () => {
    it("should have all required fields for each model", () => {
      const requiredFields = ["input", "output", "cacheRead", "cacheWrite", "currency", "symbol"];
      
      for (const [modelName, pricing] of Object.entries(MODEL_PRICING)) {
        for (const field of requiredFields) {
          expect(pricing).toHaveProperty(field);
        }
      }
    });

    it("should have positive prices", () => {
      for (const [modelName, pricing] of Object.entries(MODEL_PRICING)) {
        expect(pricing.input).toBeGreaterThan(0);
        expect(pricing.output).toBeGreaterThan(0);
        expect(pricing.cacheRead).toBeGreaterThan(0);
      }
    });
  });
});
