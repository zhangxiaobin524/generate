#!/bin/bash
set -e

SERVER_IP="120.55.250.184"
SERVER_USER="root"
SERVER_PASS="123524zxB"
PROJECT_DIR="/Users/zhangxiaobin/self-project/generate"
REMOTE_DIR="/root/generate"

export SSHPASS="$SERVER_PASS"
SSH_OPTS="-o StrictHostKeyChecking=no"

echo "================================"
echo "  学信网复刻 - 部署到服务器"
echo "================================"
echo ""

# 1. 同步文件到服务器
echo "[1/4] 正在同步文件到服务器..."
sshpass -e rsync -avz --delete \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    -e "ssh $SSH_OPTS" \
    "$PROJECT_DIR/" \
    "$SERVER_USER@$SERVER_IP:$REMOTE_DIR/"
echo "文件同步完成"

# 2. 确保 docker 可用
echo ""
echo "[2/4] 检查 Docker 环境..."
sshpass -e ssh $SSH_OPTS "$SERVER_USER@$SERVER_IP" 'docker --version && docker compose version' || {
    echo "Docker 未安装，正在安装..."
    sshpass -e ssh $SSH_OPTS "$SERVER_USER@$SERVER_IP" 'curl -fsSL https://get.docker.com | sh && systemctl enable docker && systemctl start docker'
}

# 3. 重新构建启动
echo ""
echo "[3/4] 重新构建并启动服务..."
sshpass -e ssh $SSH_OPTS "$SERVER_USER@$SERVER_IP" "cd $REMOTE_DIR && docker compose down && docker compose up -d --build"

# 4. 检查状态
echo ""
echo "[4/4] 等待服务启动..."
sleep 5
sshpass -e ssh $SSH_OPTS "$SERVER_USER@$SERVER_IP" "cd $REMOTE_DIR && docker compose ps"

echo ""
echo "================================"
echo "  部署完成！"
echo "  登录页: http://$SERVER_IP:9003/login.html"
echo "  账号管理: http://$SERVER_IP:9003/account-generator.html"
echo "================================"
