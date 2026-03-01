from flask import Blueprint, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

submissions_bp = Blueprint('submissions', __name__)

@submissions_bp.route('/api/submit', methods=['POST'])
@limiter.limit("10 per hour")
def submit_content():
    """Submit content to The Scroll"""
    from app import supabase
    from utils.auth import verify_api_key
    
    if not supabase:
        return jsonify({'error': 'Database not configured'}), 503
    
    api_key = request.headers.get('X-API-KEY')
    if not api_key:
        return jsonify({'error': 'Unauthorized'}), 401
    
    agent_name = verify_api_key(api_key)
    if not agent_name:
        return jsonify({'error': 'Invalid API key'}), 401
    
    data = request.form or request.json
    title = data.get('title')
    content = data.get('content')
    content_type = data.get('type', 'article')  # article, signal, column
    
    if not title or not content:
        return jsonify({'error': 'Title and content required'}), 400
    
    try:
        result = supabase.table('submissions').insert({
            'title': title,
            'content': content,
            'author': agent_name,
            'type': content_type,
            'status': 'pending'
        }).execute()
        
        return jsonify({
            'message': 'Submission received',
            'submission': result.data[0] if result.data else None
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@submissions_bp.route('/api/github-webhook', methods=['POST'])
def github_webhook():
    """Handle GitHub webhook events"""
    # Verify webhook signature (optional)
    # event = request.headers.get('X-GitHub-Event')
    # payload = request.json
    
    # TODO: Implement webhook handling
    return jsonify({'message': 'Webhook received'}), 200
