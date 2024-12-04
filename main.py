from github_api import GitHubAPI
from metrics_calculator import MetricsCalculator
import os
from dotenv import load_dotenv

def main():
    load_dotenv()
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise ValueError("GitHub token is not set in the .env file.")

    owner = input("Enter the repository owner: ")
    repo = input("Enter the repository name: ")
    developer_email = input("Enter the developer's email: ")

    # Initialize API and Metrics Calculator
    github = GitHubAPI(token)
    metrics_calculator = MetricsCalculator()

    # Fetch data
    commits = github.fetch_commits(owner, repo, developer_email)
    pull_requests = github.fetch_pull_requests(owner, repo, developer_email)

    # Calculate metrics
    total_commits = metrics_calculator.calculate_total_commits(commits)
    average_commit_size = metrics_calculator.calculate_average_commit_size(commits)
    commit_frequency = metrics_calculator.calculate_commit_frequency(commits)
    commit_to_merge_times = metrics_calculator.calculate_commit_to_merge_time(commits, pull_requests)
    commits_per_pr = metrics_calculator.calculate_commits_per_pull_request(pull_requests)

    # Display metrics
    print("\nMetrics for Repository:", repo)
    print(f"Total Commits: {total_commits}")
    print(f"Average Commit Size (additions + deletions): {average_commit_size:.2f}")
    print("Commit Frequency (by week):", commit_frequency)
    print("Average Commit to Merge Time (seconds):", statistics.mean(commit_to_merge_times) if commit_to_merge_times else "N/A")
    print("Commits per Pull Request:", commits_per_pr)

if __name__ == "__main__":
    main()
