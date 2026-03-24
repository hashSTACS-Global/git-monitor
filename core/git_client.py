"""Git operations: clone repos and extract commit data with diffs."""

import os
import re
import subprocess
from datetime import datetime
from pathlib import Path

from .models import CommitData, FileDiff

# Where cloned repos are stored
DEFAULT_CLONE_DIR = Path.home() / ".cache" / "git-monitor" / "repos"


def _run_git(args: list[str], cwd: str) -> str:
    result = subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {result.stderr.strip()}")
    return result.stdout


def ensure_repo(repo_url: str, clone_dir: str | None = None) -> str:
    """Clone or update a repo. Returns the local path."""
    clone_base = Path(clone_dir) if clone_dir else DEFAULT_CLONE_DIR
    clone_base.mkdir(parents=True, exist_ok=True)

    # Derive folder name from URL
    repo_name = repo_url.rstrip("/").split("/")[-1].removesuffix(".git")
    owner = repo_url.rstrip("/").split("/")[-2]
    local_path = clone_base / f"{owner}__{repo_name}"

    if local_path.exists():
        # Fetch latest
        _run_git(["fetch", "--all", "--prune"], cwd=str(local_path))
    else:
        subprocess.run(
            ["git", "clone", "--no-checkout", repo_url, str(local_path)],
            capture_output=True,
            text=True,
            timeout=300,
            check=True,
        )

    return str(local_path)


def get_commits(
    repo_path: str,
    branch: str = "main",
    since: str | None = None,
    until: str | None = None,
) -> list[CommitData]:
    """Get commit list for a branch within a time range."""
    args = [
        "log",
        f"origin/{branch}",
        "--format=%H|%h|%an|%ae|%aI|%P|%s",
    ]
    if since:
        args.append(f"--since={since}")
    if until:
        args.append(f"--until={until}")

    output = _run_git(args, cwd=repo_path)
    commits = []

    for line in output.strip().splitlines():
        if not line.strip():
            continue
        parts = line.split("|", 6)
        if len(parts) < 7:
            continue

        sha, short_sha, author_name, author_email, date_str, parents, subject = parts
        is_merge = " " in parents.strip()  # merge commits have multiple parents

        commits.append(
            CommitData(
                sha=sha,
                short_sha=short_sha,
                author_name=author_name,
                author_email=author_email,
                date=datetime.fromisoformat(date_str),
                message=subject,
                is_merge=is_merge,
            )
        )

    return commits


def get_commit_full_message(repo_path: str, sha: str) -> str:
    """Get the full commit message (subject + body)."""
    return _run_git(["log", "-1", "--format=%B", sha], cwd=repo_path).strip()


def get_commit_diff(repo_path: str, sha: str, max_diff_lines: int = 5000) -> list[FileDiff]:
    """Get the diff for a single commit with line stats and patches."""
    # Get numstat first for accurate line counts
    numstat_output = _run_git(
        ["show", "--numstat", "--format=", sha], cwd=repo_path
    )

    file_stats: dict[str, tuple[int, int]] = {}
    for line in numstat_output.strip().splitlines():
        if not line.strip():
            continue
        parts = line.split("\t", 2)
        if len(parts) == 3:
            adds_str, dels_str, filename = parts
            adds = int(adds_str) if adds_str != "-" else 0
            dels = int(dels_str) if dels_str != "-" else 0
            file_stats[filename] = (adds, dels)

    # Get the actual diff patches
    diff_output = _run_git(
        ["show", "--format=", "--patch", sha], cwd=repo_path
    )

    # Parse diff into per-file patches
    files = _parse_diff(diff_output, file_stats, max_diff_lines)
    return files


def _parse_diff(
    diff_output: str,
    file_stats: dict[str, tuple[int, int]],
    max_lines: int,
) -> list[FileDiff]:
    """Parse unified diff output into FileDiff objects."""
    files: list[FileDiff] = []
    current_file = None
    current_patch_lines: list[str] = []
    total_lines = 0

    diff_header_re = re.compile(r"^diff --git a/(.*) b/(.*)")

    for line in diff_output.splitlines():
        header_match = diff_header_re.match(line)
        if header_match:
            # Save previous file
            if current_file:
                _finalize_file(files, current_file, current_patch_lines, file_stats)

            current_file = header_match.group(2)
            current_patch_lines = [line]
            total_lines += 1
        elif current_file:
            if total_lines < max_lines:
                current_patch_lines.append(line)
                total_lines += 1

    # Save last file
    if current_file:
        _finalize_file(files, current_file, current_patch_lines, file_stats)

    return files


def _finalize_file(
    files: list[FileDiff],
    filename: str,
    patch_lines: list[str],
    file_stats: dict[str, tuple[int, int]],
) -> None:
    patch = "\n".join(patch_lines)

    # Detect status from diff content
    status = "modified"
    if any(l.startswith("new file") for l in patch_lines[:5]):
        status = "added"
    elif any(l.startswith("deleted file") for l in patch_lines[:5]):
        status = "deleted"
    elif any(l.startswith("rename from") for l in patch_lines[:5]):
        status = "renamed"

    adds, dels = file_stats.get(filename, (0, 0))

    files.append(
        FileDiff(
            filename=filename,
            status=status,
            additions=adds,
            deletions=dels,
            patch=patch,
        )
    )


def enrich_commits(
    repo_path: str,
    commits: list[CommitData],
    include_diffs: bool = True,
    max_diff_lines: int = 5000,
) -> list[CommitData]:
    """Enrich commits with full messages and diffs."""
    for commit in commits:
        commit.message = get_commit_full_message(repo_path, commit.sha)

        if include_diffs:
            commit.files = get_commit_diff(repo_path, commit.sha, max_diff_lines)
            commit.total_additions = sum(f.additions for f in commit.files)
            commit.total_deletions = sum(f.deletions for f in commit.files)

    return commits
