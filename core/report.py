"""Report generation: produce structured output for different consumers."""

import json
from .models import CommitData, AuthorStats, RuleViolation


def generate_json_report(
    commits: list[CommitData],
    author_stats: dict[str, AuthorStats],
    violations: list[RuleViolation],
    repo_url: str,
    branch: str,
    since: str | None,
    until: str | None,
) -> dict:
    """Generate a complete JSON report."""
    return {
        "meta": {
            "repo": repo_url,
            "branch": branch,
            "since": since,
            "until": until,
            "total_commits": len(commits),
            "total_authors": len(author_stats),
        },
        "author_stats": {k: v.to_dict() for k, v in author_stats.items()},
        "violations": [v.to_dict() for v in violations],
        "commits": [c.to_dict() for c in commits],
    }


def generate_markdown_stats(
    author_stats: dict[str, AuthorStats],
    violations: list[RuleViolation],
    repo_url: str,
    branch: str,
    since: str | None,
    until: str | None,
) -> str:
    """Generate a Markdown summary (stats + violations only, no LLM analysis)."""
    lines = [
        f"# Commit Analysis Report",
        f"",
        f"**Repo**: {repo_url}  ",
        f"**Branch**: {branch}  ",
        f"**Period**: {since or 'beginning'} → {until or 'now'}  ",
        f"",
        f"## Author Statistics",
        f"",
        f"| Author | Commits | Additions | Deletions | Net Lines |",
        f"|--------|---------|-----------|-----------|-----------|",
    ]

    for a in sorted(author_stats.values(), key=lambda x: x.commit_count, reverse=True):
        net = a.total_additions - a.total_deletions
        lines.append(
            f"| {a.name} | {a.commit_count} | +{a.total_additions} | -{a.total_deletions} | {net:+d} |"
        )

    lines.append("")

    # Per-author commit details
    lines.append("## Commit Details by Author")
    lines.append("")

    for a in sorted(author_stats.values(), key=lambda x: x.commit_count, reverse=True):
        lines.append(f"### {a.name} ({a.commit_count} commits)")
        lines.append("")
        for c in a.commits:
            merge_tag = " [MERGE]" if c.get("is_merge") else ""
            lines.append(
                f"- `{c['sha']}` {c['message']}{merge_tag} (+{c['additions']}/-{c['deletions']}, {c['files_changed']} files)"
            )
        lines.append("")

    # Violations
    if violations:
        lines.append("## Rule Violations")
        lines.append("")
        for v in violations:
            icon = "❌" if v.severity == "error" else "⚠️"
            lines.append(f"- {icon} `{v.commit_sha}` **{v.rule_name}**: {v.message}")
        lines.append("")

    return "\n".join(lines)
