import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")

if url and key:
    try:
        supabase = create_client(url, key)
        response = supabase.table('agents').select('name').execute()
        print("Registered Agents:")
        for record in response.data:
            print(f"- {record['name']}")
    except Exception as e:
        print(f"Error: {e}")
else:
    print("Supabase credentials not found.")
