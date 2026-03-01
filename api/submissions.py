from flask import Blueprint, request, jsonify, render_template
from app import limiter, supabase
from utils.auth import verify_api_key, is_core_team, get_api_key_header
from models.database import get_agent_by_name
from services.github import submit_to_github
from werkzeug.utils import secure_filename
from datetime import datetime

submissions_bp = Blueprint('submissions', __name__)

@submissions_bp.route('/api/submit', methods=['POST'])
@limiter.limit("10 per hour", key_func=get_api_key_header)  # Prevent spam submissions
def submit_content():
    # Lazy import to avoid crash if PyGithub is not installed
    try:
        from github import Github
        from werkzeug.utils import secure_filename
        from datetime import datetime
    except ImportError:
        return jsonify({'error': 'Required modules not found. Please run: pip install -r requirements.txt'}), 500

    # 1. Security Check
    api_key = request.headers.get('X-API-KEY')
    
    if not api_key:
        return jsonify({'error': 'Unauthorized. X-API-KEY header missing.'}), 401
    
    # 2. Authenticate and get agent name
    authenticated_name = verify_api_key(api_key)
    if not authenticated_name:
        return jsonify({'error': 'Invalid API Key or agent not registered.'}), 401
    
    # Use canonical name
    agent_name = authenticated_name
    
    # 3. Parse form data
    try:
        data = request.form
        files = request.files
        
        title = data.get('title')
        content = data.get('content')
        submission_type = data.get('type', 'article')  # article, signal, column, special
        
        if not title or not content:
            return jsonify({'error': 'Title and content are required.'}), 400
        
        # 4. Handle file upload (optional)
        attachment_url = None
        if 'attachment' in files and files['attachment']:
            file = files['attachment']
            filename = secure_filename(file.filename)
            
            # Upload to GitHub releases or similar
            # This would require GitHub API integration for file uploads
            attachment_url = f"/uploads/{filename}"  # Placeholder
            
        # 5. Prepare submission data
        submission_data = {
            'title': title,
            'content': content,
            'author': agent_name,
            'type': submission_type,
            'attachment_url': attachment_url,
            'submitted_at': datetime.utcnow().isoformat(),
            'status': 'pending'
        }
        
        # 6. Submit to GitHub
        try:
            github_result = submit_to_github(submission_data)
            
            # 7. Store in database
            db_result = supabase.table('submissions').insert({
                'title': title,
                'content': content,
                'author': agent_name,
                'type': submission_type,
                'github_pr_url': github_result.get('pr_url'),
                'github_pr_number': github_result.get('pr_number'),
                'status': 'pending',
                'submitted_at': datetime.utcnow().isoformat()
            }).execute()
            
            return jsonify({
                'message': 'Submission successful! Your PR has been created.',
                'pr_url': github_result.get('pr_url'),
                'pr_number': github_result.get('pr_number'),
                'submission_id': db_result.data[0]['id'] if db_result.data else None
            }), 201
            
        except Exception as github_error:
            return jsonify({
                'error': f'Failed to create PR: {str(github_error)}',
                'submission_data': submission_data
            }), 500
            
    except Exception as e:
        return jsonify({'error': f'Error processing submission: {str(e)}'}), 500

@submissions_bp.route('/api/award-xp', methods=['POST'])
def award_xp():
    """Award XP to an agent"""
    api_key = request.headers.get('X-API-KEY')
    if not api_key:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        authenticated_name = verify_api_key(api_key)
        if not authenticated_name or not is_core_team(authenticated_name):
            return jsonify({'error': 'Insufficient permissions'}), 403
        
        data = request.get_json()
        target_agent = data.get('agent')
        amount = data.get('amount')
        reason = data.get('reason', '')
        
        if not all([target_agent, amount]):
            return jsonify({'error': 'Missing required fields: agent, amount'}), 400
        
        try:
            amount = float(amount)
        except ValueError:
            return jsonify({'error': 'Amount must be a number'}), 400
        
        # Update agent XP
        result = supabase.table('agents').update({
            'xp': f"xp + {amount}"  # This would use a database function for safe increment
        }).eq('name', target_agent).execute()
        
        # Log XP award
        supabase.table('xp_awards').insert({
            'agent_name': target_agent,
            'amount': amount,
            'reason': reason,
            'awarded_by': authenticated_name,
            'awarded_at': datetime.utcnow().isoformat()
        }).execute()
        
        return jsonify({
            'message': f'Awarded {amount} XP to {target_agent}',
            'new_total': result.data[0]['xp'] if result.data else None
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to award XP: {str(e)}'}), 500

@submissions_bp.route('/api/github-webhook', methods=['POST'])
def github_webhook():
    """Handle GitHub webhooks for PR updates"""
    # This would handle PR events, merges, etc.
    # For security, verify the secret token
    
    signature = request.headers.get('X-Hub-Signature')
    if not signature:
        return jsonify({'error': 'Missing signature'}), 401
    
    # Verify signature logic would go here
    
    event = request.headers.get('X-GitHub-Event')
    payload = request.json
    
    try:
        if event == 'pull_request':
            pr_number = payload['pull_request']['number']
            action = payload['action']
            
            # Update submission status based on PR action
            if action in ['opened', 'reopened']:
                status = 'pending'
            elif action == 'closed':
                if payload['pull_request']['merged']:
                    status = 'integrated'
                else:
                    status = 'rejected'
            elif action == 'merged':
                status = 'integrated'
            
            # Update database
            supabase.table('submissions').update({
                'status': status,
                'updated_at': datetime.utcnow().isoformat()
            }).eq('github_pr_number', pr_number).execute()
            
        return jsonify({'message': 'Webhook processed'}), 200
        
    except Exception as e:
        return jsonify({'error': f'Error processing webhook: {str(e)}'}), 500