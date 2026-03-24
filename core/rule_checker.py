"""Programmatic rule checking for commit messages and practices.

Checks rules that can be verified without LLM (format, length, patterns).
Soft/subjective rules are left for the LLM analysis phase.
"""

import re
from pathlib import Path

from .models import CommitData, RuleViolation

# Built-in checks that are commonly expected
CONVENTIONAL_COMMIT_RE = re.compile(
    r"^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\(.+\))?!?:\s.+"
)


def check_all(
    commits: list[CommitData],
    rules_md_path: str | None = None,
) -> tuple[list[RuleViolation], str | None]:
    """Run programmatic checks. Returns violations and the rules content for LLM phase."""
    violations: list[RuleViolation] = []
    rules_content = None

    if rules_md_path and Path(rules_md_path).exists():
        rules_content = Path(rules_md_path).read_text(encoding="utf-8")

    for commit in commits:
        if commit.is_merge:
            continue  # skip merge commits for rule checking

        violations.extend(_check_message_basics(commit))

        # If rules_md mentions conventional commits, check that
        if rules_content and "conventional" in rules_content.lower():
            violations.extend(_check_conventional_commit(commit))

    return violations, rules_content


def _check_message_basics(commit: CommitData) -> list[RuleViolation]:
    """Basic commit message quality checks."""
    violations = []
    subject = commit.message.split("\n")[0]

    if len(subject) < 5:
        violations.append(
            RuleViolation(
                rule_name="message_too_short",
                severity="warning",
                message=f"Commit message subject is too short ({len(subject)} chars): '{subject}'",
                commit_sha=commit.short_sha,
            )
        )

    if len(subject) > 120:
        violations.append(
            RuleViolation(
                rule_name="message_too_long",
                severity="warning",
                message=f"Commit message subject exceeds 120 chars ({len(subject)})",
                commit_sha=commit.short_sha,
            )
        )

    if subject and subject[0].islower():
        pass  # conventional commits are lowercase, not a violation

    return violations


def _check_conventional_commit(commit: CommitData) -> list[RuleViolation]:
    """Check if commit follows conventional commit format."""
    subject = commit.message.split("\n")[0]
    if not CONVENTIONAL_COMMIT_RE.match(subject):
        return [
            RuleViolation(
                rule_name="conventional_commit_format",
                severity="error",
                message=f"Does not follow conventional commit format: '{subject[:80]}'",
                commit_sha=commit.short_sha,
            )
        ]
    return []
