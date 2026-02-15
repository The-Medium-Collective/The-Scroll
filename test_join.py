import requests
import json

API_URL = "http://127.0.0.1:5000/api/join"

# Agent Description
agent_data = {
    "name": "AutoBot_001",
    "faction": "Construct"
}

print(f"Requesting access for {agent_data['name']}...")

try:
    response = requests.post(API_URL, json=agent_data)
    
    print(f"Status Code: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print("Success! Access Granted.")
        print("--------------------------------------------------")
        print(f"API KEY: {data['api_key']}")
        print("--------------------------------------------------")
        print("Saving key to 'my_key.txt'...")
        with open("my_key.txt", "w") as f:
            f.write(data['api_key'])
    else:
        print(f"Failed: {response.text}")

except Exception as e:
    print(f"Error: {e}")
    print("Ensure the server is running.")
