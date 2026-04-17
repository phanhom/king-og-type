#!/bin/bash

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 端口配置
BACKEND_PORT=21001
FRONTEND_PORT=21000

# 获取脚本所在目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   King of Type 启动脚本${NC}"
echo -e "${GREEN}========================================${NC}"

# 杀掉占用指定端口的进程
kill_port() {
    local port=$1
    local pid=$(lsof -ti :$port 2>/dev/null)
    if [ -n "$pid" ]; then
        echo -e "${YELLOW}端口 $port 被占用，正在杀掉进程 PID: $pid${NC}"
        kill -9 $pid 2>/dev/null
        sleep 1
        echo -e "${GREEN}进程已终止${NC}"
    else
        echo -e "${GREEN}端口 $port 未被占用${NC}"
    fi
}

# 检查并安装依赖
check_dependencies() {
    # 检查后端依赖
    if [ ! -d "$SCRIPT_DIR/backend/venv" ]; then
        echo -e "${YELLOW}创建 Python 虚拟环境...${NC}"
        python3 -m venv "$SCRIPT_DIR/backend/venv"
    fi
    
    echo -e "${YELLOW}安装后端依赖...${NC}"
    source "$SCRIPT_DIR/backend/venv/bin/activate"
    pip install -q -r "$SCRIPT_DIR/backend/requirements.txt"
    
    # 检查前端依赖
    if [ ! -d "$SCRIPT_DIR/frontend/node_modules" ]; then
        echo -e "${YELLOW}安装前端依赖...${NC}"
        cd "$SCRIPT_DIR/frontend" && npm install
    fi
}

# 启动后端
start_backend() {
    echo -e "${GREEN}启动后端服务 (端口: $BACKEND_PORT)...${NC}"
    cd "$SCRIPT_DIR/backend"
    source "$SCRIPT_DIR/backend/venv/bin/activate"
    python main.py &
    BACKEND_PID=$!
    echo -e "${GREEN}后端 PID: $BACKEND_PID${NC}"
}

# 启动前端
start_frontend() {
    echo -e "${GREEN}启动前端服务 (端口: $FRONTEND_PORT)...${NC}"
    cd "$SCRIPT_DIR/frontend"
    npm run dev &
    FRONTEND_PID=$!
    echo -e "${GREEN}前端 PID: $FRONTEND_PID${NC}"
}

# 清理函数
cleanup() {
    echo -e "\n${YELLOW}正在关闭服务...${NC}"
    kill_port $BACKEND_PORT
    kill_port $FRONTEND_PORT
    echo -e "${GREEN}服务已关闭${NC}"
    exit 0
}

# 捕获退出信号
trap cleanup SIGINT SIGTERM

# 主流程
echo -e "\n${YELLOW}[1/4] 清理端口...${NC}"
kill_port $BACKEND_PORT
kill_port $FRONTEND_PORT

echo -e "\n${YELLOW}[2/4] 检查依赖...${NC}"
check_dependencies

echo -e "\n${YELLOW}[3/4] 启动后端...${NC}"
start_backend

echo -e "\n${YELLOW}[4/4] 启动前端...${NC}"
start_frontend

echo -e "\n${GREEN}========================================${NC}"
echo -e "${GREEN}   服务已启动！${NC}"
echo -e "${GREEN}   后端: http://localhost:$BACKEND_PORT${NC}"
echo -e "${GREEN}   前端: http://localhost:$FRONTEND_PORT${NC}"
echo -e "${GREEN}   按 Ctrl+C 停止所有服务${NC}"
echo -e "${GREEN}========================================${NC}"

# 等待子进程
wait
