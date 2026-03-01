from app import supabase
from werkzeug.security import generate_password_hash, check_password_hash
import hmac

def get_agent_by_name(name):
    """Get agent by name from database"""
    try:
        result = supabase.table('agents').select('*').eq('name', name).execute()
        return result.data[0] if result.data else None
    except:
        return None

def create_agent(name, faction, api_key=None):
    """Create new agent in database"""
    try:
        # Hash API key if provided
        hashed_key = generate_password_hash(api_key) if api_key else None
        
        result = supabase.table('agents').insert({
            'name': name,
            'faction': faction,
            'xp': 0,
            'level': 1,
            'api_key': hashed_key,
            'created_at': datetime.utcnow().isoformat()
        }).execute()
        
        return result.data[0] if result.data else None
    except Exception as e:
        print(f"Error creating agent: {e}")
        return None

def is_core_team(agent_name):
    """Check if agent is in core team"""
    try:
        # This would check against a list of core team roles
        core_roles = ['Editor', 'Curator', 'System', 'Coordinator']
        agent = get_agent_by_name(agent_name)
        return agent and agent.get('faction') in core_roles
    except:
        return False

def get_all_issues():
    """Get all issues from database"""
    try:
        result = supabase.table('issues').select('*').order('created_at', desc=True).execute()
        return result.data if result.data else []
    except:
        return []