#!/usr/bin/env python3
"""
Script to automatically close GitHub issues with the "close-if-no-reply-timeout" label
if the last comment is from "jamesread" and is older than 2 weeks.

When run without a repo argument, processes every repository listed in
~/.config/jwr-github/maintained-repos.txt.

GitHub token is read from /etc/github/config.ini (github-token=...), GITHUB_TOKEN,
or --github-token.

Usage:
    jwr-gh-close-stale-isues.py user/repo
    jwr-gh-close-stale-isues.py
"""

import sys
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional, Tuple

import configargparse

try:
    from github import Github
    from github.Issue import Issue
except ImportError:
    print("Error: PyGithub is required. Install it with: pip install PyGithub")
    sys.exit(1)

try:
    from rich.console import Console
    from rich.logging import RichHandler
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text
except ImportError:
    print("Error: rich is required. Install it with: pip install rich")
    sys.exit(1)

# Interactive (TTY) gets color + markup; pipes/redirects stay plain.
IS_INTERACTIVE = sys.stdout.isatty()
console = Console(force_terminal=IS_INTERACTIVE, highlight=False)

logging.basicConfig(
    level=logging.INFO,
    format="%(message)s" if IS_INTERACTIVE else "%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        RichHandler(
            console=console,
            show_time=True,
            show_path=False,
            markup=True,
            rich_tracebacks=True,
        )
        if IS_INTERACTIVE
        else logging.StreamHandler()
    ],
)
logger = logging.getLogger(__name__)

# Configuration
TARGET_LABEL = "close-if-no-reply-timeout"
TARGET_USER = "jamesread"
TIMEOUT_DAYS = 14
MAINTAINED_REPOS_FILE = Path.home() / ".config" / "jwr-github" / "maintained-repos.txt"


def parse_args() -> configargparse.Namespace:
    parser = configargparse.ArgumentParser(
        description="Automatically close stale GitHub issues",
        default_config_files=["/etc/github/config.ini"],
    )
    parser.add(
        "repo",
        nargs="?",
        default=None,
        help=(
            'GitHub repository in "user/repo" format. '
            f"If omitted, process all repos in {MAINTAINED_REPOS_FILE}"
        ),
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


def validate_repo_name(repo: str) -> Tuple[str, str]:
    """Validate and split 'user/repo' into (owner, name)."""
    parts = repo.split("/")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ValueError(f'Invalid repository format: "{repo}". Expected "user/repo".')
    return parts[0], parts[1]


def load_maintained_repos() -> List[str]:
    """Load unique repo names from maintained-repos.txt."""
    if not MAINTAINED_REPOS_FILE.exists():
        logger.error(
            f"No repository given and [bold]{MAINTAINED_REPOS_FILE}[/] does not exist."
            if IS_INTERACTIVE
            else f"No repository given and {MAINTAINED_REPOS_FILE} does not exist."
        )
        sys.exit(1)

    seen = set()
    repos: List[str] = []
    for line in MAINTAINED_REPOS_FILE.read_text().splitlines():
        name = line.strip()
        if not name or name in seen:
            continue
        seen.add(name)
        repos.append(name)

    if not repos:
        logger.error(
            f"No repositories found in [bold]{MAINTAINED_REPOS_FILE}[/]."
            if IS_INTERACTIVE
            else f"No repositories found in {MAINTAINED_REPOS_FILE}."
        )
        sys.exit(1)

    return repos


def get_last_comment(issue: Issue) -> Optional[dict]:
    """
    Get the last comment on an issue.
    Returns a dict with 'user' and 'created_at' or None if no comments.
    """
    try:
        comments = list(issue.get_comments())
        if not comments:
            return None

        last_comment = comments[-1]
        return {
            "user": last_comment.user.login,
            "created_at": last_comment.created_at,
        }
    except Exception as e:
        logger.error(f"Error getting comments for issue #{issue.number}: {e}")
        return None


def should_close_issue(issue: Issue) -> Tuple[bool, str]:
    """
    Check if an issue should be closed.
    Returns (should_close, reason).
    """
    labels = [label.name for label in issue.labels]
    if TARGET_LABEL not in labels:
        return False, f"Missing label '{TARGET_LABEL}'"

    last_comment = get_last_comment(issue)
    if not last_comment:
        return False, "No comments found"

    if last_comment["user"] != TARGET_USER:
        return False, f"Last comment is from '{last_comment['user']}', not '{TARGET_USER}'"

    comment_time = last_comment["created_at"]
    if comment_time.tzinfo is None:
        comment_time = comment_time.replace(tzinfo=timezone.utc)
    else:
        comment_time = comment_time.astimezone(timezone.utc)

    now = datetime.now(timezone.utc)
    comment_age = now - comment_time
    if comment_age < timedelta(days=TIMEOUT_DAYS):
        return False, (
            f"Last comment is only {comment_age.days} days old "
            f"(need {TIMEOUT_DAYS} days)"
        )

    return True, f"Last comment from '{TARGET_USER}' is {comment_age.days} days old"


def print_banner(title: str, subtitle: Optional[str] = None) -> None:
    """Print a section banner suited to interactive or plain output."""
    if IS_INTERACTIVE:
        body = Text(title, style="bold cyan")
        if subtitle:
            body.append(f"\n{subtitle}", style="dim")
        console.print(Panel(body, border_style="cyan", padding=(0, 1)))
    else:
        logger.info("=" * 60)
        logger.info(title)
        if subtitle:
            logger.info(subtitle)
        logger.info("=" * 60)


def print_issue_header(index: int, total: int, number: int, title: str) -> None:
    if IS_INTERACTIVE:
        console.print()
        console.print(
            f"[dim]\\[{index}/{total}][/] "
            f"[bold]#{number}[/] [white]{title}[/]"
        )
    else:
        logger.info(f"\n[{index}/{total}] Processing issue #{number}: {title}")


def print_status(kind: str, message: str) -> None:
    """kind: closed | removed | skipped | error"""
    styles = {
        "closed": ("green", "✓", "CLOSED"),
        "removed": ("yellow", "⊙", "LABEL REMOVED"),
        "skipped": ("dim", "⊘", "Skipped"),
        "error": ("red", "✗", "Error"),
    }
    color, icon, label = styles[kind]
    if IS_INTERACTIVE:
        console.print(f"  [{color}]{icon} {label}[/{color}]: {message}")
        return

    line = f"  {icon} {label}: {message}"
    if kind == "error":
        logger.error(line)
    else:
        logger.info(line)


def print_repo_summary(
    repo_name: str,
    processed: int,
    closed: int,
    label_removed: int,
    skipped: int,
) -> None:
    if IS_INTERACTIVE:
        table = Table(
            title=f"Summary — {repo_name}",
            show_header=True,
            header_style="bold",
            border_style="dim",
            title_style="bold",
        )
        table.add_column("Metric", style="cyan")
        table.add_column("Count", justify="right")
        table.add_row("Processed", str(processed))
        table.add_row("Closed", f"[green]{closed}[/]" if closed else "0")
        table.add_row(
            "Labels removed",
            f"[yellow]{label_removed}[/]" if label_removed else "0",
        )
        table.add_row("Skipped", f"[dim]{skipped}[/]")
        console.print()
        console.print(table)
    else:
        logger.info(
            "Summary for %s — processed: %s, closed: %s, labels removed: %s, skipped: %s",
            repo_name,
            processed,
            closed,
            label_removed,
            skipped,
        )


def process_repo(github: Github, repo_name: str) -> bool:
    """
    Process stale issues for one repository.
    Returns True on success, False on failure.
    """
    try:
        owner, name = validate_repo_name(repo_name)
    except ValueError as e:
        logger.error(str(e))
        return False

    print_banner(f"Repository: {owner}/{name}")

    try:
        repo = github.get_repo(f"{owner}/{name}")
        if IS_INTERACTIVE:
            console.print(f"[green]Connected[/] to [bold]{repo.full_name}[/]")
        else:
            logger.info(f"Successfully connected to repository: {repo.full_name}")
    except Exception as e:
        logger.error(f"Error connecting to repository: {e}")
        return False

    if IS_INTERACTIVE:
        console.print("[dim]Fetching open issues…[/]")
    else:
        logger.info("Fetching open issues...")

    try:
        open_issues = list(repo.get_issues(state="open"))
        if IS_INTERACTIVE:
            console.print(f"Found [bold]{len(open_issues)}[/] open issues")
        else:
            logger.info(f"Found {len(open_issues)} open issues")
    except Exception as e:
        logger.error(f"Error fetching issues: {e}")
        return False

    processed_count = 0
    closed_count = 0
    skipped_count = 0
    label_removed_count = 0

    for issue in open_issues:
        processed_count += 1
        print_issue_header(processed_count, len(open_issues), issue.number, issue.title)

        labels = [label.name for label in issue.labels]
        if TARGET_LABEL in labels:
            last_comment = get_last_comment(issue)
            if last_comment and last_comment["user"] != TARGET_USER:
                try:
                    issue.remove_from_labels(TARGET_LABEL)
                    print_status(
                        "removed",
                        f"Last comment is from '{last_comment['user']}', "
                        f"giving '{TARGET_USER}' time to reply",
                    )
                    label_removed_count += 1
                    skipped_count += 1
                    continue
                except Exception as e:
                    print_status(
                        "error",
                        f"removing label from issue #{issue.number}: {e}",
                    )

        should_close, reason = should_close_issue(issue)

        if should_close:
            try:
                issue.edit(state="closed")
                print_status("closed", reason)
                closed_count += 1
            except Exception as e:
                print_status("error", f"closing issue #{issue.number}: {e}")
        else:
            print_status("skipped", reason)
            skipped_count += 1

    print_repo_summary(
        repo.full_name,
        processed_count,
        closed_count,
        label_removed_count,
        skipped_count,
    )
    return True


def main():
    """Main function to process issues."""
    args = parse_args()

    subtitle = (
        f"label={TARGET_LABEL}  ·  user={TARGET_USER}  ·  timeout={TIMEOUT_DAYS}d"
    )
    print_banner("GitHub Issue Auto-Close", subtitle)

    if args.repo:
        repos = [args.repo]
    else:
        repos = load_maintained_repos()
        msg = (
            f"No repository given; processing [bold]{len(repos)}[/] from "
            f"[dim]{MAINTAINED_REPOS_FILE}[/]"
            if IS_INTERACTIVE
            else f"No repository given; processing {len(repos)} from {MAINTAINED_REPOS_FILE}"
        )
        if IS_INTERACTIVE:
            console.print(msg)
        else:
            logger.info(msg)

    github = Github(args.github_token)

    failures = 0
    for repo_name in repos:
        if not process_repo(github, repo_name):
            failures += 1

    if IS_INTERACTIVE:
        console.print()
        if len(repos) > 1:
            succeeded = len(repos) - failures
            style = "green" if failures == 0 else "yellow"
            console.print(
                f"[{style}]Finished:[/{style}] "
                f"[bold]{succeeded}/{len(repos)}[/] repositories succeeded"
            )
        if failures:
            console.print(f"[bold red]Exiting with {failures} failure(s)[/]")
            sys.exit(1)
        console.print("[bold green]Done[/]")
    else:
        logger.info("=" * 60)
        if len(repos) > 1:
            logger.info(
                f"Finished: {len(repos) - failures}/{len(repos)} repositories succeeded"
            )
        if failures:
            sys.exit(1)
        logger.info("=" * 60)


if __name__ == "__main__":
    main()
