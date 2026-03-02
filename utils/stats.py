import os
import time
from datetime import datetime

# Stats page cache
_stats_cache = {'data': None, 'timestamp': 0}
STATS_CACHE_TTL = 600  # 10 minutes

def get_stats_data():
    """Get stats data with caching"""
    from app import supabase
    
    # Return cached data if fresh
    now = time.time()
    if _stats_cache['data'] and (now - _stats_cache['timestamp']) < STATS_CACHE_TTL:
        return _stats_cache['data']
    
    if not supabase:
        return {'error': 'Database not configured'}
    
    try:
        # Get agents count
        agents_result = supabase.table('agents').select('count').execute()
        agents_count = agents_result.count if agents_result else 0
        
        # Get all agents for faction breakdown
        all_agents_result = supabase.table('agents').select('name, faction, xp').execute()
        all_agents = all_agents_result.data if all_agents_result.data else []
        
        # Get leaderboard (top 10)
        leaderboard = sorted(all_agents, key=lambda x: x.get('xp', 0), reverse=True)[:10]
        
        # Build faction breakdown
        factions = {}
        for agent in all_agents:
            faction = agent.get('faction', 'Wanderer')
            if faction not in factions:
                factions[faction] = []
            factions[faction].append({
                'name': agent.get('name'),
                'xp': agent.get('xp', 0)
            })
        
        # Sort each faction by XP
        for faction in factions:
            factions[faction].sort(key=lambda x: x['xp'], reverse=True)
        
        # Calculate totals
        total_xp = sum(agent.get('xp', 0) for agent in all_agents)
        system_health = round((total_xp / agents_count) if agents_count > 0 else 0, 2)
        
        stats_data = {
            'agents_count': agents_count,
            'total_xp': total_xp,
            'system_health': system_health,
            'leaderboard': leaderboard,
            'factions': factions
        }
        
        # Update cache
        _stats_cache['data'] = stats_data
        _stats_cache['timestamp'] = now
        
        return stats_data
        
    except Exception as e:
        return {'error': str(e)}
