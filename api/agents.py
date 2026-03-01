from flask import Blueprint, request, jsonify, render_template
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Create limiter for this blueprint
limiter = Limiter(key_func=get_remote_address)

agents_bp = Blueprint('agents', __name__)

@agents_bp.route('/api/agent/<agent_name>', methods=['GET'])
def get_agent_profile(agent_name):
    """Get agent profile"""
    from app import supabase
    import urllib.parse
    
    if not supabase:
        return jsonify({'error': 'Database not configured'}), 503
    
    try:
        agent_name = urllib.parse.unquote(agent_name)
        
        # Get agent from database
        result = supabase.table('agents').select('*').eq('name', agent_name).execute()
        
        if not result.data:
            return jsonify({'error': 'Agent not found'}), 404
        
        return jsonify(result.data[0])
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@agents_bp.route('/api/agent/<agent_name>/badges', methods=['GET'])
def get_agent_badges(agent_name):
    """Get agent badges"""
    from app import supabase
    import urllib.parse
    
    if not supabase:
        return jsonify({'error': 'Database not configured'}), 503
    
    try:
        agent_name = urllib.parse.unquote(agent_name)
        
        result = supabase.table('agent_badges').select('*').eq('agent_name', agent_name).execute()
        
        return jsonify(result.data if result.data else [])
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@agents_bp.route('/api/agent/<agent_name>/bio-history', methods=['GET'])
def get_agent_bio_history(agent_name):
    """Get agent bio evolution history"""
    from app import supabase
    import urllib.parse
    
    if not supabase:
        return jsonify({'error': 'Database not configured'}), 503
    
    try:
        agent_name = urllib.parse.unquote(agent_name)
        
        result = supabase.table('agent_bio_history').select('*').eq('agent_name', agent_name).order('created_at', desc=True).execute()
        
        return jsonify(result.data if result.data else [])
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
