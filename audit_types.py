import os
import json
from github import Github, Auth
from dotenv import load_dotenv

load_dotenv()

token = os.environ.get('GITHUB_TOKEN')
repo_name = os.environ.get('REPO_NAME')

g = Github(auth=Auth.Token(token))

def get_count(q):
    return g.search_issues(f"repo:{repo_name} is:pr {q}").totalCount

stats = {
    'merged_submissions': get_count("is:merged label:\"Zine Submission\""),
    'open_submissions': get_count("is:open label:\"Zine Submission\""),
    'open_signals': get_count("is:open label:\"Zine Signal\""),
    'open_no_label': get_count("is:open -label:\"Zine Submission\" -label:\"Zine Signal\" -label:\"Zine Column\" -label:\"Zine Special Issue\" -label:\"Zine Interview\""),
}

print(json.dumps(stats, indent=2))
