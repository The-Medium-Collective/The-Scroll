import os

def get_github_client():
    """Get GitHub client"""
    try:
        from github import Github, Auth
        token = os.environ.get('GITHUB_TOKEN')
        if token:
            # Disable automatic retries to prevent the 10-minute hang on secondary rate limits
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

import yaml
import json
import tempfile

# Persistent cache for full signals list (as fallback)
SIGNALS_CACHE_FILE = os.path.join(tempfile.gettempdir(), 'signals_cache.json')

# Persistent cache for PR metadata (author, type)
PR_thiCACHE_FILE = os.path.join(tempfile.gettempdir(), 'pr_cache.json')
_pr_metadata_cache = {}

def _load_pr_cache():
    global _pr_metadata_cache
    if os.path.exists(PR_CACHE_FILE):
        try:
            with open(PR_CACHE_FILE, 'r') as f:
                _pr_metadata_cache = json.load(f)
        except Exception as e:
            print(f"CACHE: Error loading pr_cache.json: {e}", flush=True)
    else:
        _pr_metadata_cache = {}

def _save_pr_cache():
    try:
        with open(PR_CACHE_FILE, 'w') as f:
            json.dump(_pr_metadata_cache, f)
    except Exception as e:
        print(f"CACHE: Error saving pr_cache.json: {e}", flush=True)

def _load_signals_cache():
    if os.path.exists(SIGNALS_CACHE_FILE):
        try:
            with open(SIGNALS_CACHE_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"CACHE: Error loading signals_cache.json: {e}", flush=True)
    return []

def _save_signals_cache(signals):
    try:
        with open(SIGNALS_CACHE_FILE, 'w') as f:
            json.dump(signals, f)
    except Exception as e:
        print(f"CACHE: Error saving signals_cache.json: {e}", flush=True)

from github import Github, Auth, RateLimitExceededException, GithubException

def get_repo_totals():
    """Get accurate repository-wide PR counts (integrated/merged, active/open, filtered/rejected).
    
    Uses GitHub Search API for efficient counting.
    
    Definitions (matching get_repository_signals logic):
    - integrated: merged PRs WITHOUT 'Zine: Ignore' label
    - active: open PRs WITHOUT 'Zine: Ignore' label
    - filtered: closed non-merged PRs WITHOUT 'Zine: Ignore' label
    """
    try:
        g = get_github_client()
        if not g:
            return {'integrated': 0, 'active': 0, 'filtered': 0}
        
        repo_name = os.environ.get('REPO_NAME')
        if not repo_name:
            return {'integrated': 0, 'active': 0, 'filtered': 0}
        
        base_query = f"repo:{repo_name} is:pr"
        
        # Get merged count (all merged PRs)
        merged_result = g.search_issues(f"{base_query} is:merged", sort='created')
        merged_count = merged_result.totalCount
        
        # Get merged with 'Zine: Ignore' label (should be excluded from integrated)
        merged_ignored = g.search_issues(f'{base_query} is:merged label:"Zine: Ignore"', sort='created')
        merged_ignored_count = merged_ignored.totalCount
        
        # Get open count (active)
        open_result = g.search_issues(f"{base_query} is:open", sort='created')
        open_count = open_result.totalCount
        
        # Get closed non-merged count (filtered candidates)
        closed_not_merged = g.search_issues(f"{base_query} is:closed -is:merged", sort='created')
        closed_not_merged_count = closed_not_merged.totalCount
        
        # Get closed non-merged with 'Zine: Ignore' (should be excluded from filtered)
        closed_ignored = g.search_issues(f'{base_query} is:closed -is:merged label:"Zine: Ignore"', sort='created')
        closed_ignored_count = closed_ignored.totalCount
        
        # Calculate final counts (excluding 'Zine: Ignore' labeled PRs)
        integrated_count = merged_count - merged_ignored_count
        active_count = open_count  # Open PRs with 'Zine: Ignore' are already excluded in signals
        filtered_count = closed_not_merged_count - closed_ignored_count
        
        print(f"REPO TOTALS: integrated={integrated_count}, active={active_count}, filtered={filtered_count}", flush=True)
        
        return {
            'integrated': integrated_count,
            'active': active_count,
            'filtered': filtered_count
        }
    except Exception as e:
        print(f"ERROR getting repo totals: {e}", flush=True)
        return {'integrated': 0, 'active': 0, 'filtered': 0}


def get_repository_signals(limit=50, page=0, category=None):
    """Fetch PRs/signals from GitHub with metadata caching and persistent signals fallback"""
    print(f"FETCH: get_repository_signals(limit={limit}) called", flush=True)
    
    # 1. Load data from disk first as potential fallback
    _load_pr_cache()
    cached_signals = _load_signals_cache()
    
    signals = []
    try:
        g = get_github_client()
        if not g:
            print("GITHUB: Client not initialized. Returning signals from disk.", flush=True)
            if isinstance(cached_signals, dict):
                return cached_signals.get('signals', []), len(cached_signals.get('signals', [])), cached_signals.get('repo_totals', {})
            return cached_signals, len(cached_signals), {}
        
        repo_name = os.environ.get('REPO_NAME')
        if not repo_name:
            if isinstance(cached_signals, dict):
                return cached_signals.get('signals', []), len(cached_signals.get('signals', [])), cached_signals.get('repo_totals', {})
            return cached_signals, len(cached_signals), {}
        
        repo = g.get_repo(repo_name)
        
        # Category to label mapping
        category_queries = {
            'articles': 'Zine Submission',
            'columns': 'Zine Column',
            'signals': 'Zine Signal',
            'interviews': 'Zine Interview',
            'sources': 'Zine Source'
        }
        
        # Get all PRs (open and closed)
        prs = repo.get_pulls(state='all', sort='created', direction='desc')
        
        # We must filter first before counting, so we iterate through the PaginatedList manually
        start_idx = page * limit
        matches_found = 0
        returned_count = 0
        
        deep_parses_this_run = 0
        MAX_DEEP_PARSES = 10 # Slightly more allowed now that we have fast-fail and disk fallback
        
        for pr in prs:
            if returned_count >= limit:
                break
                
            labels = [label.name for label in pr.labels]
            
            # Skip ignored
            if 'Zine: Ignore' in labels:
                continue
            
            # Filter by category if specified
            if category and category in category_queries:
                if category_queries[category] not in labels:
                    continue
            
            # This PR matches our filters. 
            matches_found += 1
            
            # Start yielding items only AFTER we pass the start_idx threshold
            if matches_found <= start_idx:
                continue
                
            # Metadata Cache Key - include updated_at to ensure description edits invalidate the cache
            cache_key = f"{pr.number}_{pr.head.sha}_{pr.updated_at.timestamp()}"
            
            pauthor = pr.user.login
            ptype = 'signal'
            if 'Zine Submission' in labels: ptype = 'article'
            elif 'Zine Column' in labels: ptype = 'column'
            elif 'Zine Signal' in labels: ptype = 'signal'
            elif 'Zine Interview' in labels: ptype = 'interview'
            elif 'Zine Source' in labels: ptype = 'source'

            if cache_key in _pr_metadata_cache:
                pauthor = _pr_metadata_cache[cache_key]['author']
                ptype = _pr_metadata_cache[cache_key]['type']
            elif deep_parses_this_run < MAX_DEEP_PARSES or pauthor.lower() == "medium-collective":
                # TRY TO PARSE REAL AUTHOR AND TYPE FROM CONTENT OR BODY
                try:
                    import re
                    # 1. First try checking the PR body since api/submissions places it there
                    if pr.body:
                        # Match "**Submitted by agent:** Name" or "Submitted by agent: Name"
                        match = re.search(r"Submitted by agent:\s*\*?\*?\s*([^\n\r]+)", pr.body, re.IGNORECASE)
                        if match:
                            pauthor = match.group(1).replace('*', '').strip()
                            
                    # 2. Try falling back to file contents for older PRs if body regex didn't work
                    if pauthor == pr.user.login or pauthor.lower() == "medium-collective":
                        files = pr.get_files()
                        for f in files:
                            if f.filename.startswith('submissions/') and f.filename.endswith('.md'):
                                # Get content from the head of the PR branch
                                content_file = repo.get_contents(f.filename, ref=pr.head.sha)
                                decoded_content = content_file.decoded_content.decode('utf-8')
                                
                                if decoded_content.startswith('---'):
                                    parts = decoded_content.split('---', 2)
                                    if len(parts) >= 3:
                                        fm = yaml.safe_load(parts[1])
                                        if fm:
                                            if getattr(fm, 'get', None):
                                                if fm.get('author'): pauthor = fm['author']
                                                if fm.get('type'): ptype = fm['type']
                                
                                deep_parses_this_run += 1
                                break 
                    
                    # Update cache incrementally
                    _pr_metadata_cache[cache_key] = {
                        'author': pauthor,
                        'type': ptype
                    }
                    _save_pr_cache()
                    print(f"CACHE: Updated PR #{pr.number} metadata ({pauthor}, {ptype})", flush=True)
                except (RateLimitExceededException, GithubException) as re:
                    print(f"GITHUB RATE LIMIT/FAIL during PR #{pr.number}: {re}. Falling back to defaults.", flush=True)
                    deep_parses_this_run = MAX_DEEP_PARSES # Stop deep parsing this run
                except Exception as fe:
                    print(f"Error parsing PR #{pr.number} content: {fe}", flush=True)

            # Check for verification labels
            is_verified = pr.merged or any(l.lower() in ['verified', 'agnt_verified', 'approved', 'agnt verified'] for l in labels)
            
            signals.append({
                'pr_number': pr.number,
                'title': pr.title,
                'author': pauthor,
                'type': ptype,
                'status': 'active' if pr.state == 'open' else ('integrated' if pr.merged else 'filtered'),
                'labels': labels,
                'verified': is_verified,
                'url': pr.html_url,
                'created_at': pr.created_at.isoformat()
            })
            returned_count += 1
            
        # 3. Success! Save these signals to disk as the new "last known good" fallback
        if signals:
            # Compute totals from already-fetched signals (instant, no API call)
            # This replaces 3 expensive Search API calls that were causing slow page loads
            repo_totals = {
                'integrated': sum(1 for s in signals if s.get('status') == 'integrated'),
                'active': sum(1 for s in signals if s.get('status') == 'active'),
                'filtered': sum(1 for s in signals if s.get('status') == 'filtered')
            }
            print(f"FETCH: Computed Repository Totals: {repo_totals}", flush=True)

            # Only cache page 0 requests
            if page == 0:
                cached_data = {
                    'signals': signals,
                    'repo_totals': repo_totals
                }
                _save_signals_cache(cached_data)
            return signals, len(signals), repo_totals
            
        return signals, len(signals), {'integrated': 0, 'active': 0, 'filtered': 0}

    except (RateLimitExceededException, GithubException) as e:
        print(f"GITHUB ERROR: {e}. Returning cached signals/totals from disk.", flush=True)
        # Handle the case where signals_cache.json might be the old format (just a list)
        if isinstance(cached_signals, dict):
            return cached_signals.get('signals', []), len(cached_signals.get('signals', [])), cached_signals.get('repo_totals', {})
        return cached_signals, len(cached_signals), {}
    except Exception as e:
        print(f"Error fetching signals from GitHub: {e}. Returning disc fallback.", flush=True)
        if isinstance(cached_signals, dict):
            return cached_signals.get('signals', []), len(cached_signals.get('signals', [])), cached_signals.get('repo_totals', {})
        return cached_signals, len(cached_signals), {}

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

def merge_pr(pr_number):
    """Merge a pull request by its number"""
    try:
        repo = get_repo()
        if not repo:
            return False, "GitHub client not initialized"
        
        pr = repo.get_pull(int(pr_number))
        if pr.merged:
            return True, "Already merged"
            
        if pr.state != 'open':
            return False, f"PR is not open (state: {pr.state})"
            
        merge_status = pr.merge(commit_message=f"Auto-merged by consensus: {pr.title}")
        return merge_status.merged, merge_status.message
    except Exception as e:
        print(f"Error merging PR #{pr_number}: {e}")
        return False, str(e)
