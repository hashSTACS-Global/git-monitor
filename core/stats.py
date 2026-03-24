"""Statistics computation: aggregate commit data by author."""

from .models import AuthorStats, CommitData


def stats_by_author(commits: list[CommitData]) -> dict[str, AuthorStats]:
    """Group and summarize commits by author."""
    authors: dict[str, AuthorStats] = {}

    for c in commits:
        key = c.author_email
        if key not in authors:
            authors[key] = AuthorStats(name=c.author_name, email=c.author_email)

        a = authors[key]
        a.commit_count += 1
        a.total_additions += c.total_additions
        a.total_deletions += c.total_deletions
        a.commits.append(
            {
                "sha": c.short_sha,
                "date": c.date.isoformat(),
                "message": c.message.split("\n")[0][:120],
                "additions": c.total_additions,
                "deletions": c.total_deletions,
                "files_changed": len(c.files),
                "is_merge": c.is_merge,
            }
        )

    return authors
