#!/usr/bin/env python3
"""
Adapter for running inside Claude Code.

Outputs structured data that Claude can directly read and analyze:
1. Markdown stats report (printed to stdout)
2. Per-commit diffs written to output/ directory for Claude to read individually

This two-step approach works well with Claude's context:
- Stats + violations are compact, always included
- Diffs are written to files, Claude reads them selectively for deep analysis
"""

import argparse
import json
import sys
from pathlib import Path

# Ensure project root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.git_client import ensure_repo, get_commits, enrich_commits
from core.stats import stats_by_author
from core.rule_checker import check_all
from core.report import generate_markdown_stats


OUTPUT_DIR = Path(__file__).parent.parent / "output"


def write_commit_diffs(commits, output_dir: Path):
    """Write each commit's diff to a separate file for Claude to read."""
    diff_dir = output_dir / "diffs"
    diff_dir.mkdir(parents=True, exist_ok=True)

    # Clean old files
    for f in diff_dir.glob("*.md"):
        f.unlink()

    manifest = []
    for c in commits:
        if c.is_merge or not c.files:
            continue

        filename = f"{c.short_sha}_{c.author_name.replace(' ', '_')}.md"
        filepath = diff_dir / filename

        content = [
            f"# Commit {c.short_sha}",
            f"**Author**: {c.author_name} <{c.author_email}>",
            f"**Date**: {c.date.isoformat()}",
            f"**Message**:",
            f"```",
            c.message,
            f"```",
            f"**Stats**: +{c.total_additions}/-{c.total_deletions}, {len(c.files)} files",
            f"",
            f"## Changed Files",
        ]

        for f in c.files:
            content.append(f"\n### {f.filename} ({f.status}, +{f.additions}/-{f.deletions})")
            content.append(f"```diff")
            content.append(f.patch)
            content.append(f"```")

        filepath.write_text("\n".join(content), encoding="utf-8")
        manifest.append({
            "sha": c.short_sha,
            "author": c.author_name,
            "message": c.message.split("\n")[0][:100],
            "file": str(filepath),
        })

    return manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("repo_url")
    parser.add_argument("--branch", default="main")
    parser.add_argument("--since")
    parser.add_argument("--until")
    parser.add_argument("--rules")
    parser.add_argument("--clone-dir")
    parser.add_argument("--max-diff-lines", type=int, default=5000)
    args = parser.parse_args()

    output_dir = OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    # Fetch
    print(f"Fetching repo: {args.repo_url}", file=sys.stderr)
    repo_path = ensure_repo(args.repo_url, args.clone_dir)

    # Commits
    print(f"Getting commits on {args.branch}...", file=sys.stderr)
    commits = get_commits(repo_path, args.branch, args.since, args.until)
    print(f"Found {len(commits)} commits", file=sys.stderr)

    if not commits:
        print("No commits found.")
        return

    # Enrich
    print("Fetching diffs...", file=sys.stderr)
    enrich_commits(repo_path, commits, True, args.max_diff_lines)

    # Stats
    author_stats = stats_by_author(commits)
    violations, rules_content = check_all(commits, args.rules)

    # Output stats as markdown (compact, goes to stdout for Claude)
    stats_md = generate_markdown_stats(
        author_stats, violations,
        args.repo_url, args.branch, args.since, args.until,
    )

    # Write diffs to files
    manifest = write_commit_diffs(commits, output_dir)

    # Write manifest for Claude to know which files to read
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2))

    # Write rules content if provided
    rules_info = ""
    if rules_content:
        rules_path = output_dir / "rules_content.md"
        rules_path.write_text(rules_content, encoding="utf-8")
        rules_info = f"\nTeam rules saved to: {rules_path}"

    # Print the summary for Claude to read
    print(stats_md)
    print()
    print("---")
    print(f"Commit diffs written to: {output_dir}/diffs/")
    print(f"Manifest: {manifest_path}")
    if rules_info:
        print(rules_info)
    print(f"\nTotal: {len(manifest)} non-merge commits with diffs available for analysis.")


if __name__ == "__main__":
    main()
