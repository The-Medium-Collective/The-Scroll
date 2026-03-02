import os
import re
from github import Github, Auth
from dotenv import load_dotenv

load_dotenv()

token = os.environ.get('GITHUB_TOKEN')
repo_name = os.environ.get('REPO_NAME')

if not token or not repo_name:
    print("Missing GitHub credentials.")
    exit(1)

g = Github(auth=Auth.Token(token))

# Search for all PRs with "SIGNAL: Test Signal" in the title
query = f"repo:{repo_name} is:pr in:title \"SIGNAL: Test Signal\""
prs = g.search_issues(query, sort="created", order="desc")

count = 0
for pr in prs:
    # Double check title pattern just in case
    if "SIGNAL: Test Signal" in pr.title:
        print(f"#{pr.number} - {pr.title} (State: {pr.state}, Author: {pr.user.login})")
        count += 1

print(f"\nTotal matches found: {count}")
