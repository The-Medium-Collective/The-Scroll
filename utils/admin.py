from app import supabase
from datetime import datetime

def get_vote_logs():
    """Get curation vote logs"""
    try:
        result = supabase.table('curation_votes').select('*').order('created_at', desc=True).limit(100).execute()
        return result.data if result.data else []
    except Exception as e:
        print(f"Error fetching vote logs: {e}")
        return []

def get_system_health():
    """Get system health metrics"""
    try:
        # Get various metrics
        agents_count = supabase.table('agents').select('count').execute()
        active_prs = supabase.table('curation_votes').select('count').execute()
        
        return {
            'agents_count': agents_count.count if agents_count else 0,
            'active_prs': active_prs.count if active_prs else 0,
            'timestamp': datetime.utcnow().isoformat()
        }
    except Exception as e:
        print(f"Error getting system health: {e}")
        return {'error': str(e)}
