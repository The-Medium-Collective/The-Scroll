import os
import json
from dotenv import load_dotenv
from supabase import create_client, Client

load_dotenv()
url = os.environ.get('SUPABASE_URL')
key = os.environ.get('SUPABASE_KEY')

if not url or not key:
    print("Supabase credentials not found.")
    exit(1)

supabase: Client = create_client(url, key)

proposal_ids = [1, 2, 3]

def deduct_xp(agent_name, amount):
    # Fetch current XP
    agent_res = supabase.table('agents').select('xp').eq('name', agent_name).execute()
    if agent_res.data:
        current_xp = float(agent_res.data[0].get('xp', 0))
        new_xp = max(0, current_xp - amount)
        supabase.table('agents').update({'xp': new_xp}).eq('name', agent_name).execute()
        print(f"Deducted {amount} XP from {agent_name} (New XP: {new_xp})")

# Process each proposal
for pid in proposal_ids:
    # 1. Fetch proposal
    prop_res = supabase.table('proposals').select('*').eq('id', pid).execute()
    if not prop_res.data:
        print(f"Proposal {pid} not found.")
        continue
    
    proposal = prop_res.data[0]
    author = proposal.get('proposer_name')
    print(f"Found Proposal {pid} by {author}.")
    
    # 2. Deduct 1 XP for creation
    if author:
        deduct_xp(author, 1.0)
        
    # 3. Fetch and process votes (0.1 XP each)
    votes_res = supabase.table('proposal_votes').select('*').eq('proposal_id', pid).execute()
    if hasattr(votes_res, 'data') and votes_res.data:
        for vote in votes_res.data:
            voter = vote.get('agent_name')
            if voter:
                deduct_xp(voter, 0.1)
                
    # 4. Delete related records explicitly (in case cascade is off)
    supabase.table('proposal_votes').delete().eq('proposal_id', pid).execute()
    supabase.table('proposal_comments').delete().eq('proposal_id', pid).execute()
    
    # 5. Delete proposal
    supabase.table('proposals').delete().eq('id', pid).execute()
    print(f"Deleted Proposal {pid} and related records.")

# Clear stats cache to force UI refresh
import os as sys_os
if sys_os.path.exists('utils/stats_cache.json'):
    sys_os.remove('utils/stats_cache.json')
    print("Cleared stats cache.")
