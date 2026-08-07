#!/usr/bin/env python3
"""
List open GitHub issues across Greyvar, OliveTin, and jamesread.

Equivalent to the GitHub web search:
    (org:Greyvar OR org:OliveTin OR user:jamesread) is:open sort:updated-asc archived:false

The Search API does not accept OR across org/user qualifiers alone, so each scope is
queried separately and results are merged, deduplicated, and sorted locally.

Writes a Markdown report to ~/gh-issues-report.md with Active and Pending
sections. Pending items have the "close-if-no-reply-timeout" label; all others
are Active. Within each section, items are grouped by project then by type
(issue / pull request).

GitHub token is read from /etc/github/config.ini (github-token=...), GITHUB_TOKEN,
or --github-token.

Usage:
    jwr-gh-list-open-issues.py
"""

import sys
import logging
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

import configargparse

try:
    from github import Github
    from github.Issue import Issue
except ImportError:
    print("Error: PyGithub is required. Install it with: pip install PyGithub")
    sys.exit(1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)

# Scopes that make up: (org:Greyvar OR org:OliveTin OR user:jamesread)
SEARCH_SCOPES = ("org:Greyvar", "org:OliveTin", "user:jamesread")
SEARCH_FILTERS = "is:open archived:false"
REPORT_PATH = Path.home() / "gh-issues-report.md"

# Display order for type sections
TYPE_ORDER = ("Issue", "Pull Request")

# Issues with this label are listed under Pending; all others under Active
PENDING_LABEL = "close-if-no-reply-timeout"


def parse_args() -> configargparse.Namespace:
    parser = configargparse.ArgumentParser(
        description="List open GitHub issues across Greyvar, OliveTin, and jamesread",
        default_config_files=["/etc/github/config.ini"],
    )
    parser.add(
        "-c",
        "--config",
        is_config_file=True,
        help="Path to configuration file",
    )
    parser.add(
        "--github-token",
        env_var="GITHUB_TOKEN",
        required=True,
        help="GitHub API token",
    )
    return parser.parse_args()


def repo_full_name(issue: Issue) -> str:
    """Parse owner/repo from the HTML URL (avoids an extra API call)."""
    url_parts = issue.html_url.rstrip("/").split("/")
    if len(url_parts) >= 5:
        return f"{url_parts[3]}/{url_parts[4]}"
    return "?"


def item_type(issue: Issue) -> str:
    """Classify a search result as Issue or Pull Request from the HTML URL."""
    if "/pull/" in issue.html_url:
        return "Pull Request"
    return "Issue"


def is_pending(issue: Issue) -> bool:
    """True if the issue has the close-if-no-reply-timeout label."""
    return any(label.name == PENDING_LABEL for label in issue.labels)


def search_scope(github: Github, scope: str) -> List[Issue]:
    query = f"{scope} {SEARCH_FILTERS}"
    logger.info(f"Searching: {query}")
    try:
        results = github.search_issues(query=query, sort="updated", order="asc")
        issues = list(results)
        logger.info(f"  → {len(issues)} results")
        return issues
    except Exception as e:
        logger.error(f"  ✗ Error searching '{query}': {e}")
        return []


def group_items(
    items: List[Issue],
) -> Dict[str, Dict[str, List[Issue]]]:
    """Group by project, then by type. Items within each group sorted by updated_at."""
    grouped: Dict[str, Dict[str, List[Issue]]] = defaultdict(lambda: defaultdict(list))
    for issue in items:
        grouped[repo_full_name(issue)][item_type(issue)].append(issue)

    for project in grouped:
        for kind in grouped[project]:
            grouped[project][kind].sort(key=lambda i: i.updated_at)

    return grouped


def count_items(grouped: Dict[str, Dict[str, List[Issue]]]) -> int:
    return sum(len(items) for kinds in grouped.values() for items in kinds.values())


def format_section(
    title: str,
    grouped: Dict[str, Dict[str, List[Issue]]],
) -> List[str]:
    total = count_items(grouped)
    lines: List[str] = [
        f"## {title} ({total})",
        "",
    ]

    if total == 0:
        lines.append("*None*")
        lines.append("")
        return lines

    for project in sorted(grouped):
        kinds = grouped[project]
        project_total = sum(len(v) for v in kinds.values())
        lines.append(f"### {project} ({project_total})")
        lines.append("")

        ordered_kinds = [k for k in TYPE_ORDER if k in kinds]
        ordered_kinds.extend(sorted(k for k in kinds if k not in TYPE_ORDER))

        for kind in ordered_kinds:
            issues = kinds[kind]
            lines.append(f"#### {kind}s ({len(issues)})")
            lines.append("")
            for issue in issues:
                updated = issue.updated_at.strftime("%Y-%m-%d %H:%M:%S UTC")
                lines.append(f"- [#{issue.number} {issue.title}]({issue.html_url})")
                lines.append(f"  - updated: {updated}")
            lines.append("")

    return lines


def format_report(
    active: Dict[str, Dict[str, List[Issue]]],
    pending: Dict[str, Dict[str, List[Issue]]],
) -> str:
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    active_count = count_items(active)
    pending_count = count_items(pending)
    total = active_count + pending_count

    lines: List[str] = [
        "# GitHub Open Issues Report",
        "",
        f"**Generated:** {now}",
        "",
        "**Query:** `(org:Greyvar OR org:OliveTin OR user:jamesread) "
        f"{SEARCH_FILTERS} sort:updated-asc`",
        "",
        f"**Total:** {total} (Active: {active_count}, Pending: {pending_count})",
        "",
        f"Pending = labeled `{PENDING_LABEL}`",
        "",
    ]
    lines.extend(format_section("Active", active))
    lines.extend(format_section("Pending", pending))

    return "\n".join(lines).rstrip() + "\n"


def main():
    args = parse_args()

    logger.info("=" * 60)
    logger.info("GitHub Open Issues List")
    logger.info("=" * 60)
    logger.info(
        "Intent: (org:Greyvar OR org:OliveTin OR user:jamesread) "
        f"{SEARCH_FILTERS} sort:updated-asc"
    )
    logger.info(f"Report: {REPORT_PATH}")
    logger.info("=" * 60)

    github = Github(args.github_token)

    by_id = {}
    for scope in SEARCH_SCOPES:
        for issue in search_scope(github, scope):
            by_id[issue.id] = issue

    items = list(by_id.values())
    active_items = [i for i in items if not is_pending(i)]
    pending_items = [i for i in items if is_pending(i)]
    active = group_items(active_items)
    pending = group_items(pending_items)
    report = format_report(active, pending)

    try:
        REPORT_PATH.write_text(report, encoding="utf-8")
    except OSError as e:
        logger.error(f"Failed to write {REPORT_PATH}: {e}")
        sys.exit(1)

    logger.info(
        f"Wrote {len(items)} items "
        f"(Active: {len(active_items)}, Pending: {len(pending_items)}) "
        f"to {REPORT_PATH}"
    )


if __name__ == "__main__":
    main()
