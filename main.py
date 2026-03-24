#!/usr/bin/env python3
"""
GitHub Code Analysis - Main entry point.

Usage:
    python main.py <repo_url> --branch <branch> --since <date> --until <date> [--rules <rules.md>] [--format json|markdown]

Examples:
    python main.py https://github.com/owner/repo --branch main --since 2025-03-01 --until 2025-03-24
    python main.py https://github.com/owner/repo --branch develop --since 2025-03-01 --rules rules/team_rules.md
"""

import argparse
import json
import sys
from pathlib import Path

from core.git_client import ensure_repo, get_commits, enrich_commits
from core.stats import stats_by_author
from core.rule_checker import check_all
from core.report import generate_json_report, generate_markdown_stats


def main():
    parser = argparse.ArgumentParser(description="Analyze GitHub repo commits")
    parser.add_argument("repo_url", help="GitHub repo URL")
    parser.add_argument("--branch", default="main", help="Branch to analyze (default: main)")
    parser.add_argument("--since", help="Start date (ISO format, e.g., 2025-03-01)")
    parser.add_argument("--until", help="End date (ISO format, e.g., 2025-03-24)")
    parser.add_argument("--rules", help="Path to team rules markdown file")
    parser.add_argument("--format", choices=["json", "markdown"], default="markdown", help="Output format")
    parser.add_argument("--clone-dir", help="Directory for cloning repos")
    parser.add_argument("--no-diff", action="store_true", help="Skip fetching diffs (faster, stats only)")
    parser.add_argument("--max-diff-lines", type=int, default=5000, help="Max diff lines per commit")
    parser.add_argument("--output", "-o", help="Output file path (default: stdout)")

    args = parser.parse_args()

    # Step 1: Clone / fetch repo
    print(f"[1/4] Fetching repo: {args.repo_url}", file=sys.stderr)
    repo_path = ensure_repo(args.repo_url, args.clone_dir)

    # Step 2: Get commits
    print(f"[2/4] Getting commits on {args.branch} ({args.since} → {args.until})", file=sys.stderr)
    commits = get_commits(repo_path, args.branch, args.since, args.until)
    print(f"       Found {len(commits)} commits", file=sys.stderr)

    if not commits:
        print("No commits found in the specified range.", file=sys.stderr)
        sys.exit(0)

    # Step 3: Enrich with diffs
    include_diffs = not args.no_diff
    print(f"[3/4] Enriching commits (diffs={'yes' if include_diffs else 'no'})...", file=sys.stderr)
    enrich_commits(repo_path, commits, include_diffs, args.max_diff_lines)

    # Step 4: Stats + rule checking
    print("[4/4] Computing stats and checking rules...", file=sys.stderr)
    author_stats = stats_by_author(commits)
    violations, rules_content = check_all(commits, args.rules)

    # Generate output
    if args.format == "json":
        report = generate_json_report(
            commits, author_stats, violations,
            args.repo_url, args.branch, args.since, args.until,
        )
        # Include rules content for LLM phase
        if rules_content:
            report["rules_content"] = rules_content
        output = json.dumps(report, ensure_ascii=False, indent=2)
    else:
        output = generate_markdown_stats(
            author_stats, violations,
            args.repo_url, args.branch, args.since, args.until,
        )

    # Write output
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"Report written to {args.output}", file=sys.stderr)
    else:
        print(output)


if __name__ == "__main__":
    main()
