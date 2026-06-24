#!/usr/bin/env python3
"""
Script to automatically close GitHub issues with the "close-if-no-reply-timeout" label
if the last comment is from "jamesread" and is older than 2 weeks.

GitHub token is read from /etc/github/config.ini (github-token=...), GITHUB_TOKEN,
or --github-token.
"""

import sys
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

import configargparse

try:
    from github import Github
    from github.Issue import Issue
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

# Configuration
REPO_OWNER = "OliveTin"
REPO_NAME = "OliveTin"
TARGET_LABEL = "close-if-no-reply-timeout"
TARGET_USER = "jamesread"
TIMEOUT_DAYS = 14


def parse_args() -> configargparse.Namespace:
    parser = configargparse.ArgumentParser(
        description="Automatically close stale GitHub issues",
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
            'user': last_comment.user.login,
            'created_at': last_comment.created_at
        }
    except Exception as e:
        logger.error(f"Error getting comments for issue #{issue.number}: {e}")
        return None


def should_close_issue(issue: Issue) -> Tuple[bool, str]:
    """
    Check if an issue should be closed.
    Returns (should_close, reason).
    """
    # Check if issue has the target label
    labels = [label.name for label in issue.labels]
    if TARGET_LABEL not in labels:
        return False, f"Missing label '{TARGET_LABEL}'"
    
    # Get last comment
    last_comment = get_last_comment(issue)
    if not last_comment:
        return False, "No comments found"
    
    # Check if last comment is from target user
    if last_comment['user'] != TARGET_USER:
        return False, f"Last comment is from '{last_comment['user']}', not '{TARGET_USER}'"
    
    # Check if comment is older than timeout
    comment_time = last_comment['created_at']
    # Ensure timezone-aware datetime
    if comment_time.tzinfo is None:
        comment_time = comment_time.replace(tzinfo=timezone.utc)
    else:
        comment_time = comment_time.astimezone(timezone.utc)
    
    now = datetime.now(timezone.utc)
    comment_age = now - comment_time
    if comment_age < timedelta(days=TIMEOUT_DAYS):
        return False, f"Last comment is only {comment_age.days} days old (need {TIMEOUT_DAYS} days)"
    
    return True, f"Last comment from '{TARGET_USER}' is {comment_age.days} days old"


def main():
    """Main function to process issues."""
    args = parse_args()

    logger.info("=" * 60)
    logger.info("GitHub Issue Auto-Close Script")
    logger.info("=" * 60)
    logger.info(f"Repository: {REPO_OWNER}/{REPO_NAME}")
    logger.info(f"Target label: {TARGET_LABEL}")
    logger.info(f"Target user: {TARGET_USER}")
    logger.info(f"Timeout: {TIMEOUT_DAYS} days")
    logger.info("=" * 60)
    
    github = Github(args.github_token)
    
    try:
        repo = github.get_repo(f"{REPO_OWNER}/{REPO_NAME}")
        logger.info(f"Successfully connected to repository: {repo.full_name}")
    except Exception as e:
        logger.error(f"Error connecting to repository: {e}")
        sys.exit(1)
    
    # Get all open issues
    logger.info("Fetching open issues...")
    try:
        open_issues = list(repo.get_issues(state="open"))
        logger.info(f"Found {len(open_issues)} open issues")
    except Exception as e:
        logger.error(f"Error fetching issues: {e}")
        sys.exit(1)
    
    # Process each issue
    processed_count = 0
    closed_count = 0
    skipped_count = 0
    label_removed_count = 0
    
    for issue in open_issues:
        processed_count += 1
        logger.info(f"\n[{processed_count}/{len(open_issues)}] Processing issue #{issue.number}: {issue.title}")
        
        # Check if issue has the target label and last comment is not from jamesread
        labels = [label.name for label in issue.labels]
        if TARGET_LABEL in labels:
            last_comment = get_last_comment(issue)
            if last_comment and last_comment['user'] != TARGET_USER:
                try:
                    issue.remove_from_labels(TARGET_LABEL)
                    logger.info(f"  ⊙ Removed label '{TARGET_LABEL}': Last comment is from '{last_comment['user']}', giving '{TARGET_USER}' time to reply")
                    label_removed_count += 1
                    skipped_count += 1
                    continue
                except Exception as e:
                    logger.error(f"  ✗ Error removing label from issue #{issue.number}: {e}")
        
        should_close, reason = should_close_issue(issue)
        
        if should_close:
            try:
                issue.edit(state="closed")
                logger.info(f"  ✓ CLOSED: {reason}")
                closed_count += 1
            except Exception as e:
                logger.error(f"  ✗ Error closing issue #{issue.number}: {e}")
        else:
            logger.info(f"  ⊘ Skipped: {reason}")
            skipped_count += 1
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("Summary")
    logger.info("=" * 60)
    logger.info(f"Total issues processed: {processed_count}")
    logger.info(f"Issues closed: {closed_count}")
    logger.info(f"Labels removed: {label_removed_count}")
    logger.info(f"Issues skipped: {skipped_count}")
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
