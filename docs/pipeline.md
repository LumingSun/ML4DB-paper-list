# ML4DB 论文自动更新流水线

把"发现新论文 → 判断是否收录 → 归入哪个小节 → 校验格式/去重 → 开 PR"固化下来。
设计文档见 [docs/superpowers/specs/2026-10-27-ai4db-paper-auto-collection-design.md](../superpowers/specs/2026-10-27-ai4db-paper-auto-collection-design.md)。

## 它保证什么

- **不产生幻觉论文**：标题 / 会议 / 年份 / 链接全部来自 arXiv API 与 Crossref 的返回记录，
  模型只有一个决策字段（收 / 不收 + 归哪个小节），没有可编造的字段。
- **不产生重复**：三层去重（外部 ID → 标题归一 → token 模糊匹配）。
- **不改已有内容**：校验器只接受"新增行"的 diff，删改任何已有行都会被拦下。
- **不合格就不出 PR**：格式、链接可解析、无新重复、只增不改，任一不过就失败，不出 PR。

## 每周自动跑

`.github/workflows/weekly-update.yml`，北京时间周一 09:00。需要仓库 Secret `LLM_API_KEY`
（OpenAI 兼容接口；可选 Variables `LLM_BASE_URL`、`LLM_MODEL`）。

手动触发：Actions → weekly-paper-update → Run workflow，可填 `since` 和 `dry_run`。

筛选后端二选一（仓库 Variable `SCREENER`）：

- `llm`（默认）：OpenAI 兼容 chat 接口，需要 Secret `LLM_API_KEY`；批量送 prompt，一次判 8–12 条。
- `jev`：TypeSafe Jev-1.13 decision 模型（`/api/v1/decisions`），需要 Secret `JEV_API_KEY`；
  每条论文一个请求，`in_scope` / `ai_core` / `notable` 用 noul 概率，`section` 用 choice，返回置信度。
  更便宜更快，但会多收增量式论文。
- `double`（双层确认，需同时配 `LLM_API_KEY` 和 `JEV_API_KEY`）：两个后端独立判断，
  **收录要求两者都收**；"ML 是不是本文贡献"这一项以准确率更高的 DeepSeek 为准
  （可用 `combine --ai-core-policy both|llm|any` 调整）。分歧条目全部丢弃。

两个后端共用的硬约束：模型只能从枚举小节里选；另外必须判定 `ai_core`——论文的 AI 成分是
"贡献"还是"动机"。只把 AI 当动机的论文（例如一篇 LSM 写暂停优化里提到 "AI serving"）
会被剔除，这是"标题看不出和 AI4DB 有什么关系"这类条目的主要来源。

## 本机跑

```bash
pip install -r requirements.txt
cd scripts

# 采集（需要代理时先 export https_proxy=...）
python -m ml4db harvest --since 2026-04-21 --out /tmp/cands.json

# 词法预筛 + 去重
python -m ml4db filter --in /tmp/cands.json --out /tmp/pending.json --dropped /tmp/dropped.json

# 模型筛选（走 API）
LLM_API_KEY=sk-... python -m ml4db screen --in /tmp/pending.json --out /tmp/accepted.json
# 或 Jev 决策模型
JEV_API_KEY=dk-... python -m ml4db screen --screener jev --in /tmp/pending.json --out /tmp/accepted.json
# 或双层确认（两个都配）
LLM_API_KEY=... JEV_API_KEY=... python -m ml4db screen --screener double --in /tmp/pending.json --out /tmp/accepted.json

# 补课用：按小节给 arXiv 条目设上限（已发表的不受限制）
python -m ml4db select --in /tmp/accepted.json --out /tmp/selected.json --arxiv-per-section 6

# 校验 + 开 PR（--dry-run 只校验并打印）
python -m ml4db apply --in /tmp/accepted.json --dry-run
python -m ml4db apply --in /tmp/accepted.json --pr --slug 20261027 --title "[Auto] 新增 AI4DB 论文（2026-10-27）"
```

离线 / 人工复核路径：`python -m ml4db batches --in /tmp/pending.json --dir /tmp/batches --size 25`
导出带 abstract 的分批文件，人工或 agent 复核后把 verdicts 合并成 `accepted.json`
（格式见 `scripts/ml4db/screen.py:_apply`），再走 `apply`。

## 清理存量重复

```bash
python -m ml4db cleanup --manifest cleanup/manifest.json --dry-run
python -m ml4db cleanup --manifest cleanup/manifest.json --pr --slug 20261027
```

manifest 里每条给出要删的行号、保留的行号与理由；程序会先校验两行确实是同一篇论文。

## 测试

```bash
python -m pytest scripts/tests -q
```

单测覆盖：标题归一与模糊匹配、小节解析与插入、去重三层、校验器（含 PR #36 的残缺条目
用例、PR #37 的删改用例、存量重复的祖父条款、幂等性）。

## 收录范围：以「DBMS 是否为研究对象」判定

流水线运行两周后暴露了一个判据问题，不是阈值问题。一批 **LLM × data** 论文进了列表：
表关系文档化、本体层、看板生成、表/列标注、数据准备、数据发现。它们读写关系型数据、
生成 SQL、发在 VLDB/SIGMOD，词表全中，连"ML 应用于数据库"这条判据也能对上——但它们
真正做的是分析结论、元数据或数据产品，DBMS 本身没有被改动。

现在的判据是：**只有 DBMS 是论文改动、操作、构建或度量的对象才算在范围内。**
"用了表"、"写了 SQL"、"数据在库里"都不构成在范围内。提示词里给了两条自检：

1. 把数据换成 CSV，贡献还成立吗？成立 → 数据库是偶然的。
2. 数据库系统研究者会不会认为这是对数据库系统的贡献？

显式拒绝类：BI/看板、chat-with-your-data、语义层与指标层、数据目录与数据发现、
数据准备与清洗、表/列标注与文档化、ETL、本体与知识图谱构建、文档/表格分析。

### 本地精查脚本

流水线要无人值守，所以快、便宜、失败即停。需要更准确的结论时用本地脚本——它慢、
花几分钱、并且刁钻：

```bash
cp config/audit.env.example ~/.config/ml4db/audit.env && chmod 600 ~/.config/ml4db/audit.env
# 填入 LLM_API_KEY（必填）、JEV_API_KEY（可选，独立复核）

python3 scripts/audit_scope.py --recent-commits 2   # 最近两个自动 PR 加了什么
python3 scripts/audit_scope.py --git-since d1f0578  # 某次提交之后新增的
python3 scripts/audit_scope.py --section "LLM4DB & Agent for DB"
python3 scripts/audit_scope.py --all                # 全量复查
```

- **摘要解析**：arXiv 批量 `id_list` → Crossref 批量 DOI → 标题检索回退
  （Crossref→OpenAlex）。老条目即使没有链接也能拿到摘要。摘要与判定都缓存。
- **判定**：DeepSeek 多轮（默认 3 遍）+ Jev 独立复核。
- **定向原则**：证据只能让结论变软（keep→review），不能变硬。删错一条比漏一条更伤信任。
- **自洽性**：对象在范围内却给 drop（或反之）判为模型自相矛盾，降为 review；
  多轮不一致同样降为 review；无摘要时禁止 drop。
- 结果写到 `.ml4db/audit/report.md`（表格）与 `report.json`（可复算）。

`--no-llm` 只跑 Jev（省事，但精度低）；`--no-jev` 只跑 DeepSeek。

### 改提示词前先量

`docs/scope-calibration.md` 手工标注了 40 篇（拒绝 19 / 保留 17 / 边界 4）。
改 `screen.py` 的 `SCOPE` 或 `docs/scope-calibration.md` 后，直接量：

```bash
python3 scripts/calibrate_prompt.py              # 测当前提示词
python3 scripts/calibrate_prompt.py --prompt-file /tmp/new_scope.txt   # 测候选提示词
python3 scripts/calibrate_prompt.py --repeats 3  # 顺带看判定是否稳定
```

输出拒绝精确率、召回率、该拒却收（泄漏）与该收却拒（误杀）的清单。
不稳定比不准确更糟：同一段文本判两次结果不同，说明这条目是判断题，应该落到 review。
