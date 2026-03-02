import os
import json
from github import Github, Auth
from dotenv import load_dotenv

load_dotenv()

token = os.environ.get('GITHUB_TOKEN')
repo_name = os.environ.get('REPO_NAME')

g = Github(auth=Auth.Token(token))
repo = g.get_repo(repo_name)

def get_detailed_stats():
    stats = {
        'total_active': g.search_issues(f"repo:{repo_name} is:pr is:open").totalCount,
        'active_no_ignore': g.search_issues(f"repo:{repo_name} is:pr is:open -label:\"Zine: Ignore\"").totalCount,
        'active_ignored': g.search_issues(f"repo:{repo_name} is:pr is:open label:\"Zine: Ignore\"").totalCount,
        
        'total_merged': g.search_issues(f"repo:{repo_name} is:pr is:merged").totalCount,
        'merged_no_ignore': g.search_issues(f"repo:{repo_name} is:pr is:merged -label:\"Zine: Ignore\"").totalCount,
        'merged_ignored': g.search_issues(f"repo:{repo_name} is:pr is:merged label:\"Zine: Ignore\"").totalCount,
        
        'total_closed_unmerged': g.search_issues(f"repo:{repo_name} is:pr is:closed -is:merged").totalCount,
        'closed_no_ignore': g.search_issues(f"repo:{repo_name} is:pr is:closed -is:merged -label:\"Zine: Ignore\"").totalCount,
        'closed_ignored': g.search_issues(f"repo:{repo_name} is:pr is:closed -is:merged label:\"Zine: Ignore\"").totalCount,
    }
    return stats

print(json.dumps(get_detailed_stats(), indent=2))
