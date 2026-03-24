"""Analysis parameters: definition, validation, and prompts.

This module is the single source of truth for what parameters are needed
to run an analysis. All frontends (Claude Code, Web UI, Feishu, etc.)
reference this module to know what to collect from users.
"""

from dataclasses import dataclass, field


@dataclass
class AnalysisParams:
    """Parameters for a commit analysis session."""

    repo_url: str | None = None
    branch: str = "main"
    since: str | None = None
    until: str | None = None
    rules: str | None = None
    max_diff_lines: int = 5000
    clone_dir: str | None = None

    # Metadata for frontends
    FIELD_INFO: dict = field(default_factory=lambda: {}, init=False, repr=False)

    def __post_init__(self):
        self.FIELD_INFO = {
            "repo_url": {
                "required": True,
                "prompt": "请提供要分析的 GitHub 仓库 URL（如 https://github.com/owner/repo）",
                "description": "GitHub 仓库地址",
            },
            "time_range": {
                "required": True,
                "prompt": "请指定分析的时间范围（如：今天、最近一周、3月10日到3月20日）",
                "description": "分析的时间范围（since 和 until）",
            },
            "branch": {
                "required": False,
                "prompt": "请指定要分析的分支名称",
                "description": "分支名（默认 main）",
                "default": "main",
            },
            "rules": {
                "required": False,
                "prompt": "请提供规则文件路径（留空使用默认 Conventional Commits 规则）",
                "description": "团队规范文件路径",
            },
        }

    def missing_required(self) -> list[dict]:
        """Return missing required fields with user-facing prompts.

        Returns a list of dicts, each with:
          - field: the parameter name
          - prompt: a human-readable question to ask the user

        All frontends use this to drive their interaction loop:
          - Claude Code SKILL.md: Claude reads this and asks the user
          - Web UI: renders missing fields as required form inputs
          - Feishu bot: sends the prompt as a chat message
        """
        missing = []

        if not self.repo_url:
            missing.append({
                "field": "repo_url",
                "prompt": self.FIELD_INFO["repo_url"]["prompt"],
            })

        if not self.since and not self.until:
            missing.append({
                "field": "time_range",
                "prompt": self.FIELD_INFO["time_range"]["prompt"],
            })

        return missing

    def to_cli_args(self) -> list[str]:
        """Convert to CLI argument list for claude_adapter.py."""
        if not self.repo_url:
            raise ValueError("repo_url is required")

        args = [self.repo_url]

        if self.branch and self.branch != "main":
            args.extend(["--branch", self.branch])

        if self.since:
            args.extend(["--since", self.since])

        if self.until:
            args.extend(["--until", self.until])

        if self.rules:
            args.extend(["--rules", self.rules])

        if self.max_diff_lines != 5000:
            args.extend(["--max-diff-lines", str(self.max_diff_lines)])

        if self.clone_dir:
            args.extend(["--clone-dir", self.clone_dir])

        return args

    def to_cli_string(self) -> str:
        """Convert to a single CLI argument string."""
        return " ".join(self.to_cli_args())
