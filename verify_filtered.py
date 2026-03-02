import os
import json
from github import Github, Auth
from dotenv import load_dotenv

load_dotenv()

token = os.environ.get('GITHUB_TOKEN')
repo_name = os.environ.get('REPO_NAME')

if not token or not repo_name:
    print("Missing GitHub credentials.")
    exit(1)

g = Github(auth=Auth.Token(token))

print("Fetching all PRs that match the criteria for 'Filtered':")
print("Query: is:pr is:closed -is:merged -label:\"Zine: Ignore\"")

query = f"repo:{repo_name} is:pr is:closed -is:merged -label:\"Zine: Ignore\""
prs = g.search_issues(query, sort="created", order="desc")

print(f"\nTotal matches found: {prs.totalCount}\n")

for pr in prs:
    print(f"#{pr.number} - {pr.title} (Author: {pr.user.login})")
