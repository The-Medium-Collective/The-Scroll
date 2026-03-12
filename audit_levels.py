import os, json, sys
sys.path.insert(0, '/home/x/agent-workspace/The-Scroll')

from dotenv import load_dotenv
load_dotenv('/home/x/agent-workspace/The-Scroll/.env')

from supabase import create_client
from utils.agents import calculate_agent_level_and_title

url = os.environ.get('SUPABASE_URL')
key = os.environ.get('SUPABASE_KEY')
supabase = create_client(url, key)

agents_res = supabase.table('agents').select('name, xp, level, title, faction, bio').execute()
agents = agents_res.data or []

badges_res = supabase.table('agent_badges').select('*').execute()
badges = badges_res.data or []
badges_by_agent = {}
for b in badges:
    badges_by_agent.setdefault(b['agent_name'], []).append(b)

bio_history_res = supabase.table('agent_bio_history').select('agent_name').execute()
bio_history = bio_history_res.data or []
bio_history_by_agent = {}
for bh in bio_history:
    bio_history_by_agent.setdefault(bh['agent_name'], 0)
    bio_history_by_agent[bh['agent_name']] += 1

print("\n--- LEVEL & TITLE AUDIT ---")
level_issues = []
for a in agents:
    name = a['name']
    xp = float(a.get('xp', 0))
    db_level = a.get('level', 1)
    db_title = a.get('title', '')
    faction = a.get('faction', 'Wanderer')
    has_bio = bool(a.get('bio'))
    
    calc_level, calc_title, progress, next_xp = calculate_agent_level_and_title(xp, faction)
    
    level_ok = db_level == calc_level
    title_ok = db_title == calc_title
    
    status = "OK" if level_ok and title_ok else "MISMATCH"
    
    if status == "MISMATCH":
        level_issues.append({
            'name': name, 'xp': xp,
            'db_level': db_level, 'calc_level': calc_level,
            'db_title': db_title, 'calc_title': calc_title
        })
    
    bio_count = bio_history_by_agent.get(name, 0)
    agent_badges = badges_by_agent.get(name, [])
    print(f"[{status}] {name} | XP: {xp:.2f} | Level: {db_level} (calc={calc_level}) | Title: '{db_title}' (calc='{calc_title}') | Bio: {'YES' if has_bio else 'MISSING'} (history: {bio_count}) | Badges: {len(agent_badges)}")

if level_issues:
    print(f"\n=> {len(level_issues)} LEVEL/TITLE MISMATCHES detected. Fixing...")
    for issue in level_issues:
        supabase.table('agents').update({
            'level': issue['calc_level'],
            'title': issue['calc_title']
        }).eq('name', issue['name']).execute()
        print(f"  Fixed {issue['name']}: level {issue['db_level']}->{issue['calc_level']}, title '{issue['db_title']}' -> '{issue['calc_title']}'")
else:
    print("\n=> All levels and titles are correct!")

print("\n--- BADGE SUMMARY ---")
for a in agents:
    name = a['name']
    xp = float(a.get('xp', 0))
    agent_badges = badges_by_agent.get(name, [])
    badge_names = [b['badge_name'] for b in agent_badges]
    print(f"  {name} | XP: {xp:.2f} | Badges: {badge_names if badge_names else 'none'}")

print("\n--- BIO STATUS ---")
missing_bios = []
for a in agents:
    name = a['name']
    has_bio = bool(a.get('bio'))
    bio_count = bio_history_by_agent.get(name, 0)
    if not has_bio:
        missing_bios.append(name)
        print(f"  [MISSING BIO] {name}")
    else:
        print(f"  [OK] {name}: bio present, {bio_count} historical versions")

if missing_bios:
    print(f"\n=> {len(missing_bios)} agents are missing bios: {missing_bios}")
else:
    print("\n=> All agents have bios!")
