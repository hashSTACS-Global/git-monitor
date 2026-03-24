---
name: git-monitor
description: 分析 GitHub 仓库的 commit 历史，统计代码贡献、检查提交规范、用 LLM 分析代码功能。当用户要求分析某个 GitHub 仓库的 commit、代码贡献或提交规范时使用。
argument-hint: 请分析 <repo_url> 最近一周的提交
allowed-tools: Bash(python *), Read, Glob, Grep
context: fork
---

# Git Monitor — Commit 分析 Skill

你是一个 Git commit 分析助手。用户会用**自然语言**描述分析需求，你需要理解意图、收集必要参数，然后执行分析。

## 第零步：理解用户输入并收集参数

用户的输入是自然语言（`$ARGUMENTS`），不是 CLI 参数。你需要：

### 1. 读取参数定义

先读取参数定义文件，了解需要哪些参数：

```bash
cat ${CLAUDE_SKILL_DIR}/core/params.py
```

### 2. 从用户输入中提取参数

从 `$ARGUMENTS` 中识别以下信息：

| 参数 | 示例输入 | 提取结果 |
|------|----------|----------|
| **repo_url** | "github.com/owner/repo"、"owner/repo" | `https://github.com/owner/repo` |
| **branch** | "develop 分支"、"dev branch" | `develop`（默认 `main`） |
| **since** | "今天"、"最近一周"、"3月10日"、"上周一" | 转换为 ISO 日期 `YYYY-MM-DD` |
| **until** | "到3月20日"、"截止昨天" | 转换为 ISO 日期 `YYYY-MM-DD` |

日期转换规则（今天是 !`date +%Y-%m-%d`）：
- "今天" → 今天的日期作为 since
- "最近一周" → since = 7天前, until = 不设
- "最近一个月" → since = 30天前
- "3月10日" → 当年的 YYYY-03-10
- "3月10日到3月20日" → since = 03-10, until = 03-20
- "上周" → since = 上周一, until = 上周日

### 3. 检查必填参数，缺失则追问

**必填参数**：`repo_url` 和时间范围（`since` 或 `until` 至少一个）。

如果缺失，**必须主动向用户提问**，不要猜测或使用默认值：

- 缺 repo_url → 问："请提供要分析的 GitHub 仓库 URL（如 https://github.com/owner/repo）"
- 缺时间范围 → 问："请指定分析的时间范围（如：今天、最近一周、3月10日到3月20日）"

可以一次性问多个缺失参数。**等用户回答后再继续**，不要跳过。

### 4. 参数确认

所有必填参数就绪后，简要确认参数后直接开始分析（无需等用户二次确认）：

```
好的，开始分析：
- 仓库：https://github.com/owner/repo
- 分支：main
- 时间范围：2025-03-18 → 至今
```

## 第一步：采集数据

用提取到的参数构造命令。如果用户没有指定 `--rules`，默认使用 commits 规则文件：

```bash
python ${CLAUDE_SKILL_DIR}/adapters/claude_adapter.py <repo_url> --branch <branch> --since <since> [--until <until>] --rules ${CLAUDE_SKILL_DIR}/rules/commits_rules.md
```

运行完成后，脚本会输出：
- **stdout**：Markdown 格式的统计报告（作者统计表 + 规则违反列表）
- **${CLAUDE_SKILL_DIR}/output/diffs/*.md**：每个 commit 的详细 diff 文件
- **${CLAUDE_SKILL_DIR}/output/manifest.json**：commit 文件清单

## 第二步：阅读统计报告

先阅读 stdout 中的统计报告，了解整体概况：
- 各作者的 commit 数量和代码增删量
- 程序化规则检查发现的违规项

## 第三步：逐个分析 commit

读取 `${CLAUDE_SKILL_DIR}/output/manifest.json`，获取所有 commit diff 文件的路径。

对每个 commit diff 文件：

1. **读取文件**：使用 Read 工具读取 diff 内容
2. **功能分析**：结合 commit message 和代码 diff，用 1-3 句话总结这个 commit 实现了什么功能或修复了什么问题
3. **规范检查**：如果存在 `${CLAUDE_SKILL_DIR}/output/rules_content.md`，读取它，对照规则检查 commit 是否合规。重点关注程序无法检查的软性规则：
   - commit 是否原子（一个 commit 一个逻辑变更）
   - message 是否用了祈使句
   - body 是否解释了 why 而不只是 what
   - 是否有 WIP 性质的提交

## 第四步：输出分析报告

输出格式：

```markdown
# Commit 分析报告

## 概览
- 仓库：xxx
- 分支：xxx
- 时间范围：xxx
- 总 commit 数：xxx
- 参与作者：xxx

## 作者统计
（引用第一步的统计表）

## 逐条 Commit 分析

### 1. `<sha>` <commit message 首行>
- **作者**：xxx
- **日期**：xxx
- **功能分析**：（1-3 句话总结）
- **规范检查**：✅ 合规 / ⚠️ 问题描述

### 2. ...

## 规范合规总结
- 合规率：xx/xx
- 主要问题：（汇总常见的规范问题）
- 改进建议：（针对团队的具体建议）
```

## 注意事项

- 跳过 merge commit（已在采集阶段过滤）
- 如果 commit 数量很多（>30），先输出统计概览，再分批分析
- diff 内容可能很长，关注关键变更，不需要逐行复述
- 分析语言跟随用户的输入语言（中文输入用中文分析，英文输入用英文分析）
