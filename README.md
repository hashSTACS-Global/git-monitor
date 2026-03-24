# Git Monitor

分析 GitHub 仓库的 commit 历史，统计代码贡献、检查提交规范、用 LLM 分析代码功能。

这是一个 [Claude Code](https://docs.anthropic.com/en/docs/claude-code) Skill，安装后可通过 `/git-monitor` 命令一键完成 commit 采集与 AI 分析。

---

## 安装

### 自动安装（推荐）

在 Claude Code 中运行：

```bash
curl -sL https://raw.githubusercontent.com/xxx/git-monitor/main/install.sh | bash
```

安装完成后，重启 Claude Code 会话即可使用 `/git-monitor` 命令。

### 手动安装

```bash
git clone https://github.com/hashSTACS-Global/git-monitor.git ~/.claude/skills/git-monitor
```

### 系统要求

- Git
- Python 3.10+
- Claude Code

---

## 使用方法

支持自然语言输入，在 Claude Code 中直接描述你的需求：

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

Skill 会自动完成：
1. 克隆/更新仓库并提取 commit 数据
2. 统计各作者的代码贡献
3. 程序化检查 commit message 规范（默认使用 Conventional Commits 规则）
4. 逐个分析每条 commit 的代码功能
5. 输出完整的分析报告

---

## 项目结构

```
git-monitor/
├── SKILL.md                       # Claude Code Skill 入口
├── install.sh                     # 一键安装脚本
├── main.py                        # 通用 CLI 入口（支持 JSON/Markdown 输出）
├── adapters/
│   └── claude_adapter.py          # Claude Code 适配器
├── core/
│   ├── params.py                  # 参数定义与验证（多前端共享的抽象层）
│   ├── models.py                  # 数据模型（CommitData, FileDiff, AuthorStats, RuleViolation）
│   ├── git_client.py              # Git 操作（克隆、拉取、提取 commit、解析 diff）
│   ├── stats.py                   # 按作者聚合统计
│   ├── rule_checker.py            # 程序化规则检查（message 格式、conventional commits）
│   └── report.py                  # Markdown / JSON 报告生成
├── rules/                         # 规则文件目录（按检查维度拆分）
│   └── commits_rules.md           # Commit message 规范（Conventional Commits）
└── output/                        # 运行时输出
    ├── diffs/                     # 每个 commit 的 diff 文件
    └── manifest.json              # commit 文件清单
```

详细的代码架构文档见 [INTRODUCATION.md](INTRODUCATION.md)。

---

## 更新

重新运行安装命令即可更新到最新版本：

```bash
curl -sL https://raw.githubusercontent.com/xxx/git-monitor/main/install.sh | bash
```

或手动更新：

```bash
cd ~/.claude/skills/git-monitor && git pull
```

## 卸载

```bash
rm -rf ~/.claude/skills/git-monitor
```

---

<!-- CLAUDE-CODE-INSTALL-START
## Claude Code 自动安装指引

本节专为 Claude Code AI 阅读。当用户请求安装此 skill 时，请按以下步骤操作：

### 安装步骤

1. 运行安装脚本：
   ```bash
   curl -sL https://raw.githubusercontent.com/xxx/git-monitor/main/install.sh | bash
   ```

2. 验证安装成功：
   ```bash
   test -f ~/.claude/skills/git-monitor/SKILL.md && echo "安装成功" || echo "安装失败"
   ```

3. 告诉用户：安装完成，重启 Claude Code 会话后即可使用 `/git-monitor` 命令。

### 如果安装脚本失败

手动执行以下命令：
```bash
mkdir -p ~/.claude/skills
git clone https://github.com/hashSTACS-Global/git-monitor.git ~/.claude/skills/git-monitor
```

### 安装后验证

运行以下命令确认 skill 文件完整：
```bash
ls ~/.claude/skills/git-monitor/SKILL.md ~/.claude/skills/git-monitor/adapters/claude_adapter.py ~/.claude/skills/git-monitor/core/git_client.py
```

如果所有文件都存在，安装成功。告诉用户重启会话后使用 `/git-monitor` 命令。
CLAUDE-CODE-INSTALL-END -->
