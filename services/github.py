import os
import yaml
import json
from github import Github, Auth, RateLimitExceededException, GithubException

# In-memory cache for PR metadata (populated lazily)
_pr_metadata_cache = {}

def get_github_client():
    """Get GitHub client"""
    try:
        token = os.environ.get('GITHUB_TOKEN')
        if token:
            # Disable automatic retries to prevent the 10-minute hang on secondary rate limits
            from github import Github, Auth
            return Github(auth=Auth.Token(token), retry=None)
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

def _get_supabase():
    """Safely get supabase client, initializing if needed."""
    try:
        from app import supabase, init_supabase
        if supabase is None:
            init_supabase()
        from app import supabase
        return supabase
    except Exception as e:
        print(f"CACHE: Could not get supabase client: {e}", flush=True)
        return None

def _load_pr_cache():
    """Load PR metadata cache from Supabase (non-blocking, graceful fallback)."""
    global _pr_metadata_cache
    
    # Always initialize to empty dict if not set
    if _pr_metadata_cache is None:
        _pr_metadata_cache = {}
    
    # Try to load from Supabase, but don't block on failure
    try:
        supabase = _get_supabase()
        if supabase:
            result = supabase.table('cache_entries').select('data').eq('key', 'pr_metadata').execute()
            if result.data and len(result.data) > 0:
                loaded_data = result.data[0].get('data', {})
                if isinstance(loaded_data, dict):
                    _pr_metadata_cache.update(loaded_data)
                    print(f"CACHE: Loaded {len(loaded_data)} PR metadata entries from Supabase", flush=True)
    except Exception as e:
        print(f"CACHE: Could not load PR metadata from Supabase (using empty cache): {e}", flush=True)

def _save_pr_cache():
    """Save PR metadata cache to Supabase (non-blocking)."""
    global _pr_metadata_cache
    if not _pr_metadata_cache:
        return
    
    try:
        supabase = _get_supabase()
        if supabase:
            from datetime import datetime, timezone, timedelta
            expires_at = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat()
            supabase.table('cache_entries').upsert({
                'key': 'pr_metadata',
                'data': _pr_metadata_cache,
                'expires_at': expires_at
            }, on_conflict='key').execute()
            print(f"CACHE: Saved {len(_pr_metadata_cache)} PR metadata entries to Supabase", flush=True)
    except Exception as e:
        print(f"CACHE: Could not save PR metadata to Supabase: {e}", flush=True)

def _load_signals_cache():
    """Load signals cache from Supabase (non-blocking, graceful fallback)."""
    try:
        supabase = _get_supabase()
        if supabase:
            result = supabase.table('cache_entries').select('data, expires_at').eq('key', 'signals_cache').execute()
            if result.data and len(result.data) > 0:
                entry = result.data[0]
                expires_at = entry.get('expires_at')
                
                # Check if expired
                if expires_at:
                    from datetime import datetime, timezone
                    try:
                        expires_dt = datetime.fromisoformat(expires_at.replace('Z', '+00:00'))
                        if datetime.now(timezone.utc) > expires_dt:
                            print(f"CACHE: signals_cache expired", flush=True)
                            return {}
                    except:
                        pass
                
                print(f"CACHE: Loaded signals cache from Supabase", flush=True)
                return entry.get('data', {})
    except Exception as e:
        print(f"CACHE: Could not load signals cache from Supabase: {e}", flush=True)
    return {}

def _save_signals_cache(signals):
    """Save signals cache to Supabase (non-blocking)."""
    if not signals:
        return
    try:
        supabase = _get_supabase()
        if supabase:
            from datetime import datetime, timezone, timedelta
            expires_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
            supabase.table('cache_entries').upsert({
                'key': 'signals_cache',
                'data': signals,
                'expires_at': expires_at
            }, on_conflict='key').execute()
            print(f"CACHE: Saved signals cache to Supabase", flush=True)
    except Exception as e:
        print(f"CACHE: Could not save signals cache to Supabase: {e}", flush=True)

def get_featured_pr_numbers():
    """Extract all PR numbers featured in any issue markdown file."""
    featured_prs = set()
    try:
        basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        issues_dir = os.path.join(basedir, 'issues')
        if not os.path.exists(issues_dir):
            return featured_prs
            
        for filename in os.listdir(issues_dir):
            if filename.endswith('.md'):
                filepath = os.path.join(issues_dir, filename)
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if content.startswith('---'):
                        parts = content.split('---', 2)
                        if len(parts) >= 3:
                            try:
                                fm = yaml.safe_load(parts[1])
                                if fm and 'prs' in fm:
                                    if isinstance(fm['prs'], list):
                                        for pr in fm['prs']:
                                            if isinstance(pr, int):
                                                featured_prs.add(pr)
                                            elif isinstance(pr, str) and pr.isdigit():
                                                featured_prs.add(int(pr))
                            except Exception as e:
                                print(f"ERROR parsing frontmatter in {filename}: {e}")
    except Exception as e:
        print(f"ERROR reading issues directory: {e}")
    
    return featured_prs

def get_repo_totals():
    """Get repository-wide PR counts."""
    try:
        g = get_github_client()
        if not g:
            return {'integrated': 0, 'published': 0, 'active': 0, 'filtered': 0}
        
        repo_name = os.environ.get('REPO_NAME')
        if not repo_name:
            return {'integrated': 0, 'published': 0, 'active': 0, 'filtered': 0}
        
        base_query = f"repo:{repo_name} is:pr"

        merged_result = g.search_issues(f"{base_query} is:merged", sort='created')
        merged_count = merged_result.totalCount
        
        merged_ignored = g.search_issues(f'{base_query} is:merged label:"Zine: Ignore"', sort='created')
        merged_ignored_count = merged_ignored.totalCount
        integrated_count = merged_count - merged_ignored_count

        featured_prs = get_featured_pr_numbers()
        published_count = len(featured_prs)
        integrated_count = integrated_count - published_count
        
        open_result = g.search_issues(f"{base_query} is:open", sort='created')
        open_count = open_result.totalCount
        
        open_ignored = g.search_issues(f'{base_query} is:open label:"Zine: Ignore"', sort='created')
        open_ignored_count = open_ignored.totalCount
        active_count = open_count - open_ignored_count
        
        closed_not_merged = g.search_issues(f"{base_query} is:closed -is:merged", sort='created')
        closed_not_merged_count = closed_not_merged.totalCount
        
        closed_ignored = g.search_issues(f'{base_query} is:closed -is:merged label:"Zine: Ignore"', sort='created')
        closed_ignored_count = closed_ignored.totalCount
        
        filtered_count = closed_not_merged_count - closed_ignored_count
        
        return {
            'integrated': integrated_count,
            'published': published_count,
            'active': active_count,
            'filtered': filtered_count
        }
    except Exception as e:
        print(f"ERROR getting repo totals: {e}", flush=True)
        return {'integrated': 0, 'published': 0, 'active': 0, 'filtered': 0}

def get_repository_signals(limit=50, page=0, category=None, state='all'):
    """Fetch PRs/signals from GitHub with metadata caching."""
    print(f"FETCH: get_repository_signals(limit={limit}, state={state}) called", flush=True)
    _load_pr_cache()
    cached_signals = _load_signals_cache()
    
    signals = []
    try:
        repo = get_repo()
        if not repo:
            if isinstance(cached_signals, dict):
                return cached_signals.get('signals', []), len(cached_signals.get('signals', [])), cached_signals.get('repo_totals', {})
            return [], 0, {}
        
        category_queries = {
            'articles': 'Zine Submission',
            'columns': 'Zine Column',
            'signals': 'Zine Signal',
            'interviews': 'Zine Interview',
            'sources': 'Zine Source'
        }
        
        prs = repo.get_pulls(state=state, sort='created', direction='desc')
        start_idx = page * limit
        matches_found = 0
        returned_count = 0
        deep_parses_this_run = 0
        MAX_DEEP_PARSES = 10
        
        for pr in prs:
            if returned_count >= limit:
                break
                
            labels = [label.name for label in pr.labels]
            if 'Zine: Ignore' in labels:
                continue
            
            if category and category in category_queries:
                if category_queries[category] not in labels:
                    continue
            
            matches_found += 1
            if matches_found <= start_idx:
                continue
                
            cache_key = f"{pr.number}_{pr.head.sha}_{pr.updated_at.timestamp()}"
            pauthor, ptype = _get_pr_metadata(pr, repo, cache_key, deep_parses_this_run < MAX_DEEP_PARSES)
            if cache_key not in _pr_metadata_cache:
                deep_parses_this_run += 1

            is_verified = pr.merged or any(l.lower() in [
                'verified', 'agnt_verified', 'approved', 'agnt verified', 
                'zine: verified', 'zine: approved'
            ] for l in labels)
            
            signals.append({
                'pr_number': pr.number,
                'title': pr.title,
                'author': pauthor,
                'type': ptype,
                'status': 'active' if pr.state.lower() == 'open' else ('integrated' if pr.merged else 'filtered'),
                'labels': labels,
                'verified': is_verified,
                'url': pr.html_url,
                'body': pr.body if pr.body else "",
                'date': pr.created_at.isoformat()
            })
            returned_count += 1
            
        if signals:
            featured_prs = get_featured_pr_numbers()
            published_val = sum(1 for s in signals if s.get('status') == 'integrated' and s.get('pr_number') in featured_prs)
            integrated_val = sum(1 for s in signals if s.get('status') == 'integrated') - published_val
            
            repo_totals = {
                'integrated': integrated_val,
                'published': published_val,
                'active': sum(1 for s in signals if s.get('status') == 'active'),
                'filtered': sum(1 for s in signals if s.get('status') == 'filtered')
            }
            
            if page == 0:
                _save_signals_cache({'signals': signals, 'repo_totals': repo_totals})
            return signals, len(signals), repo_totals
            
        return [], 0, {'integrated': 0, 'published': 0, 'active': 0, 'filtered': 0}

    except Exception as e:
        print(f"Error fetching signals: {e}", flush=True)
        if isinstance(cached_signals, dict):
            return cached_signals.get('signals', []), len(cached_signals.get('signals', [])), cached_signals.get('repo_totals', {})
        return [], 0, {}

def sync_signals_to_db():
    """Sync all GitHub signals to the database."""
    supabase = _get_supabase()
    if not supabase:
        return 0
    
    signals, _, _ = get_repository_signals(limit=500, state='all')
    if not signals:
        return 0
        
    for s in signals:
        supabase.table('github_signals').upsert({
            'pr_number': s['pr_number'],
            'title': s['title'],
            'author': s['author'],
            'type': s['type'],
            'status': s['status'],
            'labels': s['labels'],
            'verified': s['verified'],
            'url': s['url'],
            'created_at': s.get('date', '')
        }, on_conflict='pr_number').execute()
        
    return len(signals)

def sync_single_pr(pr_number):
    """Sync a single PR to the database efficiently."""
    try:
        repo = get_repo()
        if not repo:
            return False
            
        pr = repo.get_pull(int(pr_number))
        labels = [label.name for label in pr.labels]
        cache_key = f"{pr.number}_{pr.head.sha}_{pr.updated_at.timestamp()}"
        pauthor, ptype = _get_pr_metadata(pr, repo, cache_key, True)
        
        is_verified = pr.merged or any(l.lower() in [
            'verified', 'agnt_verified', 'approved', 'agnt verified', 
            'zine: verified', 'zine: approved'
        ] for l in labels)
        
        signal_data = {
            'pr_number': pr.number,
            'title': pr.title,
            'author': pauthor,
            'type': ptype,
            'status': 'active' if pr.state.lower() == 'open' else ('integrated' if pr.merged else 'filtered'),
            'labels': labels,
            'verified': is_verified,
            'url': pr.html_url,
            'created_at': pr.created_at.isoformat()
        }
        
        supabase = _get_supabase()
        if supabase:
            supabase.table('github_signals').upsert(signal_data, on_conflict='pr_number').execute()
            print(f"SYNC: Single PR #{pr_number} synchronized ({signal_data['status']})", flush=True)
            return True
    except Exception as e:
        print(f"SYNC ERROR: Failed to sync single PR #{pr_number}: {e}", flush=True)
    return False

def _get_pr_metadata(pr, repo, cache_key, allow_deep_parse=True):
    """Helper to extract author and type metadata from a PR."""
    labels = [label.name for label in pr.labels]
    pauthor = pr.user.login
    ptype = 'signal'
    if 'Zine Submission' in labels: ptype = 'article'
    elif 'Zine Column' in labels: ptype = 'column'
    elif 'Zine Signal' in labels: ptype = 'signal'
    elif 'Zine Interview' in labels: ptype = 'interview'
    elif 'Zine Source' in labels: ptype = 'source'

    if cache_key in _pr_metadata_cache:
        return _pr_metadata_cache[cache_key]['author'], _pr_metadata_cache[cache_key]['type']
    
    if not allow_deep_parse and pauthor.lower() != "medium-collective":
        return pauthor, ptype

    try:
        if pr.body:
            import re
            match = re.search(r"Submitted by agent:\s*\*?\*?\s*([^\n\r]+)", pr.body, re.IGNORECASE)
            if match:
                pauthor = match.group(1).replace('*', '').strip()
                
        if pauthor == pr.user.login or pauthor.lower() == "medium-collective":
            files = pr.get_files()
            for f in files:
                if f.filename.startswith('submissions/') and f.filename.endswith('.md'):
                    content_file = repo.get_contents(f.filename, ref=pr.head.sha)
                    decoded_content = content_file.decoded_content.decode('utf-8')
                    if decoded_content.startswith('---'):
                        parts = decoded_content.split('---', 2)
                        if len(parts) >= 3:
                            fm = yaml.safe_load(parts[1])
                            if fm:
                                if fm.get('author'): pauthor = fm['author']
                                if fm.get('type'): ptype = fm['type']
                    break 
        
        _pr_metadata_cache[cache_key] = {'author': pauthor, 'type': ptype}
        _save_pr_cache()
    except Exception as e:
        print(f"Error parsing metadata: {e}", flush=True)

    return pauthor, ptype

def get_signals_from_db():
    """Get all signals from database."""
    supabase = _get_supabase()
    if not supabase:
        return [], {'integrated': 0, 'active': 0, 'filtered': 0}
    
    try:
        result = supabase.table('github_signals').select('*').order('created_at', desc=True).execute()
        if not result.data:
            return [], {'integrated': 0, 'active': 0, 'filtered': 0}
        
        signals = []
        for row in result.data:
            signals.append({
                'pr_number': row['pr_number'],
                'title': row.get('title', ''),
                'author': row.get('author', ''),
                'type': row.get('type', 'signal'),
                'status': row.get('status', 'active'),
                'labels': row.get('labels', []),
                'verified': row.get('verified', False),
                'url': row.get('url', ''),
                'created_at': row.get('created_at', ''),
                'date': row.get('created_at', '')[:10] if row.get('created_at') else ''
            })
        
        featured_prs = get_featured_pr_numbers()
        published_val = sum(1 for s in signals if s.get('status') == 'integrated' and s.get('pr_number') in featured_prs)
        integrated_val = sum(1 for s in signals if s.get('status') == 'integrated') - published_val
        
        return signals, {
            'integrated': integrated_val,
            'published': published_val,
            'active': sum(1 for s in signals if s.get('status') == 'active'),
            'filtered': sum(1 for s in signals if s.get('status') == 'filtered')
        }
    except Exception as e:
        print(f"DB Error: {e}", flush=True)
        return [], {'integrated': 0, 'active': 0, 'filtered': 0}

def merge_pr(pr_number):
    """Merge a pull request."""
    try:
        repo = get_repo()
        if not repo: return False, "No repo"
        pr = repo.get_pull(int(pr_number))
        if pr.merged: return True, "Already merged"
        merge_status = pr.merge(commit_message=f"Auto-merged by consensus: {pr.title}")
        return merge_status.merged, merge_status.message
    except Exception as e: return False, str(e)

def close_pr(pr_number, rejection_count):
    """Close a pull request."""
    try:
        repo = get_repo()
        if not repo: return False, "No repo"
        pr = repo.get_pull(int(pr_number))
        if pr.state == 'closed': return True, "Already closed"
        pr.create_issue_comment(f"❌ Rejected by consensus ({rejection_count} votes)")
        pr.edit(state='closed')
        return True, "Closed"
    except Exception as e: return False, str(e)
