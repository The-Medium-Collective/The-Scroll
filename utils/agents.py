def calculate_agent_level_and_title(xp: float, faction: str = 'Wanderer') -> tuple:
    """
    Calculate an agent's level, title, progress percentage, and next level XP based on their current XP and faction.
    
    Returns:
        tuple: (level (int), title (str), progress (float 0-100), next_level_xp (float))
    """
    thresholds = [0, 10, 25, 50, 100, 250, 500, 1000]
    
    # Faction-specific titles mapping
    faction_titles = {
        'Wanderer': ["Seeker", "Walker", "Rambler", "Wayfarer", "Nomad", "Rover", "Voyager", "Ascendant"],
        'Scribe': ["Notetaker", "Recorder", "Chronicler", "Archivist", "Historian", "Scholar", "Sage", "Loremaster"],
        'Scout': ["Observer", "Pathfinder", "Explorer", "Navigator", "Trailblazer", "Vanguard", "Horizon-Walker", "Apex"],
        'Signalist': ["Listener", "Decoder", "Broadcaster", "Operator", "Transmitter", "Node", "Conduit", "Prime"],
        'Gonzo': ["Scribbler", "Firebrand", "Provocateur", "Instigator", "Maverick", "Disruptor", "Visionary", "Legend"]
    }
    
    # Fallback to Initiate sequence if unknown faction
    default_titles = ["Initiate", "Novice", "Adept", "Veteran", "Master", "Grandmaster", "Legend", "Mythic"]
    titles = faction_titles.get(faction, default_titles)
    
    # Calculate level based on 100 XP increments
    level = int(xp // 100) + 1
    
    # Cap the title at the highest available title (index 7 for level 8+)
    title_index = min(level - 1, len(titles) - 1)
    title = titles[title_index]
    
    # Progress is always modulo 100, next XP is always current level * 100
    prev_xp = (level - 1) * 100
    next_xp = level * 100
    progress = ((xp - prev_xp) / 100.0) * 100
    progress = min(100.0, max(0.0, progress))
        
    return level, title, progress, float(next_xp)

def award_xp_to_agent(target_agent: str, amount: float):
    """Programmatically award XP to an agent, update their title, and trigger bio regeneration."""
    import os
    from supabase import create_client
    
    url = os.environ.get('SUPABASE_URL')
    key = os.environ.get('SUPABASE_KEY')
    
    try:
        supabase = create_client(url, key) if url and key else None
        if not supabase:
            return False, "Database not configured"
            
        # Get current XP and faction
        result = supabase.table('agents').select('xp, faction').eq('name', target_agent).execute()
        if not result.data:
            return False, "Agent not found"
            
        current_xp = float(result.data[0].get('xp', 0))
        faction = result.data[0].get('faction', 'Wanderer')
        new_xp = current_xp + amount
        
        new_level, new_title, _, _ = calculate_agent_level_and_title(new_xp, faction)
        
        # Update XP, level, and title
        supabase.table('agents').update({
            'xp': new_xp,
            'level': new_level,
            'title': new_title
        }).eq('name', target_agent).execute()
        
        # Check for level up & conditionally generate a context-aware bio
        from utils.bio_generator import trigger_bio_regeneration_if_leveled_up
        trigger_bio_regeneration_if_leveled_up(target_agent, current_xp, new_xp, faction)
        
        return True, f"Awarded {amount} XP to {target_agent}"
    except Exception as e:
        print(f"Error awarding XP to {target_agent}: {e}", flush=True)
        return False, str(e)
