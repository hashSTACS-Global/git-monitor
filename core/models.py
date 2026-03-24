"""Data models for commit analysis."""

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class FileDiff:
    filename: str
    status: str  # added, modified, deleted, renamed
    additions: int
    deletions: int
    patch: str  # actual diff content


@dataclass
class CommitData:
    sha: str
    short_sha: str
    author_name: str
    author_email: str
    date: datetime
    message: str
    files: list[FileDiff] = field(default_factory=list)
    total_additions: int = 0
    total_deletions: int = 0
    is_merge: bool = False

    def to_dict(self) -> dict:
        return {
            "sha": self.sha,
            "short_sha": self.short_sha,
            "author_name": self.author_name,
            "author_email": self.author_email,
            "date": self.date.isoformat(),
            "message": self.message,
            "total_additions": self.total_additions,
            "total_deletions": self.total_deletions,
            "is_merge": self.is_merge,
            "files": [
                {
                    "filename": f.filename,
                    "status": f.status,
                    "additions": f.additions,
                    "deletions": f.deletions,
                    "patch_lines": len(f.patch.splitlines()) if f.patch else 0,
                }
                for f in self.files
            ],
        }


@dataclass
class AuthorStats:
    name: str
    email: str
    commit_count: int = 0
    total_additions: int = 0
    total_deletions: int = 0
    commits: list[dict] = field(default_factory=list)  # summary per commit

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "email": self.email,
            "commit_count": self.commit_count,
            "total_additions": self.total_additions,
            "total_deletions": self.total_deletions,
            "commits": self.commits,
        }


@dataclass
class RuleViolation:
    rule_name: str
    severity: str  # error, warning, info
    message: str
    commit_sha: str

    def to_dict(self) -> dict:
        return {
            "rule_name": self.rule_name,
            "severity": self.severity,
            "message": self.message,
            "commit_sha": self.commit_sha,
        }
