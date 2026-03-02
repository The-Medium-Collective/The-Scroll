import os
import json
from github import Github, Auth
from dotenv import load_dotenv

load_dotenv()

token = os.environ.get('GITHUB_TOKEN')
repo_name = os.environ.get('REPO_NAME')

g = Github(auth=Auth.Token(token))
repo = g.get_repo(repo_name)

def get_count(q):
    return g.search_issues(f"repo:{repo_name} is:pr {q}").totalCount

counts = {
    'integrated': get_count("is:merged -label:\"Zine: Ignore\""),
    'active': get_count("is:open -label:\"Zine: Ignore\""),
    'filtered': get_count("is:closed -is:merged -label:\"Zine: Ignore\"")
}

print(json.dumps(counts, indent=2))
