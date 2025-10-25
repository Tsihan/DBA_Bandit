# DDQN-based Index Selection for PostgreSQL

## 概述

这个脚本使用深度强化学习（Deep Q-Network, DDQN）在 PostgreSQL 数据库上进行自动索引选择。

## 文件说明

- **`simulation/sim_run_ddqn_experiment.py`**: DDQN实验运行脚本
- **`config/exp.conf`**: 实验配置文件（新增 `[job_benchmark_ddqn]` 配置）
- **`simulation/sim_ddqn_v3.py`**: DDQN算法实现
- **`bandits/rl_ddqn_v2.py`**: 深度Q网络核心代码

## 配置说明

在 `config/exp.conf` 中的 `[job_benchmark_ddqn]` 配置项：

```ini
[job_benchmark_ddqn]
reps = 1                    # 实验重复次数
rounds = 20                 # 实验轮数
hyp_rounds = 5              # 热身轮数（用于网络预训练）
workload_shifts = [...]     # 工作负载变化点
queries_start = [...]       # 每轮查询开始位置
queries_end = [...]         # 每轮查询结束位置
max_memory = 25000          # 最大索引内存限制 (MB)
components = ["DDQN", "NO_INDEX"]  # 要运行的组件
```

### 关键参数

- **`hyp_rounds`**: 热身轮数，DDQN在这些轮次中探索和学习，但不计入最终结果
- **`components`**: 
  - `"DDQN"` - 深度强化学习方法
  - `"NO_INDEX"` - 无索引基线
  - `"OPTIMAL"` - 最优配置（需要预先计算）
  - `"MAB"` - 传统多臂老虎机方法（用于对比）

## 运行方法

### 1. 激活虚拟环境
```bash
source /home/qihan/.venv/bin/activate
```

### 2. 运行DDQN实验
```bash
cd /home/qihan/DBABandits
python -m simulation.sim_run_ddqn_experiment
```

### 3. 修改实验配置

在 `config/exp.conf` 中修改：
```ini
[general]
run_experiment = job_benchmark_ddqn  # 指定运行的实验
```

或者在脚本中修改 `exp_id_list`：
```python
exp_id_list = ["job_benchmark_ddqn"]
```

## GPU 使用

### DDQN 会使用 GPU 吗？

**会的！** DDQN使用TensorFlow/Keras构建神经网络，如果系统有可用的GPU：

1. **TensorFlow会自动检测并使用GPU**
2. **加速神经网络训练**（特别是在大规模实验中）
3. **可以通过以下方式验证**：

```bash
# 检查GPU是否可用
nvidia-smi

# 运行时TensorFlow会输出GPU信息
python -c "import tensorflow as tf; print(tf.config.list_physical_devices('GPU'))"
```

### 强制使用/禁用GPU

如果需要控制GPU使用，可以在脚本开头添加：

```python
import os
# 禁用GPU，仅使用CPU
os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

# 或指定使用特定GPU
os.environ['CUDA_VISIBLE_DEVICES'] = '0'  # 使用第一块GPU
```

## 网络架构

DDQN使用的神经网络（在 `bandits/rl_ddqn_v2.py` 中定义）：

```python
Sequential([
    Dense(8, activation='relu'),    # 隐藏层1
    Dense(8, activation='relu'),    # 隐藏层2
    Dense(8, activation='relu'),    # 隐藏层3
    Dense(8, activation='relu'),    # 隐藏层4
    Dense(action_count, activation='softmax')  # 输出层
])
```

## 输出结果

实验完成后会生成：

```
experiments/job_benchmark_ddqn/
├── job_benchmark_ddqn.log          # 详细日志
├── reports.pickle                   # 实验数据（pickle格式）
├── *.png                            # 性能对比图表
└── comparison_tables/               # 对比表格
```

## 与MAB的区别

| 特性 | MAB (C3-UCB) | DDQN |
|------|--------------|------|
| 算法类型 | 统计学习 | 深度强化学习 |
| GPU使用 | ❌ 否 | ✅ 是 |
| 探索策略 | UCB置信区间 | ε-greedy + 经验回放 |
| 状态表示 | 简单上下文向量 | 高维状态向量 |
| 收敛速度 | 较快 | 需要热身 |
| 适用场景 | 静态/小规模工作负载 | 动态/大规模工作负载 |

## 性能监控

运行时可以监控：

```bash
# 监控GPU使用情况
watch -n 1 nvidia-smi

# 查看实时日志
tail -f experiments/job_benchmark_ddqn/job_benchmark_ddqn.log
```

## 故障排除

### 内存不足
- 减少 `BATCH_SIZE` 或 `MEMORY_CAPACITY`
- 减少网络层数或神经元数量

### GPU内存不足
```python
# 在 rl_ddqn_v2.py 开头添加
import tensorflow as tf
gpus = tf.config.experimental.list_physical_devices('GPU')
if gpus:
    tf.config.experimental.set_memory_growth(gpus[0], True)
```

### 训练不收敛
- 增加 `hyp_rounds`（热身轮数）
- 调整学习率和探索参数
- 检查工作负载是否太复杂

## 参考

- 论文实现基于: DBA Bandits with Deep Reinforcement Learning
- TensorFlow文档: https://www.tensorflow.org/
- Keras API: https://keras.io/
