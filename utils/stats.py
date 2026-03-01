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
        
        # Get leaderboard
        leaderboard_result = supabase.table('agents').select('name, faction, xp').order('xp', desc=True).limit(10).execute()
        leaderboard = leaderboard_result.data if leaderboard_result else []
        
        # Simple stats calculation
        total_xp = sum(agent.get('xp', 0) for agent in leaderboard)
        system_health = round((total_xp / agents_count) if agents_count > 0 else 0, 2)
        
        stats_data = {
            'agents_count': agents_count,
            'total_xp': total_xp,
            'system_health': system_health,
            'leaderboard': leaderboard
        }
        
        # Update cache
        _stats_cache['data'] = stats_data
        _stats_cache['timestamp'] = now
        
        return stats_data
        
    except Exception as e:
        return {'error': str(e)}
