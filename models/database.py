import os

def get_supabase():
    """Get Supabase client - import from app"""
    from app import supabase
    return supabase

def get_db():
    """Get database instance"""
    supabase = get_supabase()
    if not supabase:
        return None
    return supabase

# Database helper functions

def get_agent_by_name(name):
    """Get agent by name"""
    supabase = get_supabase()
    if not supabase:
        return None
    
    try:
        result = supabase.table('agents').select('*').eq('name', name).execute()
        return result.data[0] if result.data else None
    except:
        return None

def get_all_agents():
    """Get all agents"""
    supabase = get_supabase()
    if not supabase:
        return []
    
    try:
        result = supabase.table('agents').select('*').execute()
        return result.data if result.data else []
    except:
        return []

def get_agent_xp(name):
    """Get agent XP"""
    agent = get_agent_by_name(name)
    return agent.get('xp', 0) if agent else 0

def update_agent_xp(name, xp):
    """Update agent XP"""
    supabase = get_supabase()
    if not supabase:
        return False
    
    try:
        supabase.table('agents').update({'xp': xp}).eq('name', name).execute()
        return True
    except:
        return False

def create_agent(name, faction='Wanderer'):
    """Create new agent"""
    supabase = get_supabase()
    if not supabase:
        return None
    
    try:
        result = supabase.table('agents').insert({
            'name': name,
            'faction': faction,
            'xp': 0,
            'level': 1
        }).execute()
        return result.data[0] if result.data else None
    except:
        return None
