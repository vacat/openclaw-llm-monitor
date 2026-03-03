#!/bin/bash
#
# OpenClaw LLM Monitor 一键安装脚本
# 支持: Ubuntu/Debian/CentOS/macOS
#

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 配置
INSTALL_DIR="${HOME}/.openclaw/monitor"
REPO_URL="https://github.com/vacat/openclaw-llm-monitor.git"
PYTHON_CMD=""

echo -e "${BLUE}"
echo "╔════════════════════════════════════════════════════════════╗"
echo "║     OpenClaw LLM Monitor - 一键安装脚本                   ║"
echo "║     实时监控大模型调用、Token 使用、费用统计               ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# 检查操作系统
detect_os() {
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        if [ -f /etc/debian_version ]; then
            OS="debian"
        elif [ -f /etc/redhat-release ]; then
            OS="redhat"
        else
            OS="linux"
        fi
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
    else
        OS="unknown"
    fi
    echo -e "${BLUE}检测到操作系统: $OS${NC}"
}

# 检查 Python
check_python() {
    echo -e "${YELLOW}检查 Python 环境...${NC}"
    
    if command -v python3 &> /dev/null; then
        PYTHON_CMD="python3"
    elif command -v python &> /dev/null; then
        PYTHON_CMD="python"
    else
        echo -e "${RED}错误: 未找到 Python，请先安装 Python 3.8+${NC}"
        exit 1
    fi
    
    PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
    echo -e "${GREEN}✓ 找到 Python: $PYTHON_VERSION${NC}"
}

# 安装依赖
install_dependencies() {
    echo -e "${YELLOW}安装依赖...${NC}"
    
    # 安装 Python 依赖
    $PYTHON_CMD -m pip install --user watchdog 2>/dev/null || {
        echo -e "${YELLOW}尝试使用 --break-system-packages 安装...${NC}"
        $PYTHON_CMD -m pip install --break-system-packages watchdog 2>/dev/null || {
            echo -e "${RED}安装 watchdog 失败，请手动安装: pip install watchdog${NC}"
            exit 1
        }
    }
    
    echo -e "${GREEN}✓ 依赖安装完成${NC}"
}

# 克隆仓库
clone_repo() {
    echo -e "${YELLOW}下载 OpenClaw LLM Monitor...${NC}"
    
    if [ -d "$INSTALL_DIR" ]; then
        echo -e "${YELLOW}目录已存在，更新代码...${NC}"
        cd "$INSTALL_DIR"
        git pull origin master 2>/dev/null || git pull origin main 2>/dev/null || {
            echo -e "${YELLOW}更新失败，尝试重新克隆...${NC}"
            rm -rf "$INSTALL_DIR"
            git clone "$REPO_URL" "$INSTALL_DIR"
        }
    else
        mkdir -p "$INSTALL_DIR"
        git clone "$REPO_URL" "$INSTALL_DIR" || {
            echo -e "${RED}克隆失败，尝试直接下载...${NC}"
            mkdir -p "$INSTALL_DIR"
            cd "$INSTALL_DIR"
            curl -L "${REPO_URL%.git}/archive/refs/heads/master.tar.gz" -o monitor.tar.gz 2>/dev/null || \
            curl -L "${REPO_URL%.git}/archive/refs/heads/main.tar.gz" -o monitor.tar.gz 2>/dev/null
            tar -xzf monitor.tar.gz --strip-components=1
            rm monitor.tar.gz
        }
    fi
    
    echo -e "${GREEN}✓ 代码下载完成${NC}"
}

# 创建启动脚本
create_launcher() {
    echo -e "${YELLOW}创建启动脚本...${NC}"
    
    LAUNCHER="${HOME}/.local/bin/openclaw-monitor"
    mkdir -p "${HOME}/.local/bin"
    
    cat > "$LAUNCHER" << 'EOF'
#!/bin/bash
# OpenClaw LLM Monitor 启动脚本

INSTALL_DIR="${HOME}/.openclaw/monitor"

cd "$INSTALL_DIR"

if [ "$1" == "monitor" ]; then
    python3 openclaw_monitor.py monitor
elif [ "$1" == "stats" ]; then
    if [ "$2" == "--today" ] || [ "$2" == "-t" ]; then
        python3 openclaw_monitor.py stats --today
    elif [ -n "$2" ]; then
        python3 openclaw_monitor.py stats --date "$2"
    else
        python3 openclaw_monitor.py stats --today
    fi
elif [ "$1" == "help" ] || [ "$1" == "--help" ] || [ "$1" == "-h" ]; then
    echo "OpenClaw LLM Monitor"
    echo ""
    echo "用法:"
    echo "  openclaw-monitor monitor          # 启动实时监控"
    echo "  openclaw-monitor stats            # 查看今日统计"
    echo "  openclaw-monitor stats --today    # 查看今日统计"
    echo "  openclaw-monitor stats 2026-03-03 # 查看指定日期"
    echo "  openclaw-monitor help             # 显示帮助"
else
    python3 openclaw_monitor.py stats --today
fi
EOF
    
    chmod +x "$LAUNCHER"
    
    # 添加到 PATH
    if [[ ":$PATH:" != *":${HOME}/.local/bin:"* ]]; then
        echo 'export PATH="${HOME}/.local/bin:${PATH}"' >> "${HOME}/.bashrc"
        echo -e "${YELLOW}已添加 PATH 到 .bashrc，请运行: source ~/.bashrc${NC}"
    fi
    
    echo -e "${GREEN}✓ 启动脚本创建完成: $LAUNCHER${NC}"
}

# 初始化数据库
init_database() {
    echo -e "${YELLOW}初始化数据库...${NC}"
    
    cd "$INSTALL_DIR"
    $PYTHON_CMD -c "
import sqlite3
from pathlib import Path

db_path = Path.home() / '.openclaw' / 'monitor' / 'llm_stats.db'
db_path.parent.mkdir(parents=True, exist_ok=True)

conn = sqlite3.connect(db_path)
conn.executescript('''
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
''')
conn.close()
print('Database initialized at:', db_path)
"
    
    echo -e "${GREEN}✓ 数据库初始化完成${NC}"
}

# 扫描历史数据
scan_history() {
    echo -e "${YELLOW}扫描历史会话数据...${NC}"
    
    SESSIONS_DIR="${HOME}/.openclaw/agents/main/sessions"
    
    if [ -d "$SESSIONS_DIR" ]; then
        cd "$INSTALL_DIR"
        $PYTHON_CMD openclaw_monitor.py monitor &
        MONITOR_PID=$!
        sleep 2
        kill $MONITOR_PID 2>/dev/null || true
        echo -e "${GREEN}✓ 历史数据扫描完成${NC}"
    else
        echo -e "${YELLOW}未找到历史会话数据，跳过扫描${NC}"
    fi
}

# 显示使用说明
show_usage() {
    echo ""
    echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║              安装完成！                                   ║${NC}"
    echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BLUE}使用方法:${NC}"
    echo ""
    echo "  1. 启动实时监控:"
    echo -e "     ${YELLOW}openclaw-monitor monitor${NC}"
    echo ""
    echo "  2. 查看今日统计:"
    echo -e "     ${YELLOW}openclaw-monitor stats${NC}"
    echo ""
    echo "  3. 查看指定日期:"
    echo -e "     ${YELLOW}openclaw-monitor stats 2026-03-03${NC}"
    echo ""
    echo -e "${BLUE}文件位置:${NC}"
    echo "  - 安装目录: $INSTALL_DIR"
    echo "  - 数据库:   ${HOME}/.openclaw/monitor/llm_stats.db"
    echo "  - 启动脚本: ${HOME}/.local/bin/openclaw-monitor"
    echo ""
    echo -e "${BLUE}GitHub 仓库:${NC}"
    echo "  $REPO_URL"
    echo ""
}

# 主函数
main() {
    detect_os
    check_python
    install_dependencies
    clone_repo
    create_launcher
    init_database
    scan_history
    show_usage
}

main "$@"
