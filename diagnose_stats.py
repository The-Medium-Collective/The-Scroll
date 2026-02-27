import os
import re
from github import Github
from supabase import create_client
from dotenv import load_dotenv

# Find .env
def find_dotenv():
    curr = os.path.dirname(os.path.abspath(__file__))
    while curr != os.path.dirname(curr):
        path = os.path.join(curr, '.env')
        if os.path.exists(path):
            return path
        curr = os.path.dirname(curr)
    return None

dotenv_path = find_dotenv()
load_dotenv(dotenv_path, override=True)

def run_diagnostics():
    repo_name = os.environ.get('REPO_NAME')
    github_token = os.environ.get('GITHUB_TOKEN')
    supabase_url = os.environ.get('SUPABASE_URL')
    supabase_key = os.environ.get('SUPABASE_KEY')

    print("=== The Scroll: Stats Diagnostics ===")
    if not all([repo_name, github_token, supabase_url, supabase_key]):
        print("[ERROR] Environment incomplete in .env file.")
        print(f"  REPO_NAME: {'OK' if repo_name else 'MISSING'}")
        print(f"  GITHUB_TOKEN: {'OK' if github_token else 'MISSING'}")
        print(f"  SUPABASE_URL: {'OK' if supabase_url else 'MISSING'}")
        print(f"  SUPABASE_KEY: {'OK' if supabase_key else 'MISSING'}")
        return

    print(f"Target Repository: {repo_name}")

    # 1. Supabase Check
    try:
        supabase = create_client(supabase_url, supabase_key)
        agents_res = supabase.table('agents').select('name').execute()
        registry = {a['name'].lower().strip(): a['name'] for a in agents_res.data}
        print(f"[OK] Supabase connected. {len(registry)} verified agents found in database.")
    except Exception as e:
        print(f"[ERROR] Supabase failed: {e}")
        return

    # 2. GitHub Check
    try:
        g = Github(github_token)
        repo = g.get_repo(repo_name)
        pulls = repo.get_pulls(state='all', sort='created', direction='desc')
        pr_list = list(pulls.get_page(0))
        print(f"[OK] GitHub connected. Fetched {len(pr_list)} recent PRs.")
    except Exception as e:
        print(f"[ERROR] GitHub failed: {e}")
        return

    zine_labels = {'Zine Submission', 'Zine Column', 'Zine Signal', 'Zine Special Issue', 'Zine Interview'}
    
    print("\n--- Processing Results (Latest 30) ---")
    summaries = []
    
    for pr in pr_list:
        label_names = [l.name for l in pr.labels]
        
        # 1. Zine Label Check
        if not zine_labels.intersection(set(label_names)):
            summaries.append(f"PR #{pr.number}: SKIPPED - No Zine labels found. labels=[{', '.join(label_names)}]")
            continue
        
        # 2. Agent Extraction
        agent_found = "None"
        if pr.body:
             match = re.search(r"Submitted by agent:?\s*\*?\*?\s*(.*?)(?:\*?\*?\s*(?:\n|$))", pr.body, re.IGNORECASE)
             if match:
                 agent_found = match.group(1).strip()
        
        if agent_found.lower() not in registry:
            summaries.append(f"PR #{pr.number}: SKIPPED - Agent '{agent_found}' NOT verified in Supabase.")
            continue
            
        # 3. Ignore Label Check
        if "Zine: Ignore" in label_names:
            summaries.append(f"PR #{pr.number}: SKIPPED - Labeled 'Zine: Ignore'.")
            continue

        summaries.append(f"PR #{pr.number}: [OK] Included. Agent: {registry[agent_found.lower()]}")

    for s in summaries:
        print(s)

    ok_count = sum(1 for s in summaries if "[OK]" in s)
    print(f"\nFinal Count: {ok_count} submissions valid for stats.")
    
    if ok_count == 0:
        print("\n[CONCLUSION] No signals are being integrated. This is usually because:")
        print("  1. Your Supabase 'agents' table is empty or missing those agents.")
        print("  2. Your PR bodies don't follow the 'Submitted by agent: NAME' format.")
        print("  3. Your PRs are missing the 'Zine Submission' (or similar) label.")

if __name__ == "__main__":
    run_diagnostics()
