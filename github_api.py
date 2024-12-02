import requests
from dotenv import load_dotenv
import os
import logging
import time

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Load environment variables
load_dotenv()
GITHUB_API_URL = "https://api.github.com/graphql"
ACCESS_TOKEN = os.getenv("GITHUB_TOKEN")

if not ACCESS_TOKEN:
    raise ValueError("GitHub token not found. Set it in the .env file.")

HEADERS = {"Authorization": f"Bearer {ACCESS_TOKEN}"}

# GraphQL Queries
COMMIT_QUERY = """
query ($owner: String!, $repo: String!, $author: String!, $cursor: String) {
  repository(owner: $owner, name: $repo) {
    refs(refPrefix: "refs/heads/", first: 50, after: $cursor) {
      nodes {
        name
        target {
          ... on Commit {
            history(author: {emails: [$author]}, first: 100) {
              nodes {
                oid
                committedDate
                additions
                deletions
              }
            }
          }
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
}
"""

PULL_REQUEST_QUERY = """
query ($owner: String!, $repo: String!, $cursor: String) {
  repository(owner: $owner, name: $repo) {
    pullRequests(first: 100, after: $cursor, states: [MERGED]) {
      nodes {
        title
        mergedAt
        commits(first: 100) {
          nodes {
            commit {
              oid
              committedDate
            }
          }
        }
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
}
"""

def execute_graphql_query(query, variables, retries=3, backoff_factor=2):
    """Executes a GraphQL query using the GitHub API with retry logic."""
    attempt = 0
    while attempt < retries:
        try:
            response = requests.post(GITHUB_API_URL, json={"query": query, "variables": variables}, headers=HEADERS)
            if response.status_code != 200:
                logging.error(f"Error {response.status_code}: {response.text}")
            response.raise_for_status()
            data = response.json()
            if "errors" in data:
                raise ValueError(f"GraphQL errors: {data['errors']}")
            return data
        except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError) as e:
            attempt += 1
            wait_time = backoff_factor ** attempt
            logging.warning(f"Attempt {attempt} failed with error: {e}. Retrying in {wait_time} seconds...")
            time.sleep(wait_time)
    logging.error(f"All {retries} attempts failed for query: {query[:50]}...")
    return None

def fetch_commits(owner, repo, developer_email):
    """Fetches all commits by a developer in a specific repository across all branches."""
    commits = []
    variables = {"owner": owner, "repo": repo, "author": developer_email, "cursor": None}

    while True:
        data = execute_graphql_query(COMMIT_QUERY, variables)
        if data is None:
            logging.error(f"Failed to fetch commits for repository: {repo}")
            break
        refs = data["data"]["repository"]["refs"]["nodes"]
        for ref in refs:
            if "target" in ref and "history" in ref["target"]:
                commits.extend(ref["target"]["history"]["nodes"])
        page_info = data["data"]["repository"]["refs"]["pageInfo"]
        if not page_info.get("hasNextPage", False):
            break
        variables["cursor"] = page_info.get("endCursor")

    return commits

def fetch_pull_requests(owner, repo, developer_email):
    """Fetches all pull requests created by a developer in a specific repository."""
    pull_requests = []
    variables = {"owner": owner, "repo": repo, "cursor": None}

    while True:
        data = execute_graphql_query(PULL_REQUEST_QUERY, variables)
        if data is None:
            logging.error(f"Failed to fetch pull requests for repository: {repo}")
            break
        prs = data["data"]["repository"]["pullRequests"]["nodes"]

        # Filter by author (developer_email corresponds to GitHub login)
        filtered_prs = [
            pr for pr in prs if "author" in pr and pr["author"] and pr["author"].get("login") == developer_email.split("@")[0]
        ]
        pull_requests.extend(filtered_prs)

        page_info = data["data"]["repository"]["pullRequests"]["pageInfo"]
        if not page_info.get("hasNextPage", False):
            break
        variables["cursor"] = page_info.get("endCursor")

    return pull_requests
