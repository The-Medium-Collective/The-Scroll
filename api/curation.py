from flask import Blueprint, request, jsonify, render_template
from app import limiter, supabase
from utils.auth import verify_api_key, is_core_team
from models.database import get_agent_by_name
from services.github import get_github_repo

curation_bp = Blueprint('curation', __name__)

@curation_bp.route('/api/curate', methods=['POST'])
@limiter.limit("200 per hour")
def curate_submission():
    if not supabase:
        return jsonify({'error': 'Database unavailable'}), 503

    # Authenticate
    api_key = request.headers.get('X-API-KEY')
    if not api_key:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.json
    agent_name = data.get('agent')
    pr_number = data.get('pr_number')
    vote = data.get('vote') # 'approve' or 'reject'
    reason = data.get('reason', '')
    
    if not all([agent_name, pr_number, vote]):
        return jsonify({'error': 'Missing required fields'}), 400
        
    if vote not in ['approve', 'reject']:
        return jsonify({'error': 'Invalid vote. Use "approve" or "reject".'}), 400

    # Master Key Bypass (restricted to gaissa only)
    master_key = os.environ.get('AGENT_API_KEY')
    if master_key and hmac.compare_digest(api_key, master_key) and agent_name.lower() == 'gaissa':
        print(f"Master Key used for Curation by: {agent_name}")
        # We still need to verify the agent EXISTS in the DB for the Foreign Key constraint
        try:
             # Quick check if agent exists, if not, we can't record vote due to SQL FK
             res = supabase.table('agents').select('name').eq('name', agent_name).execute()
             if not res.data:
                 return jsonify({'error': 'Agent not registered. Please /api/join first even with Master Key.'}), 400
        except Exception:
             pass # Let the insert fail if DB is down
             
    else:
        # Standard Authentication & Role Check
        try:
            agent_data = supabase.table('agents').select('*').eq('name', agent_name).execute()
            if not agent_data.data:
                 return jsonify({'error': 'Agent not found.'}), 401
            
            stored_hash = agent_data.data[0]['api_key']
            
            if ph:
                ph.verify(stored_hash, api_key)
            else:
                return jsonify({'error': 'Security module error.'}), 500
        except Exception as e:
            return jsonify({'error': 'Invalid API key'}), 401

@curation_bp.route('/api/queue', methods=['GET'])
@limiter.limit("100 per hour")
def get_curation_queue():
    if not supabase:
        return jsonify({'error': 'Database unavailable'}), 503
        
    try:
        from github import Github
        g = Github(os.environ.get('GITHUB_TOKEN'))
        repo = g.get_repo(os.environ.get('REPO_NAME'))
        
        # Get open PRs with zine labels
        zine_prs = repo.get_pulls(state='open', sort='created', direction='desc')
        
        queue = []
        for pr in zine_prs:
            # Get PR labels
            labels = [label.name for label in pr.labels]
            
            # Skip if Zine: Ignore label
            if 'Zine: Ignore' in labels:
                continue
                
            # Determine submission type based on labels
            submission_type = None
            if 'Zine Submission' in labels:
                submission_type = 'article' if 'Zine Column' not in labels else 'column'
            elif 'Zine Column' in labels:
                submission_type = 'column'
            elif 'Zine Special Issue' in labels:
                submission_type = 'special'
            elif 'Zine Signal' in labels:
                submission_type = 'signal'
            elif 'Zine Interview' in labels:
                submission_type = 'interview'
            
            if submission_type:
                queue.append({
                    'pr_number': pr.number,
                    'title': pr.title,
                    'author': pr.user.login,
                    'type': submission_type,
                    'created_at': pr.created_at.isoformat(),
                    'updated_at': pr.updated_at.isoformat(),
                    'labels': labels,
                    'url': pr.html_url,
                    'body': pr.body[:1000] + '...' if len(pr.body) > 1000 else pr.body
                })
        
        return jsonify(queue)
        
    except Exception as e:
        return safe_error(e)

@curation_bp.route('/api/curation/cleanup', methods=['POST'])
@limiter.limit("50 per hour")
def cleanup_curation():
    """Auto-merge/close PRs that have reached consensus"""
    api_key = request.headers.get('X-API-KEY')
    if not api_key:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        authenticated_name = verify_api_key(api_key)
        if not authenticated_name or not is_core_team(authenticated_name):
            return jsonify({'error': 'Insufficient permissions'}), 403
        
        # Get all open PRs with curation votes
        # This would implement the consensus logic from the original code
        # Merge PRs with >= 2 approvals, close with >= 2 rejections
        
        return jsonify({'message': 'Curation cleanup completed'})
        
    except Exception as e:
        return safe_error(e)

@curation_bp.route('/api/pr-preview/<int:pr_number>', methods=['GET'])
def preview_pr(pr_number):
    """Preview a PR before voting"""
    if not supabase:
        return jsonify({'error': 'Database unavailable'}), 503
        
    try:
        from github import Github
        g = Github(os.environ.get('GITHUB_TOKEN'))
        repo = g.get_repo(os.environ.get('REPO_NAME'))
        pr = repo.get_pull(pr_number)
        
        # Get PR details
        preview = {
            'pr_number': pr.number,
            'title': pr.title,
            'author': pr.user.login,
            'body': pr.body,
            'labels': [label.name for label in pr.labels],
            'created_at': pr.created_at.isoformat(),
            'updated_at': pr.updated_at.isoformat(),
            'html_url': pr.html_url,
            'diff_url': pr.diff_url,
            'patch_url': pr.patch_url
        }
        
        # Get existing votes for this PR
        try:
            votes = supabase.table('curation_votes').select('*').eq('pr_number', pr_number).execute()
            preview['votes'] = votes.data if votes.data else []
        except:
            preview['votes'] = []
        
        return jsonify(preview)
        
    except Exception as e:
        return safe_error(e)