# 筛选范围校准样本

用于验证 `screen.py` 的 SCOPE 提示词改动：这些论文都出现在 README 里或曾被
候选池捞到过，其中一部分明显是「LLM × data」而不是「LLM for DB」。改动的目标
是让第二类被拒。

## 应当拒绝（数据库只是数据来源 / 对象不是 DBMS）

| 论文 | 为什么该拒 |
| --- | --- |
| Data.Readme: Documenting Table Relationships for Diverse Data Tasks | 为表关系写文档，供模型消费；DBMS 未变 |
| AgentOnto: Ontology-Guided LLM Agents for Enterprise Data Analytics | 对象是企业数据分析问答 |
| EvoOntology: A Self-Evolving Ontology Layer for Data Agents | 本体层，存在数据库里但对象不是 DBMS |
| A Governed Agent Architecture for Natural-Language Dashboard Generation | 生成看板 |
| Same Context, Different Agents: ... Semantic Layers, Multi-Agent Orchestration | 语义层与多智能体编排，DB 是背景 |
| Symbolic Separation: Grounding Deep Agents in Knowledge Graphs | 知识图谱，属硬性排除 |
| DeepPrep: An LLM-Powered Agentic System for Autonomous Data Preparation | 数据准备，属数据工程 |
| DataMosaic: Constraint-Driven Document-to-Database Construction | 文档入库，对象是数据产品 |
| SemDistill: Bootstrapping a ... Semantic Table Annotator | 表/列标注 |
| TACO: Task-Aware Column Description Generation Using LLMs | 列描述生成 |
| Tytan: Interactive Neurosymbolic Construction of Analytic Semantic Schemas | 语义层构建 |
| Conceptual schema inference for tabular datasets using LLMs | 概念模式推断，对象是数据集 |
| Discovery-Driven Integration of Disjoint Tables via Text | 表集成/数据发现 |
| Open Tabular Insight Extraction | 表格洞察抽取 |
| Metadata Reconstruction from Values Alone | 列语义恢复，元数据 |
| Polaris: Learning to Generate Table Descriptions from Retrieval Feedback | 表描述生成 |
| From Research Questions to Columns: Operationalization-Aware Data Discovery | 数据发现 |
| Policy-Aware Federated Query Orchestration Across Energy Data Spaces | 能源数据空间联邦编排，对象不是 DBMS |
| Synthesis Through Simulation: Generating Coherent Enterprise Data | 造企业数据，属数据生成/ML |

## 应当保留（DBMS 是研究对象）

| 论文 | 为什么该留 |
| --- | --- |
| MongoBench: Do LLMs Know What a MongoDB Query Will Do? | 评测对象是查询语义 |
| DiagDBench: Evaluating Agentic LLMs on Interactive Database Diagnosis | 评测数据库诊断 |
| DBA-Bench: A Production-Fidelity Benchmark for LLM-Based Database Operations Agents | 评测 DBA 操作 |
| Stop Handcrafting Your Engine! GenDB-V | 生成并验证数据库引擎 |
| Correctness Firewalls for Synthesized Database Components | 数据库组件正确性 |
| Prompt as a Data Type: In-Database LLM Prompt Management and Rewriting | 库内算子 |
| Rethinking Query Optimization for Multi-Agent Systems | 查询优化 |
| Replace or Augment: Rethinking the Role of Learned Indexes | 学习索引 |
| When Is One Query per Template Enough? Adapting Learned Cost Models | 学习代价模型 |
| DBcover: A White-box SQL Test Generation Framework | SQL 测试生成 |
| Logos: Certified Order-Sensitive SQL Rewrites | SQL 重写等价性 |
| Supervised and LLM-Augmented Cardinality Estimation | 基数估计 |
| CATune: Structural Constraint-Aware Bayesian Optimization for DBMS Configuration Tuning | 配置调优 |
| HakiCC: LLM-Driven Multi-Agent Design and Optimization of Concurrency Control Protocols | 并发控制协议 |
| JetStream: Generating Verified Query Accelerators | 查询加速器 |
| Breaking Database Lock-in: Agentic Regeneration of High Performance Storage Readers | 存储读取器生成 |
| DBAgent: An RL-Based Agent for Autonomous Database Operations and Maintenance | 自治运维 |

## 边界（人工判断，应落到 review）

| 论文 | 为什么两可 |
| --- | --- |
| EnvLunch: The Environment as a Free Lunch for Learning to Interact | DB 只在摘要里作为可执行环境出现；贡献是 agent 训练方法 |
| Conversational Query Engine for Mixed-Modality Heterogeneous Enterprise Data Sources | 有点像查询引擎，又有点像企业数据问答 |
| Evaluating Enterprise Analytics Agents | 评测方法，对象是企业分析 agent |
| Leakage-Resistant Evaluation of AI-Generated Database Specifications | 对象是数据库规格，但与迁移评估相关 |

## 实测结果

`scripts/calibrate_prompt.py` 在 40 篇标注样本上的 A/B（同一模型、同一判据、只换提示词）：

| | 旧提示词 | 新提示词 ×1 | 新提示词 ×3（多数票） |
| --- | --- | --- | --- |
| 准确率 | 67% | 89% | **94%** |
| 该拒的拒掉（召回） | 58% | 95% | **95%** |
| 该收的收进（召回） | 100% | 82% | **94%** |
| 该拒却收（泄漏） | 8 篇 | 1 篇 | **1 篇** |

旧提示词把那 8 篇 LLM × data 全收了（表关系文档化、本体层、看板生成、列描述生成、
语义层构建、概念模式推断、表描述生成、表标注），正好就是列表里混进去的那一类。

新提示词剩下的 1 篇泄漏是 `Policy-Aware Federated Query Orchestration Across Energy
Data Spaces`（边界项，判哪边都说得过去），1 篇误杀是 `Rethinking Query Optimization for
Multi-Agent Systems`（"多智能体系统"的查询优化，模型读成了 agent 编排）。

### 两个反直觉的发现

1. **title-only 判定很不准。** 校准文件里的标题是缩写的（`Logos: Certified
   Order-Sensitive SQL Rewrites` 少了后半截），第一版按精确键匹配取摘要，40 篇里
   22 篇拿不到摘要，于是凭空出现 3 篇误杀。改成"缩写匹配"（把标题切成 token 序列，
   允许校准标题是真实标题的有序子序列）后降到 4 篇。
2. **多跑几遍再取多数票，收益比换提示词还大。** 单遍 89% → 三遍 94%，
   因为剩下的误差大多来自模型在个别论文上首鼠两端，而不是判据不对。
   流水线仍然单遍（成本敏感），本地脚本默认三遍。

不稳定清单（三遍结果不一致的 4 篇）比错误清单更有用：判两次翻脸说明这是判断题，
不该让任何一个模型替人拍板——所以本地脚本把它们一律降为 `review`。
