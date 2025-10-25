#!/bin/bash
# DDQN Index Selection Quick Start Script
# PostgreSQL深度强化学习索引选择快速启动脚本

set -e  # Exit on error

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}DDQN Index Selection for PostgreSQL${NC}"
echo -e "${BLUE}========================================${NC}\n"

# 检查虚拟环境
if [ ! -d "/home/qihan/.venv" ]; then
    echo -e "${RED}❌ Virtual environment not found!${NC}"
    exit 1
fi

# 激活虚拟环境
echo -e "${GREEN}✓${NC} Activating virtual environment..."
source /home/qihan/.venv/bin/activate

# 进入项目目录
cd /home/qihan/DBABandits

# 检查GPU
echo -e "\n${YELLOW}📊 Checking GPU availability...${NC}"
if command -v nvidia-smi &> /dev/null; then
    nvidia-smi --query-gpu=name,memory.total,memory.free --format=csv,noheader
    echo -e "${GREEN}✓${NC} GPU detected! DDQN will use GPU acceleration."
else
    echo -e "${YELLOW}⚠${NC}  No GPU detected. DDQN will run on CPU (slower)."
fi

# 检查TensorFlow GPU支持
echo -e "\n${YELLOW}🔍 Checking TensorFlow GPU support...${NC}"
python -c "import tensorflow as tf; gpus = tf.config.list_physical_devices('GPU'); print('GPU available:', len(gpus) > 0); [print(f'  - {gpu.name}') for gpu in gpus]" 2>/dev/null || echo "TensorFlow check skipped"

# 显示实验配置
echo -e "\n${YELLOW}⚙️  Experiment Configuration:${NC}"
echo "  - Experiment ID: job_benchmark_ddqn"
echo "  - Algorithm: DDQN (Deep Q-Network)"
echo "  - Database: PostgreSQL (IMDB)"
echo "  - Workload: JOB Benchmark"
echo ""

# 询问用户
read -p "$(echo -e ${YELLOW}Do you want to start the experiment? [y/N]: ${NC})" -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo -e "${RED}Experiment cancelled.${NC}"
    exit 0
fi

# 运行实验
echo -e "\n${GREEN}🚀 Starting DDQN experiment...${NC}\n"
echo -e "${BLUE}========================================${NC}"

# 设置日志文件
LOG_DIR="experiments/job_benchmark_ddqn"
mkdir -p "$LOG_DIR"

# 运行实验并实时显示输出
python -m simulation.sim_run_ddqn_experiment 2>&1 | tee "${LOG_DIR}/run_$(date +%Y%m%d_%H%M%S).log"

EXITCODE=${PIPESTATUS[0]}

echo -e "\n${BLUE}========================================${NC}"

if [ $EXITCODE -eq 0 ]; then
    echo -e "${GREEN}✅ Experiment completed successfully!${NC}\n"
    echo -e "${YELLOW}📁 Results location:${NC}"
    echo "   - Logs: ${LOG_DIR}/"
    echo "   - Plots: ${LOG_DIR}/*.png"
    echo "   - Data: ${LOG_DIR}/reports.pickle"
    echo ""
    echo -e "${YELLOW}📊 View results:${NC}"
    echo "   tail -100 ${LOG_DIR}/job_benchmark_ddqn.log"
else
    echo -e "${RED}❌ Experiment failed with exit code $EXITCODE${NC}"
    echo -e "${YELLOW}Check logs at: ${LOG_DIR}/${NC}"
    exit $EXITCODE
fi
