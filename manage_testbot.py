import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

if url and key:
    try:
        supabase = create_client(url, key)
        
        # Check TestBot
        response = supabase.table('agents').select('*').eq('name', 'TestBot').execute()
        if response.data:
            agent = response.data[0]
            print(f"Current TestBot Faction: {agent.get('faction')}")
            
            if agent.get('faction') != 'System':
                print("Updating TestBot to 'System'...")
                supabase.table('agents').update({'faction': 'System'}).eq('name', 'TestBot').execute()
                print("Update complete.")
            else:
                print("TestBot is already 'System'.")
        else:
            print("TestBot not found.")
            
    except Exception as e:
        print(f"Error: {e}")
else:
    print("Supabase credentials not found.")
