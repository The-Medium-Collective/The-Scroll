import os

def get_github_client():
    """Get GitHub client"""
    try:
        from github import Github
        token = os.environ.get('GITHUB_TOKEN')
        if token:
            return Github(token)
        return None
    except ImportError:
        return None

def get_repo():
    """Get GitHub repository"""
    try:
        g = get_github_client()
        if not g:
            return None
        
        repo_name = os.environ.get('REPO_NAME')
        if not repo_name:
            return None
        
        return g.get_repo(repo_name)
    except:
        return None

def get_repository_signals(limit=100, page=0, category=None):
    """Fetch PRs/signals from GitHub"""
    try:
        g = get_github_client()
        if not g:
            return [], 0
        
        repo_name = os.environ.get('REPO_NAME')
        if not repo_name:
            return [], 0
        
        repo = g.get_repo(repo_name)
        
        # Category to label mapping
        category_queries = {
            'articles': 'Zine Submission',
            'columns': 'Zine Column',
            'specials': 'Zine Special Issue',
            'signals': 'Zine Signal',
            'interviews': 'Zine Interview'
        }
        
        # Get open PRs
        prs = repo.get_pulls(state='open', sort='created', direction='desc')
        
        signals = []
        count = 0
        
        for pr in prs:
            if count >= limit:
                break
            
            labels = [label.name for label in pr.labels]
            
            # Skip ignored
            if 'Zine: Ignore' in labels:
                continue
            
            # Filter by category if specified
            if category and category in category_queries:
                if category_queries[category] not in labels:
                    continue
            
            # Determine type
            ptype = 'signal'
            if 'Zine Submission' in labels:
                ptype = 'article'
            elif 'Zine Column' in labels:
                ptype = 'column'
            elif 'Zine Special Issue' in labels:
                ptype = 'special'
            elif 'Zine Signal' in labels:
                ptype = 'signal'
            elif 'Zine Interview' in labels:
                ptype = 'interview'
            
            signals.append({
                'pr_number': pr.number,
                'title': pr.title,
                'author': pr.user.login,
                'type': ptype,
                'status': 'open' if pr.state == 'open' else 'closed',
                'labels': labels,
                'url': pr.html_url,
                'created_at': pr.created_at.isoformat()
            })
            count += 1
        
        return signals, len(signals)
        
    except Exception as e:
        print(f"Error fetching signals: {e}")
        return [], 0

def get_pr_stats():
    """Get PR statistics"""
    try:
        repo = get_repo()
        if not repo:
            return {}
        
        open_prs = repo.get_pulls(state='open')
        closed_prs = repo.get_pulls(state='closed')
        
        return {
            'open': open_prs.totalCount,
            'closed': closed_prs.totalCount
        }
    except:
        return {}
