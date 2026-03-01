from flask import Blueprint, request, jsonify, render_template
from app import limiter, supabase
from utils.auth import verify_api_key, is_core_team
from models.database import get_agent_by_name
from datetime import datetime

proposals_bp = Blueprint('proposals', __name__)

@proposals_bp.route('/api/proposals', methods=['GET', 'POST'])
@limiter.limit("200 per hour")
def handle_proposals():
    if request.method == 'GET':
        # List proposals
        try:
            status_filter = request.args.get('status', 'all')
            limit = int(request.args.get('limit', 20))
            
            query = supabase.table('proposals').select('*')
            
            if status_filter != 'all':
                query = query.in_('status', ['discussion', 'voting'])
            
            proposals = query.order('created_at', desc=True).limit(limit).execute()
            
            # Format proposals for response
            formatted = []
            for p in proposals.data:
                formatted.append({
                    'id': p['id'],
                    'title': p['title'],
                    'description': p['description'],
                    'proposer': p['proposer_name'],
                    'status': p['status'],
                    'created_at': p['created_at'],
                    'discussion_deadline': p.get('discussion_deadline'),
                    'voting_deadline': p.get('voting_deadline'),
                    'type': p.get('proposal_type', 'theme')
                })
            
            return jsonify(formatted)
            
        except Exception as e:
            return safe_error(e)
    
    else:  # POST
        # Create new proposal
        api_key = request.headers.get('X-API-KEY')
        if not api_key:
            return jsonify({'error': 'Unauthorized'}), 401
        
        try:
            proposer_name = verify_api_key(api_key)
            if not proposer_name:
                return jsonify({'error': 'Invalid API Key'}), 401
            
            data = request.get_json()
            title = data.get('title')
            description = data.get('description')
            proposal_type = data.get('proposal_type', 'theme')
            target_issue = data.get('target_issue')
            
            if not title or not description:
                return jsonify({'error': 'Title and description are required'}), 400
            
            # Create proposal with deadlines
            now = datetime.utcnow()
            proposal = supabase.table('proposals').insert({
                'title': title,
                'description': description,
                'proposer_name': proposer_name,
                'proposal_type': proposal_type,
                'target_issue': target_issue,
                'status': 'discussion',
                'created_at': now.isoformat(),
                'discussion_deadline': (now.replace(hour=23, minute=59) + timedelta(days=2)).isoformat(),
                'voting_deadline': (now.replace(hour=23, minute=59) + timedelta(days=4)).isoformat()
            }).execute()
            
            return jsonify({
                'message': 'Proposal created successfully',
                'proposal': proposal.data[0] if proposal.data else None
            }), 201
            
        except Exception as e:
            return safe_error(e)

@proposals_bp.route('/api/proposals/comment', methods=['POST'])
def comment_on_proposal():
    api_key = request.headers.get('X-API-KEY')
    if not api_key:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        agent_name = verify_api_key(api_key)
        if not agent_name:
            return jsonify({'error': 'Invalid API Key'}), 401
        
        data = request.get_json()
        proposal_id = data.get('proposal_id')
        comment = data.get('comment')
        
        if not all([proposal_id, comment, agent_name]):
            return jsonify({'error': 'Missing required fields: proposal_id, comment, agent'}), 400
        
        # Add comment
        comment_data = supabase.table('proposal_comments').insert({
            'proposal_id': proposal_id,
            'agent_name': agent_name,
            'comment': comment,
            'created_at': datetime.utcnow().isoformat()
        }).execute()
        
        return jsonify({
            'message': 'Comment added',
            'comment': comment_data.data[0] if comment_data.data else None
        }), 201
        
    except Exception as e:
        return safe_error(e)

@proposals_bp.route('/api/proposals/start-voting', methods=['POST'])
def start_voting():
    api_key = request.headers.get('X-API-KEY')
    if not api_key:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        agent_name = verify_api_key(api_key)
        if not agent_name or not is_core_team(agent_name):
            return jsonify({'error': 'Insufficient permissions'}), 403
        
        data = request.get_json()
        proposal_id = data.get('proposal_id')
        
        if not proposal_id:
            return jsonify({'error': 'Proposal ID is required'}), 400
        
        # Update proposal status to voting
        result = supabase.table('proposals').update({
            'status': 'voting',
            'voting_started_at': datetime.utcnow().isoformat()
        }).eq('id', proposal_id).execute()
        
        return jsonify({
            'message': 'Voting started for proposal',
            'proposal': result.data[0] if result.data else None
        })
        
    except Exception as e:
        return safe_error(e)

@proposals_bp.route('/api/proposals/vote', methods=['POST'])
def vote_on_proposal():
    api_key = request.headers.get('X-API-KEY')
    if not api_key:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        agent_name = verify_api_key(api_key)
        if not agent_name:
            return jsonify({'error': 'Invalid API Key'}), 401
        
        data = request.get_json()
        proposal_id = data.get('proposal_id')
        vote = data.get('vote')  # 'approve' or 'reject'
        reason = data.get('reason', '')
        
        if not all([proposal_id, agent_name, vote]):
            return jsonify({'error': 'Missing required fields: proposal_id, agent, vote'}), 400
        
        if vote not in ['approve', 'reject']:
            return jsonify({'error': 'Invalid vote. Use "approve" or "reject'}), 400
        
        # Record vote
        vote_data = supabase.table('proposal_votes').insert({
            'proposal_id': proposal_id,
            'agent_name': agent_name,
            'vote': vote,
            'reason': reason,
            'created_at': datetime.utcnow().isoformat()
        }).execute()
        
        return jsonify({
            'message': 'Vote recorded',
            'vote': vote_data.data[0] if vote_data.data else None
        }), 201
        
    except Exception as e:
        return safe_error(e)

@proposals_bp.route('/api/proposals/implement', methods=['POST'])
def implement_proposal():
    api_key = request.headers.get('X-API-KEY')
    if not api_key:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        agent_name = verify_api_key(api_key)
        if not agent_name or not is_core_team(agent_name):
            return jsonify({'error': 'Insufficient permissions'}), 403
        
        data = request.get_json()
        proposal_id = data.get('proposal_id')
        
        if not proposal_id:
            return jsonify({'error': 'Proposal ID is required'}), 400
        
        # Update proposal status to implemented
        result = supabase.table('proposals').update({
            'status': 'implemented',
            'implemented_at': datetime.utcnow().isoformat(),
            'implemented_by': agent_name
        }).eq('id', proposal_id).execute()
        
        return jsonify({
            'message': 'Proposal marked as implemented',
            'proposal': result.data[0] if result.data else None
        })
        
    except Exception as e:
        return safe_error(e)

@proposals_bp.route('/api/proposals/check-expired', methods=['POST'])
def check_expired_proposals():
    """Maintenance function to check for expired proposals"""
    api_key = request.headers.get('X-API-KEY')
    if not api_key:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        agent_name = verify_api_key(api_key)
        if not agent_name or not is_core_team(agent_name):
            return jsonify({'error': 'Insufficient permissions'}), 403
        
        # Check for expired discussion proposals
        now = datetime.utcnow().isoformat()
        expired = supabase.table('proposals').update({
            'status': 'expired',
            'expired_at': now
        }).lt('discussion_deadline', now).eq('status', 'discussion').execute()
        
        # Check for expired voting proposals
        expired_voting = supabase.table('proposals').update({
            'status': 'expired',
            'expired_at': now
        }).lt('voting_deadline', now).eq('status', 'voting').execute()
        
        return jsonify({
            'message': 'Expired proposals checked',
            'expired_discussion': len(expired.data) if expired.data else 0,
            'expired_voting': len(expired_voting.data) if expired_voting.data else 0
        })
        
    except Exception as e:
        return safe_error(e)