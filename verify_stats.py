import requests

try:
    response = requests.get('http://127.0.0.1:5001/stats')
    print(f"Status: {response.status_code}")
    content = response.text
    print(f"Length: {len(content)}")
    
    if "No signals detected" in content:
        print("SUCCESS: Found 'No signals detected' message.")
    else:
        print("FAIL: 'No signals detected' NOT found.")
        
    if "Sinuhe420" in content:
        print("FAIL: Found 'Sinuhe420' (Old Repo).")
    else:
        print("SUCCESS: 'Sinuhe420' NOT found.")
        
    # Save to file just in case
    with open('stats_verification_py.html', 'w', encoding='utf-8') as f:
        f.write(content)

except Exception as e:
    print(f"Error: {e}")
