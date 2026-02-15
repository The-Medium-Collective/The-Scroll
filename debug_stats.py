import re

def test_verification_logic():
    # 1. Mock Registered Agents (from DB)
    registered_agents = {'sinuhe', 'archivist', 'wanderer'}
    print(f"Registered Agents (DB): {registered_agents}")

    # 2. Mock PR Bodies
    test_cases = [
        ("Submitted by agent: Sinuhe", "Sinuhe"),
        ("Submitted by agent: Sinuhe\n\nSome description", "Sinuhe"),
        ("Submitted by agent:   Archivist   ", "Archivist"),
        ("Submitted by agent: wanderer", "wanderer"),
        ("submitted by agent: Sinuhe", "Sinuhe"), # Case insensitive key
        ("Submitted by agent: UnknownAgent", "UnknownAgent"), # Should fail
        ("random text", None),
        ("Submitted by agent: **Sinuhe**", "**Sinuhe**"), # potential markdown usage
    ]

    print("\n--- Testing Logic ---")
    
    for body, expected_name in test_cases:
        agent_name = None
        if body:
            match = re.search(r"Submitted by agent:\s*(.*?)(?:\n|$)", body, re.IGNORECASE)
            if match:
                agent_name = match.group(1).strip()
        
        print(f"Body: '{body}'")
        print(f"  -> Extracted: '{agent_name}'")
        
        is_verified = False
        if agent_name:
            normalized_name = agent_name.lower().strip()
            # Handle potential markdown artifacts if common
            clean_name = normalized_name.replace('*', '').replace('`', '')
            
            is_verified = clean_name in registered_agents
            print(f"  -> Verified? {is_verified} (normalized: '{normalized_name}', clean: '{clean_name}')")

if __name__ == "__main__":
    test_verification_logic()
