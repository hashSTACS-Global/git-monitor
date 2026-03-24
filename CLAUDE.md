# Git Monitor

分析 GitHub 仓库的 commit 历史，统计代码贡献、检查提交规范、用 LLM 分析代码功能。

## 使用方法

### 第一步：采集数据

```bash
cd /Users/ken/Codes/git-monitor
python adapters/claude_adapter.py <repo_url> --branch <branch> --since <date> --until <date> [--rules rules/commits_rules.md]
```

这会输出：
- 统计报告（stdout，直接阅读）
- 每个 commit 的 diff 文件（写入 `output/diffs/` 目录）
- manifest.json（commit 文件清单）

### 第二步：LLM 分析

数据采集完成后，阅读 `output/diffs/` 下的文件，对每个 commit：
1. 结合 message 和代码 diff 分析实现了什么功能
2. 对照规则文件（如有）检查是否符合团队规范
3. 输出分析报告

### 第三步（可选）：规则检查

如果提供了 `--rules` 参数，规则文件会保存到 `output/rules_content.md`。
程序化检查结果会在统计报告中展示，主观/软性规则需要 LLM 判断。

## 项目结构

- `core/` - 核心库（git 操作、统计、规则检查），前端无关
- `adapters/` - 前端适配器（当前：Claude Code；未来：REST API、飞书等）
- `rules/` - 团队规则模板
- `output/` - 分析输出目录
- `main.py` - CLI 入口
