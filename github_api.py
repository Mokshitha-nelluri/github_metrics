import requests
import time
import logging

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class GitHubAPI:
    """Handles communication with the GitHub GraphQL API."""

    def __init__(self, token):
        self.api_url = "https://api.github.com/graphql"
        self.headers = {"Authorization": f"Bearer {token}"}

    def execute_query(self, query, variables, retries=3, backoff_factor=2):
        """Executes a GraphQL query with retry logic."""
        attempt = 0
        while attempt < retries:
            try:
                response = requests.post(self.api_url, json={"query": query, "variables": variables}, headers=self.headers)
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
        logging.error("All retries failed.")
        return None

    def fetch_commits(self, owner, repo, developer_email):
      """Fetches all commits by a developer in a specific repository."""
      query = """
      query ($owner: String!, $repo: String!, $author_email: String!, $cursor: String) {
        repository(owner: $owner, name: $repo) {
          refs(refPrefix: "refs/heads/", first: 50, after: $cursor) {
            nodes {
              name
              target {
                ... on Commit {
                  history(author: {emails: [$author_email]}, first: 100) {
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
      variables = {"owner": owner, "repo": repo, "cursor": None, "author_email": developer_email}
      commits = []

      while True:
          data = self.execute_query(query, variables)
          if data is None:
              logging.error(f"Failed to fetch commits for {repo}")
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


    def fetch_pull_requests(self, owner, repo, developer_email):
      """Fetches all pull requests created by a developer in a specific repository."""
      query = """
      query ($owner: String!, $repo: String!, $cursor: String) {
        repository(owner: $owner, name: $repo) {
          pullRequests(first: 100, after: $cursor, states: [MERGED]) {
            nodes {
              title
              author {
                login
              }
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
      variables = {"owner": owner, "repo": repo, "cursor": None}
      pull_requests = []

      while True:
          data = self.execute_query(query, variables)
          if data is None:
              logging.error(f"Failed to fetch pull requests for repository: {repo}")
              break
          prs = data["data"]["repository"]["pullRequests"]["nodes"]

          # Safely filter by author (developer_email corresponds to GitHub login)
          filtered_prs = [
              pr for pr in prs if pr.get("author") and pr["author"].get("login") == developer_email.split("@")[0]
          ]
          pull_requests.extend(filtered_prs)

          page_info = data["data"]["repository"]["pullRequests"]["pageInfo"]
          if not page_info.get("hasNextPage", False):
              break
          variables["cursor"] = page_info.get("endCursor")

      return pull_requests
