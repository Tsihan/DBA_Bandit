# Join Order Benchmark (JOB) Integration

本项目已集成 Join Order Benchmark (JOB) 查询集，用于在 IMDB 数据库上进行索引调优。

## 📁 文件说明

### 工作负载文件

1. **job_benchmark_static.json** (10 个精选查询)
   - 包含 10 个有代表性的 JOB 查询
   - 涵盖从简单到复杂的不同连接模式
   - 适合快速测试和原型验证

2. **job_all_queries.json** (113 个完整查询)
   - 包含所有 113 个 JOB benchmark 查询
   - 从 `/home/qihan/load_imdb/job_queries` 自动生成
   - 适合完整的性能评估

### 实验配置

在 `config/exp.conf` 中定义了两个实验：

#### 1. `job_benchmark_mab` (精选 10 个查询)
```ini
[job_benchmark_mab]
rounds = 10
workload_file = resources/workloads/job_benchmark_static.json
queries_start = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
queries_end = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
```

#### 2. `job_full_mab` (完整 113 个查询)
```ini
[job_full_mab]
rounds = 20
workload_file = resources/workloads/job_all_queries.json
queries_start = [0, 6, 12, 18, 24, 30, ...]  # 每轮 6 个查询
queries_end = [6, 12, 18, 24, 30, 36, ...]
```

## 🚀 使用方法

### 1. 运行精选查询实验（快速测试）

```bash
# 修改 sim_run_experiment.py
exp_id_list = ["job_benchmark_mab"]

# 运行
cd /home/qihan/DBABandits
python3 simulation/sim_run_experiment.py
```

### 2. 运行完整 JOB 实验

```bash
# 修改 sim_run_experiment.py
exp_id_list = ["job_full_mab"]

# 运行
cd /home/qihan/DBABandits
python3 simulation/sim_run_experiment.py
```

### 3. 重新生成工作负载（如果更新了查询文件）

```bash
cd /home/qihan/DBABandits
python3 scripts/generate_job_workload.py
```

这将重新扫描 `/home/qihan/load_imdb/job_queries` 目录并生成新的 `job_all_queries.json`。

## 📊 查询复杂度

精选的 10 个查询涵盖以下场景：

1. **Query 1** (1a.sql): 5 表连接 - 公司类型 + 电影信息索引
2. **Query 2** (2a.sql): 5 表连接 - 公司名称 + 关键词
3. **Query 3** (3a.sql): 4 表连接 - 关键词 + 电影信息
4. **Query 4** (4a.sql): 5 表连接 - 评分 + 关键词过滤
5. **Query 5** (6a.sql): 5 表连接 - 演员 + 关键词搜索
6. **Query 6** (7a.sql): 8 表连接 - 复杂人物传记查询
7. **Query 7** (10a.sql): 7 表连接 - 配音角色 + 公司过滤
8. **Query 8** (13a.sql): 9 表连接 - 多信息类型关联
9. **Query 9** (复杂): 12 表连接 - 完整演员表 + 多关键词
10. **Query 10** (复杂): 12 表连接 - 超级英雄角色分析

## 🔧 自定义配置

### 调整实验参数

编辑 `config/exp.conf`：

```ini
[job_benchmark_mab]
reps = 1              # 重复次数
rounds = 10           # 轮数
hyp_rounds = 0        # 假设索引轮数（PostgreSQL 必须为 0）
max_memory = 25000    # 最大内存限制（MB）
input_alpha = 1       # MAB 算法参数
time_weight = 5       # 时间权重
```

### 修改查询批次大小

如果要在 `job_full_mab` 中每轮运行不同数量的查询：

```ini
# 例如每轮 10 个查询
queries_start = [0, 10, 20, 30, ...]
queries_end = [10, 20, 30, 40, ...]
```

## 📈 结果分析

实验结果将保存在：
```
experiments/
  job_benchmark_mab/     # 10 查询实验结果
    rep_1/
      plots/
      logs/
  job_full_mab/          # 113 查询实验结果
    rep_1/
      plots/
      logs/
```

## 🎯 JOB 查询特点

- **真实工作负载**: 基于实际 IMDB 数据集
- **复杂连接**: 2-16 个表的各种连接模式
- **多样化谓词**: 字符串匹配、范围查询、IN 子句
- **聚合函数**: MIN/MAX/COUNT 等聚合操作

## ⚠️ 注意事项

1. **PostgreSQL 限制**: `hyp_rounds` 必须设置为 0（不支持假设索引）
2. **内存使用**: 完整 113 查询实验可能需要较长时间
3. **数据库连接**: 确保 `config/db.conf` 中 PostgreSQL 配置正确
4. **查询超时**: 某些复杂查询可能运行较慢，根据需要调整超时设置

## 🔗 相关资源

- [Join Order Benchmark 论文](https://db.in.tum.de/~leis/papers/lookingglass.pdf)
- [IMDB 数据集下载](http://homepages.cwi.nl/~boncz/job/imdb.tgz)
- 原始查询目录: `/home/qihan/load_imdb/job_queries`
