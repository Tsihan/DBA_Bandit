#!/bin/bash
# DBABandits JOB Benchmark - 快速命令参考

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║        DBABandits + JOB Benchmark 快速命令参考               ║"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# 检查配置
check_config() {
    echo "📋 检查配置..."
    echo ""
    echo "数据库配置 (config/db.conf):"
    grep -A 6 "\[POSTGRESQL\]" config/db.conf | grep -v "^#"
    echo ""
    echo "当前实验 (simulation/sim_run_experiment.py):"
    grep "exp_id_list" simulation/sim_run_experiment.py | head -1
    echo ""
    echo "实验设置 (config/exp.conf):"
    grep -A 2 "^\[job_benchmark_mab\]" config/exp.conf
    echo ""
}

# 运行实验
run_experiment() {
    echo "🚀 运行实验..."
    cd /home/qihan/DBABandits
    python3 simulation/sim_run_experiment.py
}

# 查看结果
view_results() {
    EXP_NAME=${1:-job_benchmark_mab}
    echo "📊 查看结果: $EXP_NAME"
    echo ""
    
    RESULT_DIR="experiments/$EXP_NAME/rep_1"
    
    if [ -d "$RESULT_DIR" ]; then
        echo "结果目录: $RESULT_DIR"
        echo ""
        echo "图表文件:"
        ls -lh $RESULT_DIR/plots/ 2>/dev/null || echo "  (暂无图表)"
        echo ""
        echo "日志文件:"
        ls -lh $RESULT_DIR/logs/*.log 2>/dev/null || echo "  (暂无日志)"
        echo ""
        echo "最新日志 (最后 20 行):"
        tail -20 $RESULT_DIR/logs/experiment.log 2>/dev/null || echo "  (日志文件不存在)"
    else
        echo "❌ 结果目录不存在: $RESULT_DIR"
        echo "请先运行实验。"
    fi
}

# 切换实验
switch_experiment() {
    EXP_NAME=$1
    if [ -z "$EXP_NAME" ]; then
        echo "用法: switch_experiment <exp_name>"
        echo "可用实验: job_benchmark_mab, job_full_mab, imdb_postgres_mab"
        return 1
    fi
    
    echo "🔄 切换到实验: $EXP_NAME"
    sed -i "s/exp_id_list = \[.*\]/exp_id_list = [\"$EXP_NAME\"]/" simulation/sim_run_experiment.py
    echo "✅ 已更新 simulation/sim_run_experiment.py"
    grep "exp_id_list" simulation/sim_run_experiment.py | head -1
}

# 重新生成工作负载
regenerate_workload() {
    echo "🔧 重新生成 JOB 工作负载..."
    python3 scripts/generate_job_workload.py
}

# 测试数据库连接
test_connection() {
    echo "🔌 测试 PostgreSQL 连接..."
    python3 << 'EOF'
import configparser
import psycopg2

config = configparser.ConfigParser()
config.read('config/db.conf')

try:
    conn = psycopg2.connect(
        host=config['POSTGRESQL']['host'],
        port=config['POSTGRESQL']['port'],
        database=config['POSTGRESQL']['database'],
        user=config['POSTGRESQL']['user'],
        password=config['POSTGRESQL']['password']
    )
    print("✅ 数据库连接成功！")
    cursor = conn.cursor()
    cursor.execute("SELECT version();")
    print(f"PostgreSQL 版本: {cursor.fetchone()[0]}")
    cursor.execute(f"SELECT COUNT(*) FROM {config['POSTGRESQL']['schema']}.title;")
    print(f"Title 表记录数: {cursor.fetchone()[0]:,}")
    conn.close()
except Exception as e:
    print(f"❌ 连接失败: {e}")
EOF
}

# 主菜单
main_menu() {
    while true; do
        echo ""
        echo "═══════════════════════════════════════════════════════════════"
        echo "选择操作:"
        echo "  1) 检查配置"
        echo "  2) 测试数据库连接"
        echo "  3) 运行实验 (job_benchmark_mab)"
        echo "  4) 运行完整实验 (job_full_mab)"
        echo "  5) 查看结果"
        echo "  6) 重新生成工作负载"
        echo "  7) 查看帮助文档"
        echo "  0) 退出"
        echo "═══════════════════════════════════════════════════════════════"
        echo -n "请选择 [0-7]: "
        read choice
        
        case $choice in
            1) check_config ;;
            2) test_connection ;;
            3) 
                switch_experiment "job_benchmark_mab"
                run_experiment 
                ;;
            4) 
                switch_experiment "job_full_mab"
                echo "⚠️  警告: 完整实验包含 113 个查询，可能需要数小时！"
                echo -n "确认运行？(y/N): "
                read confirm
                if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
                    run_experiment
                fi
                ;;
            5) 
                echo -n "实验名称 [job_benchmark_mab]: "
                read exp
                view_results ${exp:-job_benchmark_mab}
                ;;
            6) regenerate_workload ;;
            7) 
                echo ""
                echo "📚 帮助文档位置:"
                echo "  - QUICKSTART_JOB.md         (快速启动指南)"
                echo "  - CHANGES_JOB.md            (变更摘要)"
                echo "  - resources/workloads/JOB_README.md  (JOB 详细说明)"
                echo ""
                echo "查看文档: less QUICKSTART_JOB.md"
                ;;
            0) 
                echo "再见！"
                exit 0 
                ;;
            *) echo "❌ 无效选择，请重试" ;;
        esac
    done
}

# 如果直接运行，显示菜单
if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
    cd /home/qihan/DBABandits
    main_menu
fi
