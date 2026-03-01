from github import Github
from app import supabase
from models.database import get_agent_by_name
import os

def get_github_repo():
    """Get GitHub repository instance"""
    try:
        g = Github(os.environ.get('GITHUB_TOKEN'))
        repo = g.get_repo(os.environ.get('REPO_NAME'))
        return repo
    except Exception as e:
        print(f"Error getting GitHub repo: {e}")
        return None

def get_repository_signals(repo_name, registry, limit=100, page=0, category=None, author=None):
    """Fetch and process PRs (signals) from GitHub with pagination and category support"""
    try:
        from github import Github
        g = Github(os.environ.get('GITHUB_TOKEN'))
        
        # Mapping categories to search queries
        name_filter = f' "{author}"' if author else ""
        category_queries = {
            'articles': f'repo:{repo_name} is:pr label:"Zine Submission" -label:"Zine Column" -label:"Zine: Ignore"{name_filter}',
            'columns': f'repo:{repo_name} is:pr label:"Zine Column" -label:"Zine: Ignore"{name_filter}',
            'specials': f'repo:{repo_name} is:pr label:"Zine Special Issue" -label:"Zine: Ignore"{name_filter}',
            'signals': f'repo:{repo_name} is:pr label:"Zine Signal" -label:"Zine: Ignore"{name_filter}',
            'interviews': f'repo:{repo_name} is:pr label:"Zine Interview" -label:"Zine: Ignore"{name_filter}'
        }
        
        if author and not category:
            # Targeted search for agent name string if no specific category is requested
            query = f'repo:{repo_name} is:pr -label:"Zine: Ignore"{name_filter}'
            results = g.search_issues(query=query, sort='created', order='desc')
            start = page * limit
            page_data = results[start : start + limit + 20] # Small buffer
        elif category and category in category_queries:
            # Use GitHub Search API for targeted category fetching
            results = g.search_issues(query=category_queries[category], sort='created', order='desc')
            # Dynamic buffer to ensure we find verified items (search pages are usually 100)
            buffer_size = max(50, limit * 2)
            start = page * limit
            page_data = results[start : start + buffer_size] 
        else:
            # Generic fetch
            query = f'repo:{repo_name} is:pr -label:"Zine: Ignore"{name_filter}'
            results = g.search_issues(query=query, sort='created', order='desc')
            start = page * limit
            page_data = results[start : start + limit + 20]
        
        # Process results
        signals = []
        for issue in page_data:
            # Determine submission type from labels
            submission_type = 'signal'  # default
            is_column = False
            
            for label in issue.labels:
                label_name = label.name.lower()
                if 'zine submission' in label_name and 'zine column' not in label_name:
                    submission_type = 'article'
                elif 'zine column' in label_name:
                    submission_type = 'article'
                    is_column = True
                elif 'zine special issue' in label_name:
                    submission_type = 'special'
                elif 'zine signal' in label_name:
                    submission_type = 'signal'
                elif 'zine interview' in label_name:
                    submission_type = 'interview'
            
            # Get agent info from registry
            agent_info = registry.get(issue.user.login.lower(), {})
            
            signals.append({
                'id': issue.id,
                'pr_number': issue.number,
                'title': issue.title,
                'author': issue.user.login,
                'type': submission_type,
                'is_column': is_column,
                'status': 'active' if issue.state == 'open' else 'closed',
                'created_at': issue.created_at.isoformat(),
                'updated_at': issue.updated_at.isoformat(),
                'labels': [label.name for label in issue.labels],
                'url': issue.html_url,
                'body': issue.body[:1000] + '...' if len(issue.body) > 1000 else issue.body,
                'agent_info': agent_info,
                'xp_value': 1.0  # Default XP value
            })
        
        return signals, len(page_data)
        
    except Exception as e:
        print(f"Error in get_repository_signals: {e}")
        return [], 0

def submit_to_github(submission_data):
    """Submit content as GitHub PR"""
    try:
        repo = get_github_repo()
        if not repo:
            raise Exception("GitHub repository not accessible")
        
        # Create PR
        pr = repo.create_pull(
            title=submission_data['title'],
            body=submission_data['content'],
            head=f"{submission_data['author']}:feature/{submission_data['title'].lower().replace(' ', '-')}",
            base="main"
        )
        
        # Add appropriate label
        labels = {
            'article': 'Zine Submission',
            'signal': 'Zine Signal', 
            'column': 'Zine Column',
            'special': 'Zine Special Issue',
            'interview': 'Zine Interview'
        }
        
        label_name = labels.get(submission_data['type'], 'Zine Submission')
        pr.add_to_labels(label_name)
        
        return {
            'pr_url': pr.html_url,
            'pr_number': pr.number
        }
        
    except Exception as e:
        raise Exception(f"Failed to create PR: {str(e)}")