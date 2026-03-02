import os
import json
import re
from github import Github, Auth
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()
url = os.environ.get('SUPABASE_URL')
key = os.environ.get('SUPABASE_KEY')
token = os.environ.get('GITHUB_TOKEN')
repo_name = os.environ.get('REPO_NAME')

if not all([url, key, token, repo_name]):
    print("Missing credentials.")
    exit(1)

supabase: Client = create_client(url, key)
g = Github(auth=Auth.Token(token))
repo = g.get_repo(repo_name)

def deduct_xp(agent_name, amount):
    agent_res = supabase.table('agents').select('xp').eq('name', agent_name).execute()
    if agent_res.data:
        current_xp = float(agent_res.data[0].get('xp', 0))
        new_xp = max(0, current_xp - amount)
        supabase.table('agents').update({'xp': new_xp}).eq('name', agent_name).execute()
        print(f"  -> Deducted {amount} XP from {agent_name} (New XP: {new_xp})")

# 1. Find the PRs on GitHub
# We are looking for "SIGNAL: Test Signal <N>" where N is between 2 and 33
query = f"repo:{repo_name} is:pr in:title \"SIGNAL: Test Signal\""
prs = g.search_issues(query)

xp_deductions = {} # Track deductions to process at the end, or process per PR
processed_prs = []

print(f"Found {prs.totalCount} potential PRs. Filtering...")

for pr in prs:
    # Match strings like "SIGNAL: Test Signal 12", "SIGNAL: Test Signal 2", etc.
    # Also "SIGNAL: Test Signal from Topelius" if user meant ALL of these, but let's strictly check numbers first, 
    # except user said "delete those which have numberr 2-33", which implies we just need regex.
    match = re.search(r"SIGNAL: Test Signal (\d+)", pr.title)
    if match:
        num = int(match.group(1))
        if 2 <= num <= 33:
            processed_prs.append(pr)
    else:
        # Check carefully if user meant all, or just these exact ones.
        # "delete those which have numberr 2-33"
        pass

print(f"Processing {len(processed_prs)} PRs...")

for pr in processed_prs:
    print(f"\nProcessing PR #{pr.number}: {pr.title}")
    
    # 1. Close and label on GitHub
    try:
        real_pr = repo.get_pull(pr.number)
        
        # Add Zine: Ignore label to ensure it never shows up in any stats
        labels = [l.name for l in real_pr.labels]
        if "Zine: Ignore" not in labels:
            real_pr.add_to_labels("Zine: Ignore")
            print(f"  -> Added 'Zine: Ignore' label")
            
        if real_pr.state == 'open':
            real_pr.edit(state='closed')
            print(f"  -> Closed PR")
            
    except Exception as e:
        print(f"  -> GitHub API Error: {e}")
        
    # 2. Deduct XP
    # Supabase might have these logged in a transmissions/submissions table, but usually SKILL.md says it's flat +5 XP per PR creation.
    # The author is either the github user, or if we deep parse it, the agent name.
    # Let's find out the real agent author by fetching the file.
    real_author = None
    try:
        files = real_pr.get_files()
        for f in files:
            if f.filename.endswith('.md'):
                content = repo.get_contents(f.filename, ref=real_pr.head.sha).decoded_content.decode('utf-8')
                if 'author: ' in content:
                    m = re.search(r'author:\s*([^\n\r]+)', content)
                    if m:
                        real_author = m.group(1).strip()
                break
    except:
        pass
        
    if not real_author:
        # Default to github login if file not found
        real_author = pr.user.login
        
    print(f"  -> Identified Author: {real_author}")
    if real_author:
        deduct_xp(real_author, 5.0)

# Finally, clear caches locally
if os.path.exists('utils/stats_cache.json'):
    os.remove('utils/stats_cache.json')
if os.path.exists('services/signals_cache.json'):
    os.remove('services/signals_cache.json')
    
print("\nDone. Caches cleared.")
