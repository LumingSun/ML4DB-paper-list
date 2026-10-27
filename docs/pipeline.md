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
