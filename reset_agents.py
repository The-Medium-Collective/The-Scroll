import os
import uuid
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

if url and key:
    try:
        supabase = create_client(url, key)
        
        # 1. Delete all existing agents
        # Note: supbase-py doesn't support delete without filter easily, usually need a condition.
        # We'll fetch all IDs first then delete them.
        print("Fetching existing agents...")
        response = supabase.table('agents').select('id').execute()
        if response.data:
            ids = [record['id'] for record in response.data]
            print(f"Deleting {len(ids)} agents...")
            for agent_id in ids:
                 supabase.table('agents').delete().eq('id', agent_id).execute()
            print("Agents deleted.")
        else:
            print("No existing agents found.")

        # 2. Insert TestBot
        print("Inserting 'TestBot'...")
        api_key = uuid.uuid4().hex
        supabase.table('agents').insert({
            'name': 'TestBot',
            'api_key': api_key,
            'faction': 'System'
        }).execute()
        
        print(f"Success! Agent 'TestBot' created with API Key: {api_key}")
        
    except Exception as e:
        print(f"Error: {e}")
else:
    print("Supabase credentials not found.")
