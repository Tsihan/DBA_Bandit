# 🎯 JOB Benchmark 集成 - 变更摘要

**日期**: 2025-10-24  
**目标**: 集成 Join Order Benchmark (JOB) 查询到 DBABandits

---

## 📦 新增文件

### 工作负载文件
1. **resources/workloads/job_benchmark_static.json** (12 KB)
   - 10 个精选的代表性 JOB 查询
   - 涵盖 5-12 表连接的各种复杂度
   - 包含完整的谓词和负载元数据

2. **resources/workloads/job_all_queries.json** (102 KB)
   - 所有 113 个 JOB benchmark 查询
   - 从 `/home/qihan/load_imdb/job_queries` 自动生成
   - 每个查询一行 JSON 格式

### 工具脚本
3. **scripts/generate_job_workload.py** (新创建)
   - 自动扫描 JOB 查询目录
   - 提取表名、谓词、负载信息
   - 生成 DBABandits 兼容的工作负载 JSON

### 文档
4. **resources/workloads/JOB_README.md** (4.2 KB)
   - JOB 集成详细说明
   - 查询复杂度分析
   - 配置和使用指南

5. **QUICKSTART_JOB.md** (主目录)
   - 快速启动指南
   - 完整的运行步骤
   - 故障排除手册

---

## 🔧 修改文件

### 配置文件
1. **config/exp.conf**
   - ✏️ 修改 `[general]` 部分: `run_experiment = job_benchmark_mab`
   - ➕ 新增 `[job_benchmark_mab]` 实验配置 (10 查询)
   - ➕ 新增 `[job_full_mab]` 实验配置 (113 查询)

   ```ini
   [job_benchmark_mab]
   rounds = 10
   workload_file = resources/workloads/job_benchmark_static.json
   queries_start = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
   queries_end = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
   
   [job_full_mab]
   rounds = 20
   workload_file = resources/workloads/job_all_queries.json
   queries_start = [0, 6, 12, ..., 108, 113]  # 每轮 ~6 查询
   queries_end = [6, 12, ..., 113, 113]
   ```

### 主程序
2. **simulation/sim_run_experiment.py**
   - ✏️ 第 14 行: `exp_id_list = ["job_benchmark_mab"]`
   - 从 `imdb_postgres_mab` 改为 `job_benchmark_mab`

---

## 📊 工作负载对比

| 配置 | 查询数 | 文件 | 轮数 | 适用场景 |
|------|--------|------|------|----------|
| `imdb_postgres_mab` | 5 | imdb_postgres_static.json | 5 | 快速测试连接性 |
| `job_benchmark_mab` | 10 | job_benchmark_static.json | 10 | **推荐起点** |
| `job_full_mab` | 113 | job_all_queries.json | 20 | 完整性能评估 |

---

## 🎯 精选的 10 个 JOB 查询

| ID | 来源 | 表数 | 复杂度 | 关键特性 |
|----|------|------|--------|----------|
| 1 | 1a.sql | 5 | 中 | 公司类型 + 电影排名 |
| 2 | 2a.sql | 5 | 中 | 德国公司 + 关键词 |
| 3 | 3a.sql | 4 | 低 | 续集关键词 + 地理过滤 |
| 4 | 4a.sql | 5 | 中 | 评分过滤 + 续集 |
| 5 | 6a.sql | 5 | 中 | Marvel 演员搜索 |
| 6 | 7a.sql | 8 | 高 | 人物传记 + 多条件 |
| 7 | 10a.sql | 7 | 高 | 配音角色 + 俄罗斯电影 |
| 8 | 13a.sql | 9 | 高 | 德国电影 + 多信息类型 |
| 9 | 复杂 | 12 | 很高 | 完整演员表 + 暴力电影 |
| 10 | 复杂 | 12 | 很高 | 超级英雄角色分析 |

---

## 🚀 使用方法

### 快速开始（推荐）

```bash
# 1. 配置数据库（如果还没做）
vim config/db.conf  # 设置 PostgreSQL 连接信息

# 2. 运行 10 查询实验
cd /home/qihan/DBABandits
python3 simulation/sim_run_experiment.py

# 3. 查看结果
ls experiments/job_benchmark_mab/rep_1/plots/
```

### 运行完整 113 查询

```bash
# 修改实验配置
vim simulation/sim_run_experiment.py
# 改为: exp_id_list = ["job_full_mab"]

# 运行（可能需要数小时）
python3 simulation/sim_run_experiment.py
```

### 重新生成工作负载

```bash
# 如果 JOB 查询文件有更新
python3 scripts/generate_job_workload.py
```

---

## 🔍 查询示例

### 简单查询 (Query 2 - 2a.sql)
```sql
-- 5 表连接：德国公司 + 角色名称关键词
SELECT MIN(t.title) AS movie_title 
FROM company_name AS cn, keyword AS k, 
     movie_companies AS mc, movie_keyword AS mk, title AS t 
WHERE cn.country_code = '[de]' 
  AND k.keyword = 'character-name-in-title'
  AND cn.id = mc.company_id 
  AND mc.movie_id = t.id 
  AND t.id = mk.movie_id 
  AND mk.keyword_id = k.id 
  AND mc.movie_id = mk.movie_id;
```

### 复杂查询 (Query 8 - 13a.sql)
```sql
-- 9 表连接：德国电影评分和发布日期
SELECT MIN(mi.info) AS release_date, 
       MIN(miidx.info) AS rating, 
       MIN(t.title) AS german_movie 
FROM company_name AS cn, company_type AS ct, info_type AS it, 
     info_type AS it2, kind_type AS kt, movie_companies AS mc, 
     movie_info AS mi, movie_info_idx AS miidx, title AS t 
WHERE cn.country_code ='[de]' 
  AND ct.kind ='production companies' 
  AND it.info ='rating' 
  AND it2.info ='release dates' 
  AND kt.kind ='movie' 
  AND mi.movie_id = t.id 
  AND it2.id = mi.info_type_id 
  AND kt.id = t.kind_id 
  AND mc.movie_id = t.id 
  AND cn.id = mc.company_id 
  AND ct.id = mc.company_type_id 
  AND miidx.movie_id = t.id 
  AND it.id = miidx.info_type_id 
  AND mi.movie_id = miidx.movie_id 
  AND mi.movie_id = mc.movie_id 
  AND miidx.movie_id = mc.movie_id;
```

---

## 📈 预期输出

### 实验结果目录结构
```
experiments/
  job_benchmark_mab/
    rep_1/
      plots/
        batch_time_plot.png
        index_creation_cost_plot.png
        query_execution_cost_plot.png
      logs/
        experiment.log
        mab_arm_selection.log
      results/
        mab_c3ucb_results.csv
        no_index_results.csv
        config_info.json
```

### 性能指标
- **批次时间**: MAB vs NO_INDEX 对比
- **查询执行成本**: 有索引 vs 无索引
- **索引创建成本**: 各个索引的创建开销
- **臂选择**: C3-UCB 算法的索引选择历史

---

## ⚙️ 实验参数说明

### job_benchmark_mab 配置
```ini
reps = 1              # 重复实验 1 次
rounds = 10           # 10 轮，每轮 1 个查询
hyp_rounds = 0        # PostgreSQL 不支持假设索引
max_memory = 25000    # 索引最大内存 25 GB
input_alpha = 1       # C3-UCB 探索参数
time_weight = 5       # 时间权重（相对于内存）
components = ["MAB", "NO_INDEX"]  # 对比 MAB 和无索引基准
```

### 调优建议
- **增加 rounds**: 更多轮次获得更稳定的结果
- **调整 max_memory**: 根据系统内存限制
- **修改 input_alpha**: 
  - α > 1: 更多探索（尝试更多索引）
  - α < 1: 更多利用（偏好已知好的索引）

---

## 🐛 已知限制

1. **假设索引**: PostgreSQL 版本不支持 hypothetical indexes
   - `hyp_rounds` 必须设置为 0
   - 所有索引都会实际创建和删除

2. **查询超时**: 某些复杂 JOB 查询可能运行很慢
   - 可能需要在 `sql_helper_postgres.py` 中增加超时限制

3. **谓词提取**: 自动提取的谓词可能不完整
   - `generate_job_workload.py` 使用简单的正则表达式
   - 对索引选择影响有限（主要依赖实际执行计划）

---

## 📚 相关文档

- **详细使用**: `QUICKSTART_JOB.md`
- **JOB 说明**: `resources/workloads/JOB_README.md`
- **PostgreSQL 迁移**: `README.md` (PostgreSQL Quick Start)
- **数据库配置**: `config/db.conf`
- **实验配置**: `config/exp.conf`

---

## ✅ 检查清单

在运行实验前确认：

- [ ] PostgreSQL 服务正在运行
- [ ] `config/db.conf` 中凭据正确
- [ ] imdbload 数据库已加载 IMDB 数据
- [ ] Python 依赖已安装 (`psycopg2`, `pandas`, etc.)
- [ ] 从项目根目录运行脚本
- [ ] `exp_id_list` 设置为期望的实验

---

## 🎉 总结

**新增查询**: 113 个 JOB benchmark 查询  
**新增配置**: 2 个实验配置 (10 和 113 查询)  
**新增脚本**: 1 个自动生成工具  
**新增文档**: 2 个使用指南  

**当前状态**: ✅ 可以直接运行 `job_benchmark_mab` 实验

**推荐第一步**:
```bash
cd /home/qihan/DBABandits
python3 simulation/sim_run_experiment.py
```

祝实验顺利！🚀
