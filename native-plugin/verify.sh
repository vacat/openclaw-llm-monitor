#!/bin/bash
# 简单验证脚本

echo "🔍 LLM Monitor Plugin 验证"
echo "=========================="

cd /root/.openclaw/extensions/llm-monitor

# 检查文件结构
echo ""
echo "📁 文件结构:"
ls -la

# 检查关键文件
echo ""
echo "📄 关键文件检查:"
for file in index.ts openclaw.plugin.json package.json tsconfig.json dashboard/index.html tests/index.test.ts; do
    if [ -f "$file" ]; then
        echo "  ✅ $file"
    else
        echo "  ❌ $file 缺失"
    fi
done

# 检查 TypeScript 语法（简单检查）
echo ""
echo "🔤 TypeScript 语法检查:"
if grep -q "import.*from" index.ts; then
    echo "  ✅ 包含 import 语句"
fi
if grep -q "export default" index.ts; then
    echo "  ✅ 包含 export default"
fi

# 检查 Dashboard
echo ""
echo "🌐 Dashboard 检查:"
if grep -q "llm_monitor_today" index.ts; then
    echo "  ✅ 注册了 llm_monitor_today 工具"
fi
if grep -q "registerHttpRoute" index.ts; then
    echo "  ✅ 注册了 HTTP 路由"
fi

echo ""
echo "✅ 验证完成"
