# AI4DB 论文列表的自动收集与 PR 流水线 —— 设计文档

- 日期：2026-10-27
- 仓库：`LumingSun/ML4DB-paper-list`（README 单文件维护，669 条，790 star）
- 状态：已批准（v3：追加存量重复清理 PR，并修正 PR 标题格式）

## 1. 为什么做

仓库最后一次更新是 2026-04-21，至今半年空白。人工维护的问题是：发现论文、判断相关性、核对会议/年份、排出重复，全是手工活，攒一段时间就断更。

2026 年 1–3 月已有一轮自动化尝试（PR #30–#37），失败原因可归纳为三条，本设计逐条对症：

1. **条目信息不全** —— PR #36 只加了标题，没有会议/期刊和年份。
2. **基于旧 master 派生分支** —— #36/#37 的 merge-base 是 2025-12-23，覆盖不到之后的内容；#37 还会把 4 月已手工收录的论文按另一个分类再加一次。
3. **无法校验真伪与重复** —— 上一轮候选来源不可回溯，没法逐条核对论文是否真实存在。

本设计的核心约束：**模型不产生事实，只做判断；不合格的批次不出 PR。**

## 2. 目标与非目标

### 目标
- 每周自动产出一个可直接点 Merge 的 PR，内容是 README 的新增论文条目。
- 每条新增都能回溯到权威元数据（arXiv API 或 Crossref），不存在幻觉论文。
- 每次运行不引入新的重复条目。
- 新增条目格式统一；**除新增行外，不修改任何已有内容**。
- 补上 2026-04-21 到今天的缺口。

### 非目标
- 不收录向量库 / RAG / GraphRAG / 纯知识图谱类论文。
- 不重分类已有条目；不清理存量问题（见下）。
- 不新建顶级章节；v1 只在现有分类内追加（主题聚集时在 PR 描述里建议，由人决定）。
- 不自动合并 PR；不做邮件 / 微信推送，PR 即通知。
- 不依赖 DBLP（被 Anubis 人机验证拦截）、不依赖 Semantic Scholar（无 key 时 429）。
- **不修复存量数据**：README 现有 13 个标题重复（26 行，如 `Learning State Representations for Query Optimization...` 在 539/663 行）、669 条中仅 33 条带链接（且全是 GitHub 源码链接）。这些都只报告、不修改。

## 3. 收录范围

**收**：仓库现有 7 大类的主题，加上 LLM4DB / Agent-for-DB 这类新方向的论文——它们在分类上落到已有小节（例如 D-Bot、GaussMaster 现在就在 `System and Tutorial`，LLM 调参类在 `Configuration Tuning`）。

**不收**：向量检索/向量数据库、RAG、GraphRAG、纯 KG、纯推荐系统；以及"提到数据库但不是 AI×DB 交叉"的论文。

**质量优先级**：CCF A 会议/期刊（VLDB、SIGMOD、ICDE、TKDE、VLDBJ、SIGKDD、ICML、NeurIPS、ICLR、OSDI、AAAI 等）优先；arXiv 只收主题强相关且较新的。arXiv 无同行评审，靠主题相关性和完整性把关。

## 4. 条目格式

```
* {Title} ({Venue} {Year}) [链接]
```

- `Venue` 必须落在受控词表里（`VLDB`、`SIGMOD`、`SIGMOD-Companion`、`ICDE`、`TKDE`、`VLDBJ`、`KDD`、`ICML`、`NeurIPS`、`ICLR`、`AAAI`、`CIDR`、`OSDI`、`ACL`、`EMNLP`、`arXiv`…），由脚本从元数据映射，不由模型生成。
- `Year` 取会议/期刊出版年（Crossref `published-print`，缺则 `published-online`）；arXiv 取提交年。
- 链接：arXiv 用 `[[arXiv]](https://arxiv.org/abs/XXXX.XXXXX)`，期刊/会议用 `[DOI](https://doi.org/...)`。
- **关于链接的取舍（我的决定）**：现有 669 条除 33 条 GitHub 源码链接外都没有 DOI/arXiv 链接，新增条目默认**带**链接，会比邻居多一截。理由是链接是"这篇论文真实存在"的物理凭证，也正好补上"无法逐条校验"这个旧痛点。该行为可配置（`LINK_MODE=always|never`）；设成 `never` 时链接信息写进 PR 描述。旧条目不做一次性补链（需要给 669 条反查 ID，风控成本高，v1 不碰）。
- 插入位置：目标小节列表末尾，空行规则与该小节现有写法一致。

## 5. 流水线

单次运行六个阶段，一个 Python CLI（`python -m ml4db update`），Actions 和本机共用同一份代码。

### 5.1 采集（确定性，不调模型）

**回看窗口（不是水位线）**：每次跑都回看固定窗口——arXiv 120 天、Crossref 180 天。理由：Crossref 对 IEEE/ACM 会议录的索引有延迟（pub-date 是 6 月、11 月才入库），严格水位线会永久漏收；固定回看 + 去重可以容忍延迟，也让"调完词表想重跑同一窗口"成为可能。重复扫到的由 §5.3 去重掉。

- **arXiv**（`export.arxiv.org/api/query`）：
  - `cat:cs.DB`
  - `all:"text-to-sql"` / `all:"nl2sql"`（Text-to-SQL 大量论文在 cs.CL/cs.LG）
  - `all:"database" AND (all:"large language model" OR all:"LLM")`
  - 按 arXiv ID 跨查询去重。
- **Crossref**（`filter=container-title:...,from-pub-date:...`，实测可用、精确过滤不会爆量）：
  - PVLDB（`10.14778`，2026 年至今 310 条）、PACMMOD（2026 年 299 条）、TKDE（2026 年 612 条）、VLDBJ、ICDE（2026 年已入库，DOI 前缀 `10.1109/icde65706.2026.`）。
  - SIGMOD 2026 会议录本身尚不在 Crossref，其论文以 PACMMOD 形式出现，映射为 `SIGMOD`。
  - PVLDB 记录带 abstract，可直接用于判断。
- 每条候选落成结构化记录：`{title, venue_raw, year, arxiv_id|doi, abstract, source, published}`。**后续所有环节只读写这份记录，模型无法改写其中任何字段。**

### 5.2 词法预筛（确定性）

- 必须同时命中"数据库侧"和"AI 侧"词表之一，否则丢弃（词表与阈值在 `config/lexicon.yaml`）。
- 命中排除词表的（vector database、RAG、GraphRAG…）直接丢弃并记录原因。
- 目的：把送模型的候选压到每周百条量级（成本），且让拒绝可审计。实测抽样：cs.DB 近期 25 条里约 10–12 条在范围内。

### 5.3 去重（确定性，先于模型）

按顺序：
1. **外部 ID**：候选的 arXiv ID / DOI 与 README 中已出现的链接、以及**当前开着的自动 PR 分支**里的链接比对。（注意：现有条目几乎没有 ID，这一层主要对"新条目之间"和"未来批次"有效。）
2. **标题精确匹配**：NFKC 归一、小写、去 LaTeX/标点、压缩空白后比对。
3. **模糊匹配**：token-set 相似度 ≥ 92 视为重复（rapidfuzz），命中即跳过并记录被撞的已有条目。宁可漏收，不可重复。
4. 同批内部先去重一次。

### 5.4 模型筛选（唯一的模型环节）

- 输入：`candidate_id + title + abstract（有则给）+ venue/year`，以及**固定枚举的小节清单**（每个小节附定位说明）。
- 输出（严格 JSON，按批 8–12 条）：
  ```json
  {"results":[{"id":"c_017","decision":"accept","section":"## Data Access > ### Configuration Tuning","reason":"..."}]}
  ```
- 允许值只有：`accept` + 一个已存在的小节路径，或 `reject` + 理由。**标题、会议、年份、链接全部来自候选记录，JSON 里根本没有这些字段，模型没有改写渠道。**
- JSON 解析失败 → 整批重试一次 → 仍失败则整批丢弃（fail closed）。
- 模型不可用 / 超时 → 本次运行中止，不产生 PR（fail closed）。
- 接口：OpenAI 兼容（DeepSeek 等），配置 `LLM_BASE_URL` / `LLM_MODEL` / `LLM_API_KEY`；每周十余次短请求。

### 5.5 写入与校验（确定性）

写入：按小节末尾追加，只增不改。校验（不通过则不出 PR）：

1. **四要素正则**（只对新增行）：`^\* .+ \([^()]+ (19|20)\d{2}\) .*\[[^\]]+\]\(https?://.+\)$` —— 标题、venue、年份、链接齐全，直接杀死 PR #36 那类残缺条目。
2. 每条新增的链接能解析到 arXiv ID 或 DOI。
3. **不引入新重复**：每条新增行的归一化标题不得与 README 现有任何行、或本批其他新增行相撞。存量那 13 个重复是历史遗留，祖父条款放过——所以校验是"新增行之间的碰撞 + 新增行对全表的碰撞"，不是"全表无重复"。
4. 与 master 的 diff **只允许新增行**：不允许出现被删除或被修改的已有行，直接杀死 #37 那类"旧基线 + 重分类"。
5. 新增条数 ≥ 1，否则不开 PR。
6. 现有章节标题与 TOC 未被改动。

补充产出（写进 PR 描述，不改文件）：
- **可升级清单**：已作为 `(arXiv 20xx)` 收录、现在有了会议/期刊版本的论文——列出标题 + 新 venue + DOI，由人决定是否手工升级。v1 不改写老行（会违反"只增不改"）。
- **存量重复清单**：那 13 条位置，提示后续可清理。

### 5.6 开 PR

- 每次从**最新 `origin/master`** 拉分支（`auto/update-<YYYY-MM-DD>-<runid>`），不复用旧分支、不 force-push。
- 标题：`[Auto] 新增 AI4DB 论文（<日期>）`（条数写在描述里）；标签 `auto-update`。
- PR 描述固定包含：按小节的新增计数表、漏斗数字（采集 → 预筛后 → 模型接受 → 去重丢弃）、被拒抽样与理由、可升级清单、校验清单。
- **没有状态文件**（这是有意的设计决定）。每次跑都回看固定窗口，靠 README + 开着的自动 PR 去重，所以：
  - PR 挂着未合并 → 下周一发现已有开着的自动 PR，只在该 PR 下评论（补充新候选的摘要），不新开 PR；候选不会因此丢失，因为窗口是重叠的。
  - PR 被人**关闭** → 那些论文下周会再出现。若确实不想要，写进 `.auto/ignore.yaml`（人工维护的压制清单，按标题或 ID）。
  - 这样消除了"水位线随 PR 生命周期漂移"的整类 bug。

## 6. 运行方式

### GitHub Actions（默认）
- `.github/workflows/weekly-update.yml`：`cron: '0 1 * * 1'`（UTC 01:00 = 北京时间周一 09:00），外加 `workflow_dispatch`（入参 `since`、`dry_run`）。
- 权限：`contents: write`、`pull-requests: write`，用内置 `GITHUB_TOKEN`。
- **可行性已实测**：该仓库 Actions 已启用、默认 workflow 权限为 `write`、`can_approve_pull_request_reviews = true`，即 GITHUB_TOKEN 可以直接开 PR（不需要 PAT）；当前仓库还没有任何 workflow，是本设计新增。Runner 出网不受限，arXiv/Crossref 可直连，不需要代理。
- 需要的 Secret：`LLM_API_KEY`（每周十余次短请求，成本可忽略）。**回答你的问题：能，Actions 调大模型 API 就是普通 HTTPS POST，和本机跑没有区别。**

### 本机（备份 / 补课 / 调参）
- 同一 CLI：`LLM_API_KEY=... python -m ml4db update --since 2026-04-21 --dry-run`。
- 需要代理时走 `https_proxy` 环境变量（本机实测：arXiv ✅、Crossref ✅、DBLP 被拦、S2 429）。
- 可选 launchd 定时（文档给 plist 示例），非默认路径。

## 7. 首次补课

- 窗口：2026-04-21 → 运行日。实测该区间 arXiv cs.DB 1058 条、text-to-sql 169 条、PVLDB 310 条，加其他容器合计约两千条候选；预筛后数百，模型接受后估计 80–150 条。
- 交付：**一个补课 PR**（同样只增不改）。若接受数 > ~120 或跨度过大，按月份拆成 2–3 个顺序 PR，每个仍从最新 master 派生。
- 补课跑完后不建立任何水位线，周更照常用固定回看窗口。

### 7.5 存量重复清理（单独 PR）

你要求把现有 13 组同名条目也清掉，做成**独立 PR**，与补课 PR 互不干扰。

- 做法：`cleanup/manifest.json` 逐组声明「删除第 N 行 / 保留第 M 行 / 理由」，程序先校验两行归一化标题相同、再删除，最后由
  `validate_cleanup()` 卡住两条硬约束：**只删不加**、**删后全表无重复**。
- 保留哪一条的原则：优先保留在小节归属更准确的那一条（例：`Speeding Up End-to-end Query Execution…` 在
  `#### Data-based` 下缺年份，保留 `#### Query-based` 下带 `(SIGMOD 2023)` 的那条）；归属相当时保留靠前的一条。
- 这条 PR 的 diff **允许删除**，因此它走的是 `validate_cleanup()` 而不是 `validate_additions()`——两个模式的契约分开，
  补课和自动更新永远不会因为这条 PR 而放松"只增不改"。
- 合并顺序建议：先合清理 PR，再合补课 PR（两者改动的行不相邻，但按此顺序 diff 最干净）。

## 8. 仓库新增物

```
scripts/ml4db/            # 采集、预筛、去重、筛选、写入、校验、CLI
scripts/tests/            # pytest：归一化、去重、插入、校验（含 PR#36 残缺条目回归用例）
config/lexicon.yaml       # 数据库词表、AI 词表、排除词表、小节定位说明、venue 映射表
.auto/ignore.yaml         # 人工压制清单（可选，默认空）
.github/workflows/weekly-update.yml
docs/                     # 本设计文档 + 使用说明
```

README 本身除新增条目（以及一次性清理 PR 的删除）外不做任何改动。
使用说明见 `docs/pipeline.md`。

## 9. 失败模式与对策

| 失败模式 | 对策 |
|---|---|
| 模型幻觉 / 编造论文 | 模型只输出 decision + section，元数据全来自 API 记录 |
| 模型编造小节名 | 小节名必须精确命中枚举，否则该条丢弃 |
| 模型 JSON 不稳定 | 重试一次，仍失败则整批丢弃（不出 PR） |
| 新重复条目 | 三层去重 + 写入后只对新行查碰撞 |
| 基线过期（#37 病） | 每次从最新 master 拉分支；diff 禁止删除/修改已有行 |
| 条目残缺（#36 病） | 四要素正则 + 链接可解析，只对新增行硬卡 |
| 索引延迟导致漏收 | 固定回看窗口（120/180 天），不用水位线 |
| PR 长期不合并 | 检测到开着的自动 PR 就只评论；窗口重叠保证不漏 |
| PR 被关闭后论文反复出现 | `.auto/ignore.yaml` 压制 |
| API 限流/失败 | 本次中止、失败可见；下周重跑，因无状态而无需修复 |
| 补课 PR 过大 | 按月份拆分 |

## 10. 验收标准

- 补课 PR 合并后，README 中 2026 年条目从 15 条增加到预期量级，无新增重复、无幻觉、格式统一。
- 连续两周的自动 PR 可直接 Merge：抽查 10 条全部真实存在、分类合理、格式一致。
- 重跑同一天任务不产生 diff（幂等）。
- 单测覆盖：归一化与去重、格式校验（含 #36 残缺条目用例）、插入不破坏原文件、diff 只有新增、以及"存量 13 条重复不导致校验失败"的祖父条款用例。

## 11. 已由我拍板的决定（请过目）

1. **存量 13 条重复不清理**，校验只看"是否引入新重复"。
2. **新条目默认带 arXiv/DOI 链接**（可用 `LINK_MODE=never` 关掉），旧条目不做一次性补链。
3. **不引入水位线状态文件**，改用固定回看窗口 + 去重；顺带消除"未合并/被关闭 PR 让状态漂移"的整类问题。
4. **关闭的自动 PR 里的论文会重新出现**，不想要就写 `.auto/ignore.yaml`。
5. **已收录预印本见刊**不在 v1 里自动改写，只在 PR 描述里列"可升级"清单。
6. **PACMMOD 映射为 SIGMOD**（SIGMOD 2023 起论文以 PACMMOD 形式出版），词表里可调。

## 12. 留给实现者的细节

- 词表具体词条与 92 这个相似度阈值：先保守，补课时按误杀率微调。
- 补课 PR 是否拆分：按最终接受数决定。
- ICDE/SIGMOD 2026 覆盖率：先跑一次看。
- `.auto/ignore.yaml` 的字段与匹配规则。
