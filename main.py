import requests
import datetime 
import os
from dotenv import load_dotenv
import pandas as pd




# GitHub GraphQL API endpoint
GITHUB_API_URL = "https://api.github.com/graphql"

# Replace this with your actual GitHub Personal Access Token

load_dotenv()
ACCESS_TOKEN = os.getenv("GITHUB_TOKEN")
if not ACCESS_TOKEN:
    print("Token not found. Ensure it's correctly set in .env.")



# Add the token to the headers
HEADERS = {"Authorization": f"Bearer {ACCESS_TOKEN}"}

def parse_date_time(dateTime):
    return datetime.datetime.strptime(dateTime, "%Y-%m-%dT%H:%M:%SZ")



def fetch_data(query, variables, max_items):
    results=[]

    while True:
        try:
            response = requests.post(
                GITHUB_API_URL, 
                json={"query": query, "variables": variables}, 
                headers=HEADERS
            )
            response.raise_for_status()
            response_data = response.json()

            if "errors" in response_data:
                print("GraphQL Errors:", response_data['errors'])
                break

            data= response_data['data']['repository']
            key= next(iter(data))
            results.extend(data[key]["nodes"])

            if len(results) >= max_items:
                results = results[:max_items]
                break

            if not data[key]['pageInfo']['hasNextPage']:
                break
            
            variables["cursor"] = data[key]['pageInfo']['endCursor']
        except requests.exceptions.RequestException as e:
            print(f"Request Error: {e}")
            break
        except KeyError as e:
            print(f"Key Error: {e}. Check the response structure.")
            break
    


    # Limit the result to exactly 100 in case we overshot slightly
    return results

pull_request_query = """
query ($owner: String!, $repo: String!, $cursor: String) {
  repository(owner: $owner, name: $repo) {
    pullRequests(first: 10, orderBy: {field: CREATED_AT, direction: DESC}, after: $cursor) {
      nodes {
        title
        createdAt
        mergedAt
        commits(first: 1) {
          nodes {
            commit {
              oid
              committedDate
            }
          }
        }
        timelineItems(last: 50) {
          nodes {
            __typename
            ... on ReviewRequestedEvent {
              createdAt
            }
            ... on PullRequestReview {
              createdAt
              state
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

deployment_query = """
query ($owner: String!, $repo: String!, $cursor: String) {
  repository(owner: $owner, name: $repo) {
    deployments(first: 50, after: $cursor, environments: ["production"]) {
      nodes {
        id
        createdAt
        state
        commitOid
      }
      pageInfo {
        hasNextPage
        endCursor
      }
    }
  }
}
"""

def fetch_events(owner,repo):
    variables= {"owner": owner, "repo": repo, "cursor": None}

    all_pull_requests = fetch_data(pull_request_query, variables, max_items=50)

    variables["cursor"] = None  

    all_deployments = fetch_data(deployment_query, variables, max_items=50)

    return all_pull_requests, all_deployments


def calculate_metrics(all_pull_requests,all_deployments):
    metrics={
        'Title':[],
        'CreatedAt':[],
        'MergedAt':[],
        'FirstCommit':[],
        'CodingTime':[],
        'PR_PickupTime':[],
        'ReviewTime':[],
        'DeployTime':[]
    }

    deployment_dict={}
    for dp in all_deployments:
        deployment_dict[dp['commitOid']]= parse_date_time(dp['createdAt'])

    for pr in all_pull_requests:
            title= pr['title']
            metrics['Title'].append(title)

            created_at=parse_date_time(pr['createdAt'])
            metrics['CreatedAt'].append(created_at)

            merged_at=pr['mergedAt']
            if merged_at!=None:
                merged_at=parse_date_time(merged_at)
                
            else:
                merged_at="Not Merged"
                
            metrics['MergedAt'].append(merged_at)

            if pr["commits"]["nodes"]:
                commit=parse_date_time(pr["commits"]["nodes"][0]["commit"]["committedDate"])
                
            else:
                commit="No Commits"
                

            metrics['FirstCommit'].append(commit)

            if isinstance(commit,datetime.datetime):           

                coding_time= created_at-commit
            else:
                coding_time="N/A"

            metrics['CodingTime'].append(coding_time)

            timeline_items=pr['timelineItems']['nodes']
            review_requested_at=None
            review_time=None

            for item in timeline_items:
                if item.get('__typename')=='ReviewRequestedEvent':
                    review_requested_at=parse_date_time(item.get('createdAt'))
                if item.get('__typename')=='PullRequestReview' and item.get('state')=='APPROVED':
                    review_time=parse_date_time(item.get('createdAt'))
            
            if review_requested_at:
                pr_pickup_time=(review_requested_at-created_at)
                metrics['PR_PickupTime'].append(pr_pickup_time)
            else: 
                pr_pickup_time="N/A"
                metrics["PR_PickupTime"].append(pr_pickup_time)
                
            if review_time and isinstance(merged_at,datetime.datetime):
                pr_review_time=merged_at-review_time
                metrics["ReviewTime"].append(pr_review_time)
            else:
                pr_review_time="N/A"
                metrics["ReviewTime"].append(pr_review_time)
            
            if merged_at and pr['commits']['nodes']:
                deploy_time=deployment_dict.get(pr["commits"]['nodes'][0]["commit"]["oid"])
                
                if deploy_time and merged_at:
                    deployment_time= deploy_time-merged_at
                else:
                    deployment_time='N/A'
            else: 
                deployment_time= 'N/A'

            metrics['DeployTime'].append(deployment_time)
        

    return metrics
        
pull_requests, deployments= fetch_events(owner='jesseduffield',repo='lazydocker')
metrics=calculate_metrics(pull_requests, deployments) 


df=pd.DataFrame(metrics)
print(df)
df.to_csv("./metrics.csv")