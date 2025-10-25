# 🚀 DBABandits PostgreSQL + JOB Benchmark 快速启动指南

## 📋 概述

已成功将 DBABandits 从 MSSQL 迁移到支持 PostgreSQL，并集成了完整的 Join Order Benchmark (JOB) 查询集。

## ✅ 已完成的工作

### 1. PostgreSQL 支持
- ✅ 创建 `database/sql_helper_postgres.py` (546 行)
- ✅ 创建 `database/sql_helper.py` 门面模式
- ✅ 更新所有导入 (17 个文件)
- ✅ 跨平台路径处理 (`os.path.join`)
- ✅ 配置文件支持 PostgreSQL (`config/db.conf`)

### 2. JOB Benchmark 集成
- ✅ 从 `/home/qihan/load_imdb/job_queries` 提取所有 113 个查询
- ✅ 生成 `job_all_queries.json` (113 个查询)
- ✅ 精选 `job_benchmark_static.json` (10 个代表性查询)
- ✅ 创建两个实验配置：`job_benchmark_mab` 和 `job_full_mab`

### 3. 工具脚本
- ✅ `scripts/generate_job_workload.py` - 自动从 SQL 文件生成工作负载

## 🎯 可用的实验配置

### 选项 1: 精选 10 查询（推荐开始）
```bash
# 在 simulation/sim_run_experiment.py 中设置
exp_id_list = ["job_benchmark_mab"]
```
- **轮数**: 10
- **查询数**: 10 个精选的 JOB 查询
- **运行时间**: 约 20-30 分钟（取决于数据库大小）

### 选项 2: 完整 113 查询
```bash
exp_id_list = ["job_full_mab"]
```
- **轮数**: 20
- **查询数**: 所有 113 个 JOB 查询
- **运行时间**: 可能需要数小时

### 选项 3: 简单测试（原始 5 查询）
```bash
exp_id_list = ["imdb_postgres_mab"]
```
- **轮数**: 5
- **查询数**: 5 个简单测试查询

## 📝 运行步骤

### 第 1 步: 配置数据库连接

编辑 `config/db.conf`：

```ini
[POSTGRESQL]
host = localhost
port = 5432
database = imdbload
user = your_username        # 改为你的用户名
password = your_password    # 改为你的密码
schema = public
dataset = IMDB
```

### 第 2 步: 选择实验

编辑 `simulation/sim_run_experiment.py` 第 14 行：

```python
# 选择一个：
exp_id_list = ["job_benchmark_mab"]    # 推荐：10 查询
# exp_id_list = ["job_full_mab"]       # 完整：113 查询
# exp_id_list = ["imdb_postgres_mab"]  # 测试：5 查询
```

### 第 3 步: 运行实验

```bash
cd /home/qihan/DBABandits
python3 simulation/sim_run_experiment.py
```

### 第 4 步: 查看结果

```bash
# 结果保存在
ls experiments/job_benchmark_mab/rep_1/

# 查看日志
tail -f experiments/job_benchmark_mab/rep_1/logs/experiment.log
```

## 🔧 高级配置

### 调整实验参数

编辑 `config/exp.conf`：

```ini
[job_benchmark_mab]
reps = 1              # 重复实验次数
rounds = 10           # 每次实验的轮数
hyp_rounds = 0        # 假设索引轮数（PostgreSQL 必须为 0）
max_memory = 25000    # 索引内存限制（MB）
input_alpha = 1       # C3-UCB 算法的 alpha 参数
time_weight = 5       # 时间权重 vs 内存权重
components = ["MAB", "NO_INDEX"]  # 对比组件
```

### 重新生成工作负载

如果你的 JOB 查询目录有更新：

```bash
cd /home/qihan/DBABandits
python3 scripts/generate_job_workload.py
```

## 📊 工作负载文件对比

| 文件 | 查询数 | 大小 | 用途 |
|------|--------|------|------|
| `imdb_postgres_static.json` | 5 | 1.7 KB | 快速测试 |
| `job_benchmark_static.json` | 10 | 12 KB | 推荐起点 |
| `job_all_queries.json` | 113 | 102 KB | 完整评估 |

## 🎯 JOB 查询示例

### 简单查询 (2a.sql)
```sql
SELECT MIN(t.title) AS movie_title 
FROM company_name AS cn, keyword AS k, 
     movie_companies AS mc, movie_keyword AS mk, title AS t 
WHERE cn.country_code ='[de]' 
  AND k.keyword ='character-name-in-title' 
  AND cn.id = mc.company_id 
  AND mc.movie_id = t.id 
  AND t.id = mk.movie_id 
  AND mk.keyword_id = k.id 
  AND mc.movie_id = mk.movie_id;
```

### 复杂查询 (13a.sql - 9 表连接)
```sql
SELECT MIN(mi.info) AS release_date, 
       MIN(miidx.info) AS rating, 
       MIN(t.title) AS german_movie 
FROM company_name AS cn, company_type AS ct, 
     info_type AS it, info_type AS it2, kind_type AS kt, 
     movie_companies AS mc, movie_info AS mi, 
     movie_info_idx AS miidx, title AS t 
WHERE cn.country_code ='[de]' 
  AND ct.kind ='production companies' 
  AND it.info ='rating' 
  AND it2.info ='release dates' 
  AND kt.kind ='movie' 
  AND mi.movie_id = t.id 
  AND it2.id = mi.info_type_id 
  -- ... more joins
```

## 🐛 故障排除

### 问题 1: ModuleNotFoundError

**原因**: 从错误的目录运行

**解决方案**:
```bash
# 始终从项目根目录运行
cd /home/qihan/DBABandits
python3 simulation/sim_run_experiment.py
```

### 问题 2: psycopg2 not found

**解决方案**:
```bash
pip install psycopg2-binary
# 或
sudo apt-get install python3-psycopg2
```

### 问题 3: Connection refused

**解决方案**:
1. 检查 PostgreSQL 是否运行: `sudo systemctl status postgresql`
2. 验证 `pg_hba.conf` 允许本地连接
3. 确认 `config/db.conf` 中的凭据正确

### 问题 4: 查询超时

**解决方案**:
```python
# 在 database/sql_helper_postgres.py 中调整
# 搜索 cursor.execute() 并添加超时参数
```

## 📈 预期结果

运行成功后，你将看到：

```
experiments/job_benchmark_mab/
  rep_1/
    plots/
      batch_time_plot.png           # 批次时间对比
      index_creation_cost_plot.png  # 索引创建成本
      query_execution_cost_plot.png # 查询执行成本
    logs/
      experiment.log                # 详细日志
    results/
      mab_results.csv              # MAB 结果
      no_index_results.csv         # 无索引基准
```

## 🔗 相关资源

- **JOB 详细文档**: `resources/workloads/JOB_README.md`
- **PostgreSQL 迁移说明**: `README.md` (PostgreSQL Quick Start 部分)
- **原始 JOB 查询**: `/home/qihan/load_imdb/job_queries/`
- **数据库配置**: `config/db.conf`
- **实验配置**: `config/exp.conf`

## 💡 提示

1. **首次运行**: 使用 `job_benchmark_mab` (10 查询) 验证设置
2. **索引建议**: 实验会自动创建和删除索引，无需手动干预
3. **性能监控**: 使用 `pg_stat_statements` 扩展监控查询性能
4. **备份数据**: 虽然只操作索引，建议先备份重要数据

## 🎉 下一步

1. ✅ 配置 `db.conf` 数据库凭据
2. ✅ 选择实验配置（推荐 `job_benchmark_mab`）
3. ✅ 运行实验
4. ✅ 分析结果图表和日志
5. ✅ 根据结果调优参数
6. ✅ 尝试完整的 113 查询实验

---

**准备好了吗？** 运行：
```bash
cd /home/qihan/DBABandits
python3 simulation/sim_run_experiment.py
```

祝实验顺利！🚀
