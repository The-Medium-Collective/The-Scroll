import os
from supabase import create_client
from dotenv import load_dotenv

load_dotenv()

def reset_database():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")

    if not url or not key:
        print("Supabase credentials not found in .env")
        return

    supabase = create_client(url, key)

    print("WARNING: This will delete ALL agents from the database.")
    print("Deleting...")
    
    # Supabase Python client delete syntax
    try:
        # Delete all rows (neq 0 is a workaround to select all/delete all if no other filter exists)
        # Or simpler: just list all, then delete by ID
        
        # Method 1: Delete everything
        data = supabase.table("agents").delete().neq("id", 0).execute()
        print(f"Deleted {len(data.data)} agents.")
        
    except Exception as e:
        print(f"Error resetting database: {e}")

if __name__ == "__main__":
    reset_database()
