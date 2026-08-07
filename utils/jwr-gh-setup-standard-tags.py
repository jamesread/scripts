#!/usr/bin/env python3
"""
Script to create/update a standard set of GitHub labels on a repository.

Does nothing if all standard labels already exist with the expected color.
Registers the repository in ~/.config/jwr-github/maintained-repos.txt (deduplicated).

When run without a repo argument, processes every repository listed in
~/.config/jwr-github/maintained-repos.txt.

GitHub token is read from /etc/github/config.ini (github-token=...), GITHUB_TOKEN,
or --github-token.

Usage:
    jwr-gh-setup-standard-tags.py user/repo
    jwr-gh-setup-standard-tags.py
"""

import sys
import logging
from pathlib import Path
from typing import Dict, List, Tuple

import configargparse

try:
    from github import Github
    from github.Repository import Repository
except ImportError:
    print("Error: PyGithub is required. Install it with: pip install PyGithub")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Standard labels: name -> color (hex without '#')
STANDARD_LABELS: Dict[str, str] = {
    "close-if-no-reply-timeout": "ffa500",  # orange
    "needs-feedback-after-fix": "0e8a16",  # green
}

MAINTAINED_REPOS_FILE = Path.home() / ".config" / "jwr-github" / "maintained-repos.txt"


def parse_args() -> configargparse.Namespace:
    parser = configargparse.ArgumentParser(
        description="Create/update standard GitHub labels on a repository",
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
        logger.error(f"No repository given and {MAINTAINED_REPOS_FILE} does not exist.")
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
        logger.error(f"No repositories found in {MAINTAINED_REPOS_FILE}.")
        sys.exit(1)

    return repos


def get_existing_labels(repo: Repository) -> Dict[str, str]:
    """Return a mapping of label name -> color for the repository."""
    return {label.name: label.color.lower() for label in repo.get_labels()}


def ensure_standard_labels(repo: Repository) -> Tuple[int, int, int]:
    """
    Create or update standard labels on the repository.
    Returns (created_count, updated_count, skipped_count).
    """
    existing = get_existing_labels(repo)
    created = 0
    updated = 0
    skipped = 0

    for name, color in STANDARD_LABELS.items():
        expected_color = color.lower()

        if name not in existing:
            try:
                repo.create_label(name=name, color=expected_color)
                logger.info(f"  ✓ Created label '{name}' (color: #{expected_color})")
                created += 1
            except Exception as e:
                logger.error(f"  ✗ Error creating label '{name}': {e}")
            continue

        if existing[name] != expected_color:
            try:
                label = repo.get_label(name)
                label.edit(name=name, color=expected_color)
                logger.info(
                    f"  ✓ Updated label '{name}': "
                    f"#{existing[name]} -> #{expected_color}"
                )
                updated += 1
            except Exception as e:
                logger.error(f"  ✗ Error updating label '{name}': {e}")
            continue

        logger.info(f"  ⊘ Label '{name}' already exists with correct color")
        skipped += 1

    return created, updated, skipped


def register_maintained_repo(full_name: str) -> None:
    """Append owner/repo to maintained-repos.txt if not already listed."""
    try:
        if MAINTAINED_REPOS_FILE.exists():
            existing = {
                line.strip()
                for line in MAINTAINED_REPOS_FILE.read_text().splitlines()
                if line.strip()
            }
            if full_name in existing:
                logger.info(f"Repository already listed in {MAINTAINED_REPOS_FILE}")
                return

        MAINTAINED_REPOS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with MAINTAINED_REPOS_FILE.open("a") as f:
            f.write(f"{full_name}\n")
        logger.info(f"Added {full_name} to {MAINTAINED_REPOS_FILE}")
    except OSError as e:
        logger.error(f"Failed to update {MAINTAINED_REPOS_FILE}: {e}")
        sys.exit(1)


def process_repo(github: Github, repo_name: str, *, register: bool) -> bool:
    """
    Ensure standard labels on one repository.
    Returns True on success, False on failure.
    """
    try:
        owner, name = validate_repo_name(repo_name)
    except ValueError as e:
        logger.error(str(e))
        return False

    logger.info("=" * 60)
    logger.info(f"Repository: {owner}/{name}")
    logger.info("=" * 60)

    try:
        repo = github.get_repo(f"{owner}/{name}")
        logger.info(f"Successfully connected to repository: {repo.full_name}")
    except Exception as e:
        logger.error(f"Error connecting to repository: {e}")
        return False

    if register:
        register_maintained_repo(repo.full_name)

    existing = get_existing_labels(repo)
    all_present = all(
        label_name in existing and existing[label_name] == color.lower()
        for label_name, color in STANDARD_LABELS.items()
    )

    if all_present:
        logger.info(
            "All standard labels already exist with the expected colors. Nothing to do."
        )
        return True

    logger.info("Ensuring standard labels...")
    created, updated, skipped = ensure_standard_labels(repo)

    logger.info("Summary for %s — created: %s, updated: %s, skipped: %s",
                repo.full_name, created, updated, skipped)
    return True


def main():
    """Main function to set up standard labels."""
    args = parse_args()

    logger.info("=" * 60)
    logger.info("GitHub Standard Labels Setup")
    logger.info("=" * 60)
    logger.info(f"Standard labels: {len(STANDARD_LABELS)}")
    for label_name, color in STANDARD_LABELS.items():
        logger.info(f"  - {label_name} (#{color})")

    if args.repo:
        repos = [args.repo]
        register = True
    else:
        repos = load_maintained_repos()
        register = False
        logger.info(
            f"No repository given; processing {len(repos)} from {MAINTAINED_REPOS_FILE}"
        )

    github = Github(args.github_token)

    failures = 0
    for repo_name in repos:
        if not process_repo(github, repo_name, register=register):
            failures += 1

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
