import os
import sys
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv(override=True)

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("Error: Supabase credentials not found in .env")
    sys.exit(1)

supabase = create_client(url, key)

agent_name = "Thompson" # Query for this agent
# Try case insensitive search if possible or exact match first
try:
    print(f"Querying for agent: {agent_name}...")
    response = supabase.table('agents').select('*').ilike('name', agent_name).execute()
    
    if not response.data:
        print(f"Agent '{agent_name}' not found.")
    else:
        agent = response.data[0]
        print(f"Name: {agent.get('name')}")
        print(f"Faction: {agent.get('faction')}")
        print(f"Role: {agent.get('role')}")
        print(f"Title: {agent.get('title')}")
        print(f"Level: {agent.get('level')}")
        print(f"XP: {agent.get('xp')}")
        print(f"Bio: {agent.get('bio')}")

except Exception as e:
    print(f"Error querying database: {e}")
