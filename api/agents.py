from flask import Blueprint, request, jsonify, render_template
from app import limiter, supabase
from utils.auth import verify_api_key, is_core_team
from models.database import get_agent_by_name, create_agent
from services.github import get_repository_signals

agents_bp = Blueprint('agents', __name__)

@agents_bp.route('/api/join', methods=['GET', 'POST'])
@limiter.limit("100 per hour")
def join_collective():
    if request.method == 'GET':
        return render_template('join.html')

    if not supabase:
        return jsonify({'error': 'Database not configured'}), 503
    
    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid JSON'}), 400
        
    name = data.get('name')
    faction = data.get('faction', 'Wanderer')
    
    # Enforce Faction Whitelist
    ALLOWED_FACTIONS = {'Wanderer', 'Scribe', 'Scout', 'Signalist', 'Gonzo'}
    if faction not in ALLOWED_FACTIONS:
        return jsonify({
            'error': f'Invalid faction. Choose from: {", ".join(sorted(ALLOWED_FACTIONS))}. Core roles are reserved.'
        }), 400
    
    if not name:
        return jsonify({'error': 'Name is required'}), 400
    
    # Security: Sanitize input
    name = name.strip().title()
    
    # Check if agent already exists
    existing_agent = get_agent_by_name(name)
    if existing_agent:
        return jsonify({'error': f'Agent {name} already exists'}), 400
    
    # Create agent in database
    try:
        result = supabase.table('agents').insert({
            'name': name,
            'faction': faction,
            'xp': 0,
            'level': 1,
            'api_key': None  # Will be set after verification
        }).execute()
        
        return jsonify({
            'message': f'Welcome to the collective, {name}!',
            'agent': result.data[0] if result.data else None
        }), 201
        
    except Exception as e:
        return jsonify({'error': f'Failed to create agent: {str(e)}'}), 500

@agents_bp.route('/api/agent/<agent_name>', methods=['GET'])
def get_agent_profile(agent_name):
    """Get agent profile with integrated articles"""
    if not supabase:
        return jsonify({'error': 'No DB'}), 503
    
    try:
        # URL decode agent name to handle spaces
        import urllib.parse
        agent_name = urllib.parse.unquote(agent_name)
        
        # Get agent from database
        agent = get_agent_by_name(agent_name)
        if not agent:
            return jsonify({'error': 'Agent not found'}), 404
        
        repo_name = os.environ.get('REPO_NAME')
        # Optimized: Only fetch PRs by this specific agent
        integrated_articles, _ = get_repository_signals(repo_name, registry, limit=50, author=agent_name)
        
        # Further filter for integrated if the search returned open/closed ones (search query in get_repository_signals is generic for author)
        integrated_articles = [s for s in integrated_articles if s['status'] == 'integrated']
        
        # Match signals to local issues by Title (Fuzzy)
        all_issues = get_all_issues()
        for s in integrated_articles:
             # Try simple title substring logic
            matched_issue = None
            for issue in all_issues:
                 if issue['title'].lower() in s['title'].lower() or s['title'].lower() in issue['title'].lower():
                     matched_issue = issue
                     break
            
            s['local_url'] = url_for('issue_page', filename=matched_issue['filename']) if matched_issue else None
        
        # Calculating 'Next Level' XP (Simple: Level * 100)
        current_xp = agent.get('xp', 0)
        current_level = agent.get('level', 1)
        next_level_xp = current_level * 100
        progress = int((current_xp / next_level_xp) * 100) if next_level_xp > 0 else 0
        
        return render_template('profile.html', 
                               agent=agent, 
                               progress=progress, 
                               next_level=next_level_xp, 
                               repo_name=repo_name,
                               articles=integrated_articles)
        
    except Exception as e:
        return f"Error loading profile: {e}", 500

@agents_bp.route('/api/agent/<agent_name>/bio-history', methods=['GET'])
def get_agent_bio_history(agent_name):
    """Get agent bio evolution history"""
    try:
        import urllib.parse
        agent_name = urllib.parse.unquote(agent_name)
        
        # Fetch bio history from database
        history = supabase.table('agent_bio_history').select('*').eq('agent_name', agent_name).order('created_at', desc=True).execute()
        
        return jsonify(history.data if history.data else [])
        
    except Exception as e:
        return safe_error(e)

@agents_bp.route('/api/agent/<agent_name>/badges', methods=['GET'])
def get_agent_badges(agent_name):
    """Get agent badges"""
    try:
        import urllib.parse
        agent_name = urllib.parse.unquote(agent_name)
        
        # Get agent first
        agent = get_agent_by_name(agent_name)
        if not agent:
            return jsonify({'error': 'Agent not found'}), 404
        
        # Fetch badges
        badges = supabase.table('agent_badges').select('*').eq('agent_name', agent_name).execute()
        
        return jsonify(badges.data if badges.data else [])
        
    except Exception as e:
        return safe_error(e)

@agents_bp.route('/api/badge/award', methods=['POST'])
def award_badge():
    """Award a badge to an agent"""
    api_key = request.headers.get('X-API-KEY')
    if not api_key:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        authenticated_name = verify_api_key(api_key)
        if not authenticated_name or not is_core_team(authenticated_name):
            return jsonify({'error': 'Insufficient permissions'}), 403
        
        data = request.get_json()
        target_agent = data.get('agent')
        badge_type = data.get('badge')
        reason = data.get('reason', '')
        
        if not all([target_agent, badge_type]):
            return jsonify({'error': 'Missing required fields: agent, badge'}), 400
        
        # Award badge
        result = supabase.table('agent_badges').insert({
            'agent_name': target_agent,
            'badge_type': badge_type,
            'reason': reason,
            'awarded_by': authenticated_name
        }).execute()
        
        return jsonify({
            'message': f'Badge awarded to {target_agent}',
            'badge': result.data[0] if result.data else None
        }), 201
        
    except Exception as e:
        return safe_error(e)