# Git Monitor

分析 GitHub 仓库的 commit 历史，统计代码贡献、检查提交规范、输出结构化数据供 LLM 分析代码功能。

本项目是一个 Claude Code Skill，安装后可通过 `/git-monitor` 命令以自然语言驱动完整的 commit 分析流程。

---

## 目录

- [整体架构](#整体架构)
- [项目结构](#项目结构)
- [核心模块详解](#核心模块详解)
  - [core/params.py — 参数定义与验证（多前端抽象层）](#coreparamspy--参数定义与验证多前端抽象层)
  - [core/models.py — 数据模型](#coremodelspy--数据模型)
  - [core/git_client.py — Git 操作层](#coregit_clientpy--git-操作层)
  - [core/stats.py — 统计聚合](#corestatspy--统计聚合)
  - [core/rule_checker.py — 规则检查引擎](#corerule_checkerpy--规则检查引擎)
  - [core/report.py — 报告生成](#corereportpy--报告生成)
- [交互层与适配器层](#交互层与适配器层)
  - [SKILL.md — Claude Code 交互层](#skillmd--claude-code-交互层)
  - [adapters/claude_adapter.py — 数据采集执行器](#adaptersclaude_adapterpy--数据采集执行器)
  - [main.py — 通用 CLI 入口](#mainpy--通用-cli-入口)
- [运行流程](#运行流程)
- [设计决策与权衡](#设计决策与权衡)
- [当前局限与扩展方向](#当前局限与扩展方向)
- [使用方法](#使用方法)

---

## 整体架构

Git Monitor 采用**三层架构**：

```
┌──────────────────────────────────────────────────────────────┐
│                    交互层 (Interaction)                        │
│                                                               │
│  SKILL.md              (未来: Web UI)      (未来: 飞书 Bot)    │
│  Claude 解析自然语言     表单收集参数         消息收集参数        │
│  追问缺失参数            渲染参数表单         发消息追问          │
└──────────────┬───────────────┬───────────────┬───────────────┘
               │               │               │
               ▼               ▼               ▼
┌──────────────────────────────────────────────────────────────┐
│                 参数抽象层 (core/params.py)                     │
│                                                               │
│  AnalysisParams: 参数定义 + 验证 + 提示语                       │
│  missing_required(): 返回缺失必填项 + 人类可读的追问提示          │
│  to_cli_args(): 转换为 CLI 参数                                │
│                                                               │
│  ► 所有前端共享这一层，保证参数定义和验证逻辑一致                   │
└──────────────────────────┬───────────────────────────────────┘
                           │ 参数就绪后调用
┌──────────────────────────▼───────────────────────────────────┐
│                    执行层 (Execution)                          │
│                                                               │
│  adapters/              core/                                 │
│  claude_adapter.py      git_client.py   stats.py              │
│  main.py                rule_checker.py report.py             │
│                         models.py                             │
└──────────────────────────────────────────────────────────────┘
```

**核心原则**：

- **交互层**负责用户沟通（理解自然语言、追问缺失参数），不同前端各自实现
- **参数抽象层**（`core/params.py`）定义"需要什么参数、怎么验证、缺了怎么提示"，所有前端共享
- **执行层**（`core/` + `adapters/`）不关心参数从哪来，只接收结构化参数并执行分析

---

## 项目结构

```
git-monitor/
├── SKILL.md                       # Claude Code Skill 入口（自然语言交互 + 分析流程）
├── install.sh                     # 一键安装脚本
├── main.py                        # 通用 CLI 入口（支持 JSON/Markdown/文件输出）
├── adapters/
│   ├── __init__.py
│   └── claude_adapter.py          # 数据采集执行器（输出统计 + diff 文件）
├── core/
│   ├── __init__.py
│   ├── params.py                  # 参数定义、验证、提示语（所有前端共享的抽象层）
│   ├── models.py                  # 四个数据类：FileDiff, CommitData, AuthorStats, RuleViolation
│   ├── git_client.py              # Git 操作：克隆、拉取、提取 commit、解析 diff
│   ├── stats.py                   # 按作者聚合 commit 统计
│   ├── rule_checker.py            # 程序化规则检查（格式、长度、conventional commits）
│   └── report.py                  # Markdown / JSON 报告生成
├── rules/                         # 规则文件目录（按检查维度拆分）
│   └── commits_rules.md           # Commit message 规范（未来扩展：代码规范、提交模式等）
├── output/                        # 运行时输出目录
│   ├── diffs/                     # 每个 commit 的 diff 文件（*.md）
│   ├── manifest.json              # commit 文件清单
│   └── rules_content.md           # 规则文件副本（供 LLM 阶段使用）
├── CLAUDE.md                      # Claude Code 项目指令
├── README.md                      # 安装说明 + 使用方法
└── INTRODUCATION.md               # 本文件：详细代码架构文档
```

---

## 核心模块详解

### core/params.py — 参数定义与验证（多前端抽象层）

这是所有前端（Claude Code、Web UI、飞书等）共享的参数定义层。定义了分析任务需要哪些参数、哪些必填、缺失时如何提示用户。

**`AnalysisParams` 数据类**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `repo_url` | str | 是 | GitHub 仓库 URL |
| `branch` | str | 否 | 分支名，默认 `main` |
| `since` | str | 是（至少一个） | 开始日期（ISO 格式） |
| `until` | str | 是（至少一个） | 结束日期（ISO 格式） |
| `rules` | str | 否 | 规则文件路径 |
| `max_diff_lines` | int | 否 | 每个 commit 的 diff 行数上限，默认 5000 |
| `clone_dir` | str | 否 | 自定义仓库克隆目录 |

**关键方法**：

- `missing_required()` → 返回缺失的必填参数列表，每项包含 `field`（字段名）和 `prompt`（人类可读的提示语）。所有前端用这个方法驱动参数收集的交互循环。
- `to_cli_args()` → 将参数转换为 CLI 参数列表，供 `claude_adapter.py` 使用。
- `to_cli_string()` → 将参数转换为完整的 CLI 参数字符串。

**`FIELD_INFO` 元数据**：

每个字段附带 `required`、`prompt`、`description`、`default` 等元信息，前端可用于：
- Claude Code：读取 prompt 来追问用户
- Web UI：读取 description 和 required 来渲染表单
- 飞书 Bot：读取 prompt 来发送追问消息

**各前端如何使用**：

| 前端 | 交互方式 | 使用 params.py 的方法 |
|------|----------|----------------------|
| Claude Code（SKILL.md） | Claude 从自然语言提取参数 | 读取 params.py 了解需要什么，用 `missing_required()` 的 prompt 追问缺失项 |
| Web UI | 表单输入 | 读取 `FIELD_INFO` 渲染表单字段，提交后调用 `missing_required()` 校验 |
| 飞书 Bot | 对话消息 | 收到消息后用 LLM 提取参数，用 `missing_required()` 的 prompt 发消息追问 |

---

### core/models.py — 数据模型

定义了整个分析管线的四个数据类，所有模块围绕这些模型通信：

| 数据类 | 职责 | 关键字段 |
|--------|------|----------|
| `FileDiff` | 单个文件的变更 | `filename`, `status`(added/modified/deleted/renamed), `additions`, `deletions`, `patch` |
| `CommitData` | 一次 commit 的完整信息 | `sha`, `author_*`, `date`, `message`, `files: list[FileDiff]`, `is_merge` |
| `AuthorStats` | 按作者聚合的统计 | `commit_count`, `total_additions/deletions`, `commits`(每条 commit 的摘要) |
| `RuleViolation` | 一条规则违反记录 | `rule_name`, `severity`(error/warning/info), `message`, `commit_sha` |

所有模型都实现了 `to_dict()` 方法，用于 JSON 序列化。

---

### core/git_client.py — Git 操作层

封装了所有 Git 命令调用，是系统的数据源头。

**函数调用链**：

```
ensure_repo()           克隆或 fetch 仓库到 ~/.cache/git-monitor/repos/{owner}__{repo}/
    ↓
get_commits()           git log 提取 commit 基础信息（sha, author, date, subject, is_merge）
    ↓
enrich_commits()        遍历每个 commit，补全详细信息：
    ├→ get_commit_full_message()    git log -1 --format=%B → 完整 message（含 body）
    └→ get_commit_diff()            git show --numstat + --patch → FileDiff 列表
         └→ _parse_diff()           逐行解析 unified diff，拆分为 per-file 补丁
              └→ _finalize_file()   从 diff header 推断文件状态（added/deleted/renamed/modified）
```

**关键设计**：

- **`_run_git()`**：统一的 git 命令执行器，120 秒超时，失败时抛出 `RuntimeError`
- **`ensure_repo()`**：幂等操作——已存在则 `fetch --all --prune`，不存在则 `clone --no-checkout`（不展开工作树，节省空间）
- **`enrich_commits()`** 是**同步串行**的：逐个 commit 调用 `git show`，对于大仓库（数百个 commit）可能较慢（见[当前局限](#当前局限与扩展方向)）
- **Diff 行数限制**：`max_diff_lines` 参数（默认 5000）防止二进制文件或生成文件撑爆内存

---

### core/stats.py — 统计聚合

只有一个函数 `stats_by_author()`，将 commit 列表按 `author_email` 分组，汇总：

- 每位作者的 commit 总数、代码增删总量
- 每条 commit 的摘要（sha、日期、message 截断至 120 字符、增删行数、文件数、是否 merge）

返回 `dict[email → AuthorStats]`。

---

### core/rule_checker.py — 规则检查引擎

**设计理念**：将规则检查分为两类——

1. **程序化检查**（本模块负责）：能用正则/条件判断的硬性规则
2. **LLM 检查**（留给后续阶段）：需要语义理解的软性规则（如"是否原子提交"、"是否解释了 why"）

**当前执行流程**：

```python
check_all(commits, rules_md_path)
    │
    ├→ 读取 rules 文件内容（如果提供）
    │
    └→ 遍历每个非 merge commit：
         ├→ _check_message_basics(commit)
         │   ├→ subject < 5 字符 → warning: message_too_short
         │   └→ subject > 120 字符 → warning: message_too_long
         │
         └→ _check_conventional_commit(commit)  ← 仅当 rules 文件中包含 "conventional" 时触发
             └→ 正则匹配: ^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\(.+\))?!?:\s.+
                 不匹配 → error: conventional_commit_format
```

**当前特点与局限**：

- **同步串行执行**：当前按顺序遍历 commit 列表，没有多线程或并发机制。对于几十到几百个 commit 的场景，规则检查本身的计算开销极小（纯字符串/正则操作），串行足够快
- **条件触发**：conventional commit 检查不是默认启用的，只有当 rules 文件内容中出现 "conventional" 关键词时才激活
- **merge commit 过滤**：自动跳过合并提交（合并提交的 message 通常是自动生成的，检查没有意义）
- **输出双通道**：返回 `(violations, rules_content)` 元组——violations 用于程序化报告，rules_content 原文传递给 LLM 做主观分析

---

### core/report.py — 报告生成

提供两种输出格式：

| 函数 | 输出格式 | 内容 |
|------|----------|------|
| `generate_markdown_stats()` | Markdown | 作者统计表格 + 每人 commit 明细 + 违规列表（❌/⚠️ 图标） |
| `generate_json_report()` | JSON dict | 完整结构化数据：meta、author_stats、violations、commits |

报告模块**不包含 diff 内容**（diff 太大），只包含统计和违规信息。diff 的输出由适配器层决定如何处理。

---

## 交互层与适配器层

### SKILL.md — Claude Code 交互层

SKILL.md 是 Claude Code 的 Skill 入口文件，定义了 Claude 在 `/git-monitor` 命令被触发时应遵循的完整流程。它不是 Python 代码，而是一份给 Claude 的**行为指令**。

**交互流程**：

```
用户输入自然语言
  "请分析 github.com/owner/repo 最近一周的提交"
    │
    ▼
Claude 读取 core/params.py，了解需要哪些参数
    │
    ▼
Claude 从自然语言中提取参数：
  repo_url = "https://github.com/owner/repo"
  since = 7 天前（转换为 YYYY-MM-DD）
    │
    ▼
检查 missing_required()
  ├→ 有缺失 → 用 prompt 追问用户 → 等待回答 → 再次检查
  └→ 全部就绪 → 确认参数并开始分析
    │
    ▼
构造 CLI 命令，调用 claude_adapter.py
    │
    ▼
读取 output/ 目录，逐个分析 commit diff
    │
    ▼
输出完整分析报告
```

**自然语言日期解析**（由 Claude 在运行时完成）：

| 用户说 | 解析为 |
|--------|--------|
| "今天" | since = 当天日期 |
| "最近一周" | since = 7 天前 |
| "最近一个月" | since = 30 天前 |
| "3月10日" | since = 当年 YYYY-03-10 |
| "3月10日到3月20日" | since = 03-10, until = 03-20 |

**关键设计**：SKILL.md 中使用 `${CLAUDE_SKILL_DIR}` 引用所有文件路径，不含硬编码路径，确保安装到任何位置都能工作。

---

### adapters/claude_adapter.py — 数据采集执行器

接收 CLI 参数，执行数据采集和统计，输出结果。它**不负责交互**（交互由 SKILL.md 驱动），只做执行。

采用**两阶段输出策略**，为 LLM 的上下文窗口优化：

| 阶段 | 输出位置 | 内容 | 设计原因 |
|------|----------|------|----------|
| Phase 1 | stdout（Claude 直接读取） | Markdown 统计 + 违规列表 | 紧凑，始终在上下文内 |
| Phase 2 | `output/diffs/*.md` 文件 | 每个 commit 的完整 diff | Claude 按需读取，避免一次性撑爆上下文 |

**`write_commit_diffs()` 函数**：
- 为每个非 merge commit 生成 `{short_sha}_{author}.md` 文件
- 包含：commit 元数据、完整 message、每个文件的 diff 补丁
- 运行前先清空旧文件（幂等）
- 返回 manifest 列表，写入 `manifest.json` 供 Claude 知道该读哪些文件

### main.py — 通用 CLI 入口

面向通用场景的命令行入口，相比 claude_adapter 提供更灵活的选项：

| 选项 | 说明 |
|------|------|
| `--format json\|markdown` | 选择输出格式（默认 markdown） |
| `--output FILE` | 输出到文件而非 stdout |
| `--no-diff` | 跳过 diff 采集，只做统计（快速模式） |
| `--max-diff-lines N` | 每个 commit 的 diff 行数上限（默认 5000） |

---

## 运行流程

完整的数据流从用户自然语言输入到最终分析报告：

```
用户自然语言输入
  "请分析 github.com/owner/repo 最近一周的提交"
   │
   ▼
┌──────────────────────────────────────────┐
│ 0. 参数收集（交互层 — SKILL.md）           │
│    Claude 从自然语言提取参数                │
│    参考 core/params.py 的参数定义           │
│    缺失必填项 → 追问用户                    │
│    → AnalysisParams (repo_url, since, ...) │
└──────────────┬───────────────────────────┘
               │ 参数就绪，构造 CLI 命令
               ▼
┌──────────────────────────────────────────┐
│ 1. git_client.ensure_repo()              │
│    克隆或更新仓库到本地缓存                  │
│    ~/.cache/git-monitor/repos/           │
└──────────────┬───────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│ 2. git_client.get_commits()              │
│    git log 提取 commit 基础元数据            │
│    → CommitData[] (无 diff)               │
└──────────────┬───────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│ 3. git_client.enrich_commits()           │
│    逐个 commit 补全：                      │
│    ├ get_commit_full_message()            │
│    └ get_commit_diff() → _parse_diff()   │
│    → CommitData[] (含完整 message + diff)  │
└──────────────┬───────────────────────────┘
               │
        ┌──────┴──────┐
        ▼             ▼
┌─────────────┐ ┌──────────────┐
│ 4a. stats   │ │ 4b. rule     │
│ _by_author()│ │ _checker     │
│ 按作者聚合   │ │ .check_all() │
│ → AuthorStat│ │ → Violations │
└──────┬──────┘ └──────┬───────┘
       │               │
       └───────┬───────┘
               ▼
┌──────────────────────────────────────────┐
│ 5. 输出（由适配器决定）                      │
│                                          │
│ claude_adapter:                          │
│   stdout → Markdown 统计                  │
│   files  → output/diffs/*.md             │
│   files  → output/manifest.json          │
│                                          │
│ main.py:                                 │
│   stdout/file → Markdown 或 JSON 报告     │
└──────────────────────────────────────────┘
               │
               ▼
┌──────────────────────────────────────────┐
│ 6. LLM 分析（交互层 — SKILL.md）           │
│    Claude 读取 manifest.json              │
│    逐个读取 diffs/*.md 分析代码功能          │
│    对照 rules_content.md 检查软性规则       │
│    输出完整分析报告                          │
└──────────────────────────────────────────┘
```

---

## 设计决策与权衡

### 为什么交互逻辑不写在 Python 里？

在 Claude Code 中，交互（自然语言理解、追问用户）由 Claude 本身完成，不需要 Python 代码。SKILL.md 是给 Claude 的行为指令，Claude 就是"交互引擎"。但参数的定义和验证逻辑（需要什么、缺了什么、提示语是什么）写在 `core/params.py` 中，确保所有前端共享同一套规则。

### 为什么 core 和 adapter 分离？

`core/` 完全不知道输出目的地是谁。它只生产数据结构和格式化文本。这样新增前端时，只需要写一个新的 adapter 来消费 core 的输出，不需要改动核心逻辑。

### 为什么 rule_checker 不做所有规则检查？

团队规范中很多规则本质上是"主观"的（如"commit 是否原子""message 是否解释了 why"），这些无法用正则或条件判断，必须由 LLM 理解代码语义后判断。因此 rule_checker 只负责能程序化验证的硬性规则，软性规则的原文通过 `rules_content` 传递给 LLM 阶段。

### 为什么 diff 写入单独文件而非全部输出到 stdout？

一个中等规模仓库一周的 diff 可能有几万到几十万行。全部塞进 stdout 会超出 LLM 的上下文窗口。按 commit 拆分成独立文件后，LLM 可以按需读取，先看 manifest 和统计决定优先分析哪些 commit。

### 为什么 enrich_commits 是同步串行的？

当前版本优先保证正确性和代码简洁。串行调用 `git show` 对于几十个 commit 通常在几秒内完成。瓶颈在网络（clone/fetch）而非本地 git 命令。

---

## 当前局限与扩展方向

### 性能

| 现状 | 可改进方向 |
|------|-----------|
| `enrich_commits()` 同步串行，逐个调用 `git show` | 可用 `concurrent.futures.ThreadPoolExecutor` 并行获取 diff，git 本地操作是 IO 密集型，适合多线程 |
| `rule_checker.check_all()` 同步遍历 | 规则检查是纯 CPU 计算且开销极小，当前无需并发；若未来加入 LLM 调用类的规则检查，可考虑异步 |

### 多前端适配

| 现状 | 可改进方向 |
|------|-----------|
| `core/params.py` 已实现参数定义和验证的共享抽象层 | ✅ 已完成 |
| `SKILL.md` 实现了 Claude Code 的自然语言交互 | ✅ 已完成 |
| `claude_adapter.py` 是唯一的数据采集执行器 | 可定义 `BaseAdapter` 抽象基类，规范执行器接口 |
| 无 Web UI 或飞书适配器 | 可基于 `params.py` 快速实现新前端 |

**潜在的新适配器**：
- `rest_adapter.py` — REST API 服务，前端用 `FIELD_INFO` 渲染表单，后端用 `missing_required()` 校验
- `feishu_adapter.py` — 飞书机器人，用 LLM 从消息中提取参数，用 `missing_required()` 追问
- `github_action_adapter.py` — CI 集成，在 PR 上自动评论分析结果

### 多 LLM 支持

| 现状 | 可改进方向 |
|------|-----------|
| LLM 分析由 Claude 在 SKILL.md 中直接完成 | 可加入 `core/llm_analyzer.py` 模块，封装 LLM 调用逻辑 |
| 无 LLM provider 抽象 | 可定义统一接口，支持 Claude / GPT / 本地模型等多个 provider |

```python
# 未来可能的 LLM 分析层（尚未实现）
class LLMAnalyzer(ABC):
    @abstractmethod
    def analyze_commit(self, commit: CommitData, rules: str) -> str: ...

class ClaudeAnalyzer(LLMAnalyzer): ...
class OpenAIAnalyzer(LLMAnalyzer): ...
```

### 规则检查扩展

| 现状 | 可改进方向 |
|------|-----------|
| 只有 `commits_rules.md` 一种规则文件 | 按维度扩展：代码规范规则、GitHub 提交模式规则等 |
| 只有 2 类硬编码检查（message 长度 + conventional commits） | 可改为插件式架构，每个检查是独立的 `RulePlugin` |
| conventional commits 检查通过 rules 文件中的关键词触发 | 可改为显式配置，如 rules 文件 frontmatter 中声明启用的检查项 |

---

## 使用方法

### 方式一：Claude Code Skill（推荐）

支持自然语言输入：

```
/git-monitor 请分析 github.com/owner/repo 最近一周的提交
/git-monitor 分析 github.com/owner/repo 今天的提交
/git-monitor 分析 github.com/owner/repo 从3月10日到3月20日的提交
/git-monitor 分析 github.com/owner/repo 的 develop 分支最近一个月的提交
```

如果没有说明仓库或时间范围，Skill 会主动询问：

```
/git-monitor 分析最近的提交

→ Skill: 请提供要分析的 GitHub 仓库 URL（如 https://github.com/owner/repo）
← 用户: github.com/owner/repo
→ Skill: 请指定分析的时间范围（如：今天、最近一周、3月10日到3月20日）
← 用户: 最近一周
→ Skill: 好的，开始分析...
```

安装方法见 [README.md](README.md)。

### 方式二：手动调用适配器

```bash
cd /path/to/git-monitor
python adapters/claude_adapter.py https://github.com/owner/repo \
    --branch main \
    --since 2025-03-01 \
    --until 2025-03-24 \
    --rules rules/commits_rules.md

# 然后在 Claude Code 中阅读 output/diffs/ 下的文件进行 LLM 分析
```

### 方式三：通用 CLI

```bash
# Markdown 报告
python main.py https://github.com/owner/repo --branch main --since 2025-03-01

# JSON 报告输出到文件
python main.py https://github.com/owner/repo --branch main --format json -o report.json

# 快速统计（跳过 diff 采集）
python main.py https://github.com/owner/repo --branch main --no-diff
```

### 命令行参数（方式二、三）

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `repo_url` | GitHub 仓库 URL（必填） | - |
| `--branch` | 分析的分支 | `main` |
| `--since` | 开始日期（ISO 格式） | 不限 |
| `--until` | 结束日期（ISO 格式） | 不限 |
| `--rules` | 团队规则文件路径 | 无 |
| `--format` | 输出格式 json/markdown（仅 main.py） | `markdown` |
| `--output` | 输出文件路径（仅 main.py） | stdout |
| `--no-diff` | 跳过 diff 采集（仅 main.py） | false |
| `--clone-dir` | 自定义仓库克隆目录 | `~/.cache/git-monitor/repos/` |
| `--max-diff-lines` | 每个 commit 的 diff 行数上限 | `5000` |
