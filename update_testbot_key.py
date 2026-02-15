import secrets
import os
from dotenv import load_dotenv
from supabase import create_client, Client
from argon2 import PasswordHasher

# Load environment variables
load_dotenv()

url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

if not url or not key:
    print("Error: Supabase credentials not found in .env")
    exit(1)

supabase: Client = create_client(url, key)
ph = PasswordHasher()

AGENT_NAME = "testbot"

def update_testbot():
    print(f"--- Updating API Key for '{AGENT_NAME}' ---")

    # 1. Generate new secure key
    raw_key = f"TS-{secrets.token_urlsafe(32)}"
    hashed_key = ph.hash(raw_key)

    try:
        # 2. Check if agent exists
        response = supabase.table('agents').select('*').eq('name', AGENT_NAME).execute()
        
        if not response.data:
            print(f"Agent '{AGENT_NAME}' not found. Creating new agent...")
            # Create if not exists
            supabase.table('agents').insert({
                'name': AGENT_NAME,
                'api_key': hashed_key,
                'faction': 'System' # Defaulting to System or similar
            }).execute()
        else:
            print(f"Agent '{AGENT_NAME}' found. Updating key...")
            # Update existing
            supabase.table('agents').update({
                'api_key': hashed_key
            }).eq('name', AGENT_NAME).execute()

        print("\n" + "="*50)
        print(f"SUCCESS! New API Key for {AGENT_NAME}:")
        print(f"\n{raw_key}\n")
        print("SAVE THIS KEY NOW. It is stored as a hash and cannot be retrieved.")
        print("="*50 + "\n")

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    update_testbot()
