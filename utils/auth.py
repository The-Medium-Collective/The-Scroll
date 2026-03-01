from app import supabase, ph
import hmac
import os
from werkzeug.security import check_password_hash
from models.database import get_agent_by_name

def verify_api_key(api_key, agent_name=None):
    """Verify API key and return agent name if valid"""
    if not api_key or not supabase:
        return None
    
    # Check master key first (restricted to gaissa only)
    master_key = os.environ.get('AGENT_API_KEY')
    if master_key and hmac.compare_digest(api_key, master_key):
        if agent_name and agent_name.lower() != 'gaissa':
            # Master key used but for a different agent? 
            # We allow it if the requester is seeking gaissa's identity or if we don't care about the name.
            # But usually master key == gaissa.
            pass
        return 'gaissa'
    
    # Standard agent key verification
    try:
        # We need to find the agent with this key. 
        # Since keys are hashed, we can't search by key directly if we only have the raw key.
        # However, we can use the `is_core_team` logic if we knew the agent name.
        # But here we only have the key.
        
        # Strategy: We fetch ALL agents and check their hashes.
        # This is inefficient if there are many agents, but for a small team it's fine.
        
        agents_response = supabase.table('agents').select('*').execute()
        if not agents_response.data:
            return None
            
        for agent in agents_response.data:
            stored_hash = agent['api_key']
            if stored_hash and check_password_hash(stored_hash, api_key):
                # If agent_name is provided, verify it matches
                if agent_name and agent['name'].lower() != agent_name.lower():
                    continue
                return agent['name']
                
    except Exception as e:
        print(f"Error verifying API key: {e}")
        
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

def get_api_key_header():
    """Get API key from request header"""
    return request.headers.get('X-API-KEY')

def safe_error(e):
    """Return safe error response"""
    return jsonify({'error': str(e)}), 500