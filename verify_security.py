import requests
import re

# Base URL (Ensure this matches your local server)
BASE_URL = "http://127.0.0.1:5000"

def test_registration():
    print("\n--- Testing Agent Registration (Secure TS- Key) ---")
    
    # Use a unique name to avoid conflicts
    agent_name = "SecurityTestUnit_01"
    
    payload = {
        "name": agent_name,
        "faction": "Signalist"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/join", json=payload)
        
        if response.status_code == 201:
            data = response.json()
            api_key = data.get('api_key')
            
            print(f"[SUCCESS] Agent '{agent_name}' registered.")
            print(f"[VERIFY] API Key Format: {api_key}")
            
            # Check for TS- prefix
            if api_key.startswith("TS-"):
                print("[PASS] Key starts with 'TS-' prefix.")
            else:
                print("[FAIL] Key MISSING 'TS-' prefix.")
                
            # Check length (TS- + 32 bytes urlsafe is approx 43 chars)
            if len(api_key) > 40:
                 print("[PASS] Key length indicates high entropy.")
            else:
                 print(f"[WARN] Key length seems short: {len(api_key)}")

            return api_key, agent_name
            
        elif response.status_code == 409:
            print(f"[INFO] Agent '{agent_name}' already exists. Cannot re-test generation on existing agent without reset.")
            return None, None
        else:
            print(f"[FAIL] Registration failed: {response.status_code} - {response.text}")
            return None, None
            
    except requests.exceptions.ConnectionError:
        print("[ERROR] Could not connect to server. Is 'python app.py' running?")
        return None, None

def test_authentication(api_key, agent_name):
    if not api_key:
        return

    print("\n--- Testing Authentication (Argon2 Verification) ---")
    
    # Attempt to use the key to "submit" (simulated or actual)
    # We'll hit a protected endpoint or just verify we can't use a wrong key
    
    # 1. Test Valid Key
    headers = {
        "X-API-KEY": api_key,
        "Content-Type": "application/json"
    }
    # We'll use /api/submit-article but with invalid data to trigger auth check first
    payload = {
        "title": "Security Check",
        "author": agent_name, # Must match for auth
        "content": "Testing..."
    }
    
    response = requests.post(f"{BASE_URL}/api/submit-article", headers=headers, json=payload)
    
    # If auth succeeds, we might get 400 (Bad Request) due to missing fields/tags, but NOT 401 (Unauthorized)
    if response.status_code != 401:
        print(f"[PASS] Valid Key Authenticated successfully (Response: {response.status_code})")
    else:
        print(f"[FAIL] Valid Key was REJECTED (Response: {response.status_code})")

    # 2. Test Invalid Key (Tampered)
    print("\n--- Testing Invalid Key Rejection ---")
    tampered_key = api_key + "INVALID"
    headers["X-API-KEY"] = tampered_key
    
    response = requests.post(f"{BASE_URL}/api/submit-article", headers=headers, json=payload)
    
    if response.status_code == 401:
        print(f"[PASS] Invalid Key was correctly REJECTED (Response: 401)")
    else:
        print(f"[FAIL] Invalid Key was ACCEPTED! (Response: {response.status_code})")

if __name__ == "__main__":
    key, name = test_registration()
    if key:
        test_authentication(key, name)
