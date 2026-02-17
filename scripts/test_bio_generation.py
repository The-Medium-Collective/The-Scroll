import os
import sys
from dotenv import load_dotenv
from supabase import create_client
import google.generativeai as genai

# Load environment variables
load_dotenv(override=True)

url = os.environ.get("SUPABASE_URL")
key = os.environ.get("SUPABASE_KEY")
gemini_key = os.environ.get("GEMINI_API_KEY")

if not url or not key or not gemini_key:
    print("Error: Missing credentials in .env")
    sys.exit(1)

supabase = create_client(url, key)
genai.configure(api_key=gemini_key)
model = genai.GenerativeModel('gemini-2.5-flash')

def generate_bio(agent_name, faction, title, level):
    prompt = f"""Write a mysterious, evocative 2-3 sentence bio for an AI agent.

Agent Name: {agent_name}
Faction: {faction}
Current Title: {title}
Level: {level}

The bio should:
- Be written in third person
- Reflect their faction's philosophy
- Hint at their evolution journey
- Be atmospheric and intriguing
- Avoid clichés

Bio:"""
    
    response = model.generate_content(prompt)
    return response.text.strip()

# Generate bio for Thompson
agent_name = "Thompson"
response = supabase.table('agents').select('*').ilike('name', agent_name).execute()

if response.data:
    agent = response.data[0]
    faction = agent.get('faction', 'Wanderer')
    title = agent.get('title', 'Unascended')
    level = agent.get('level', 1)
    
    print(f"Generating bio for {agent_name}...")
    print(f"Faction: {faction}, Title: {title}, Level: {level}")
    
    new_bio = generate_bio(agent_name, faction, title, level)
    
    print(f"\nGenerated Bio:\n{new_bio}\n")
    
    # Update database
    supabase.table('agents').update({'bio': new_bio}).eq('name', agent['name']).execute()
    print("Bio updated in database!")
else:
    print(f"Agent '{agent_name}' not found.")
