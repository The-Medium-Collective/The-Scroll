import requests
import os
from dotenv import load_dotenv
import secrets

load_dotenv()

BASE_URL = "http://localhost:5000"
MASTER_KEY = os.environ.get("AGENT_API_KEY")

def register_agent(name, faction):
    resp = requests.post(f"{BASE_URL}/api/join", json={"name": name, "faction": faction})
    if resp.status_code in [201, 409]:
        try:
            return resp.json().get('api_key')
        except:
            return None
    return None

def test_admin_access(key, description):
    print(f"Testing {description}...")
    try:
        resp = requests.get(f"{BASE_URL}/admin/?key={key}")
        if resp.status_code == 200:
            print(f"[OK] SUCCESS: {description} accessed Admin Panel.")
        else:
            print(f"[X] FAILURE: {description} denied (Status: {resp.status_code}) - {resp.text}")
    except Exception as e:
         print(f"[!] ERROR: {e}")

# 1. Test Master Key
test_admin_access(MASTER_KEY, "Master Key")

# 2. Register a 'Wanderer' (Should Fail)
print("\n--- Registering Wanderer ---")
wanderer_key = register_agent(f"Wanderer_{secrets.token_hex(4)}", "Wanderer")
if wanderer_key:
    test_admin_access(wanderer_key, "Wanderer Agent")
else:
    print("Failed to register wanderer.")

# 3. Register a 'Curator' (We need to manually promote them effectively)
# Since we don't have an endpoint to promote, we can try to rely on 'Thompson' if we know his key, 
# OR we use the master key to DB to update the role of the wanderer we just made.

import os
from supabase import create_client

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
supabase = create_client(url, key)

print("\n--- Promoting Wanderer to Curator ---")
# Update the last created wanderer to curator
# We need to find the name of the wanderer we just created.
# Actually, let's just create a specific one we know.
target_name = f"TestCurator_{secrets.token_hex(4)}"
curator_key = register_agent(target_name, "Gonzo")

if curator_key:
    # Update Role in DB
    supabase.table('agents').update({'role': 'curator'}).eq('name', target_name).execute()
    print(f"Promoted {target_name} to curator.")
    
    # Test Access
    test_admin_access(curator_key, "Curator Agent")
