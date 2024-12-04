from datetime import datetime
import statistics

class MetricsCalculator:
    """Processes data to calculate metrics."""

    def calculate_commit_frequency(self, commits):
        """Calculate weekly commit frequency."""
        commit_dates = [datetime.strptime(commit["committedDate"], "%Y-%m-%dT%H:%M:%SZ") for commit in commits]
        weekly_counts = {}
        for date in commit_dates:
            week = date.strftime("%Y-%U")
            weekly_counts[week] = weekly_counts.get(week, 0) + 1
        return weekly_counts

    def calculate_commit_to_merge_time(self, commits, pull_requests):
        """Calculate the time from commit to PR merge."""
        times = []
        for pr in pull_requests:
            if not pr.get("mergedAt"):
                continue
            merge_time = datetime.strptime(pr["mergedAt"], "%Y-%m-%dT%H:%M:%SZ")
            for commit in pr.get("commits", {}).get("nodes", []):
                commit_time = datetime.strptime(commit["commit"]["committedDate"], "%Y-%m-%dT%H:%M:%SZ")
                times.append((merge_time - commit_time).total_seconds())
        return times

    def calculate_commits_per_pull_request(self, pull_requests):
        """Calculate average commits per PR."""
        total_commits = sum(len(pr["commits"]["nodes"]) for pr in pull_requests)
        total_prs = len(pull_requests)
        return total_commits / total_prs if total_prs else 0

    def calculate_total_commits(self, commits):
        """Calculate total number of commits."""
        return len(commits)

    def calculate_average_commit_size(self, commits):
        """
        Calculate the average commit size in terms of additions and deletions.
        
        Average Commit Size = (Total additions + Total deletions) / Total commits
        """
        total_commits = len(commits)
        total_additions = sum(commit.get("additions", 0) for commit in commits)
        total_deletions = sum(commit.get("deletions", 0) for commit in commits)
        
        if total_commits == 0:
            return 0  # Avoid division by zero
        
        return (total_additions + total_deletions) / total_commits
