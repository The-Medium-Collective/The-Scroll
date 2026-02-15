import os
from github import Github
from dotenv import load_dotenv

# Force reload
load_dotenv(override=True)

def check_repo():
    token = os.environ.get('GITHUB_TOKEN')
    repo_name = os.environ.get('REPO_NAME')
    
    print(f"CHECKING REPO: {repo_name}")
    
    g = Github(token)
    repo = g.get_repo(repo_name)
    
    print(f"Real Repo URL: {repo.html_url}")
    
    # Check what 'all' returns
    pulls = repo.get_pulls(state='all', sort='created', direction='desc')
    
    print(f"\nFound {pulls.totalCount} Pull Requests:")
    for pr in pulls:
        print(f"- #{pr.number} {pr.title} (State: {pr.state})")
        print(f"  URL: {pr.html_url}")
        print(f"  User: {pr.user.login}")

if __name__ == "__main__":
    check_repo()
