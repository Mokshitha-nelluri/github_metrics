from github_api import fetch_commits, fetch_pull_requests
from datetime import datetime
import statistics
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def calculate_commit_metrics(owner, repo, developer_email):
    """
    Calculates commit-related metrics for a developer in a single repository.
    """
    logging.info(f"Fetching metrics for repository: {repo}")

    # Fetch commits and pull requests
    commits = fetch_commits(owner, repo, developer_email)
    pull_requests = fetch_pull_requests(owner, repo, developer_email)

    total_commits = len(commits)
    total_pull_requests = len(pull_requests)

    # Commit Frequency
    commit_dates = [commit.get("committedDate") for commit in commits if "committedDate" in commit]
    commit_frequencies = calculate_commit_frequency(commit_dates)

    # Commit Sizes
    commit_sizes = [(commit.get("additions", 0), commit.get("deletions", 0)) for commit in commits]
    average_commit_size = (
        sum(add + delete for add, delete in commit_sizes) / total_commits if total_commits else 0
    )

    # Commit to Merge Times
    commit_to_merge_times = calculate_commit_to_merge_time(commits, pull_requests)

    # Commits per PR
    commits_per_pr = calculate_commits_per_pull_request(pull_requests)

    return {
        "Total Commits": total_commits,
        "Total Pull Requests": total_pull_requests,
        "Commit Frequency (commits per week)": commit_frequencies,
        "Average Commit Size (additions + deletions)": average_commit_size,
        "Commit to Merge Time (seconds)": commit_to_merge_times,
        "Commits per Pull Request": commits_per_pr,
    }

def calculate_commit_frequency(commit_dates):
    """Calculate commit frequency by week."""
    commit_dates = [datetime.strptime(date, "%Y-%m-%dT%H:%M:%SZ") for date in commit_dates]
    week_commit_counts = {}
    for date in commit_dates:
        week = date.strftime("%Y-%U")
        week_commit_counts[week] = week_commit_counts.get(week, 0) + 1
    return week_commit_counts

def calculate_commit_to_merge_time(commits, pull_requests):
    """Calculate time from commit to PR merge."""
    commit_to_merge_times = []
    for pr in pull_requests:
        merged_at = pr.get("mergedAt")
        if not merged_at:
            continue
        merged_time = datetime.strptime(merged_at, "%Y-%m-%dT%H:%M:%SZ")
        for commit_node in pr.get("commits", {}).get("nodes", []):
            commit_time = datetime.strptime(commit_node["commit"]["committedDate"], "%Y-%m-%dT%H:%M:%SZ")
            commit_to_merge_times.append((merged_time - commit_time).total_seconds())
    return commit_to_merge_times

def calculate_commits_per_pull_request(pull_requests):
    """Calculate the average number of commits per PR."""
    total_commits = sum(len(pr["commits"]["nodes"]) for pr in pull_requests)
    total_prs = len(pull_requests)
    return total_commits / total_prs if total_prs else 0

if __name__ == "__main__":
    owner = input("Enter the repository owner: ")
    repo = input("Enter the repository name: ")
    developer_email = input("Enter the developer's email: ")

    metrics = calculate_commit_metrics(owner, repo, developer_email)
    print("\nRepository Metrics")
    for key, value in metrics.items():
        print(f"{key}: {value}")
