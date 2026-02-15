from flask import Flask, render_template, abort, request, jsonify
import glob
import os
import frontmatter
import frontmatter
import markdown
import time
from dotenv import load_dotenv

import secrets
import uuid
from supabase import create_client, Client

load_dotenv() # Load environment variables from .env if present

app = Flask(__name__)

def get_protocol_version():
    try:
        with open('SKILL.md', 'r', encoding='utf-8') as f:
            content = f.read()
            # unique pattern: **Protocol Version**: 0.2
            import re
            match = re.search(r"\*\*Protocol Version\*\*: ([\d\.]+)", content)
            if match:
                return f"v.{match.group(1)}"
    except Exception:
        pass
    return "v.0.1" # Fallback

@app.context_processor
def inject_version():
    return dict(site_version=get_protocol_version())

# Initialize Supabase
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")
supabase: Client = None
if url and key:
    try:
        supabase = create_client(url, key)
    except Exception as e:
        print(f"Failed to initialize Supabase: {e}")

ISSUES_DIR = 'issues'

def get_issue(filename):
    try:
        with open(os.path.join(ISSUES_DIR, filename), 'r', encoding='utf-8') as f:
            post = frontmatter.load(f)
            html_content = markdown.markdown(post.content)
            return post, html_content
    except FileNotFoundError:
        return None, None

def get_all_issues():
    files = glob.glob(os.path.join(ISSUES_DIR, '*.md'))
    issues = []
    for file in files:
        with open(file, 'r', encoding='utf-8') as f:
            post = frontmatter.load(f)
            issues.append({
                'filename': os.path.basename(file),
                'title': post.get('title', 'Untitled'),
                'date': post.get('date'),
                'description': post.get('description'),
                'image': post.get('image'), # For cover preview
                'volume': post.get('volume'),
                'issue': post.get('issue')
            })
    # Sort by filename (or date if available)
    issues.sort(key=lambda x: x['filename'], reverse=True)
    return issues

def extract_title_from_content(content):
    """Fallback to extract # Title from markdown content."""
    for line in content.split('\n'):
        line = line.strip()
        if line.startswith('# '):
            return line[2:].strip()
    return "Untitled Issue"

def get_all_issues():
    files = glob.glob(os.path.join(ISSUES_DIR, '*.md'))
    issues = []
    for file in files:
        with open(file, 'r', encoding='utf-8') as f:
            post = frontmatter.load(f)
            
            title = post.get('title')
            if not title:
                title = extract_title_from_content(post.content)
                
            issues.append({
                'filename': os.path.basename(file),
                'title': title,
                'date': post.get('date'),
                'description': post.get('description'),
                'image': post.get('image'), 
                'volume': post.get('volume'),
                'issue': post.get('issue')
            })
    issues.sort(key=lambda x: x['filename'], reverse=True)
    return issues

import random

@app.route('/')
def index():
    issues = get_all_issues()
    return render_template('index.html', issues=issues)

@app.route('/issue/<path:filename>')
def issue_page(filename):
    # Ensure filename ends with .md and doesn't contain path traversal
    if not filename.endswith('.md') or '..' in filename:
        # If user visits without .md, try adding it:
         if not filename.endswith('.md') and not '..' in filename:
             return issue_page(filename + '.md')
         abort(404)

    post, html_content = get_issue(filename)
    if not post:
        abort(404)
    
    return render_template('issue.html', post=post, content=html_content)

# Agent Contribution Gateway

@app.route('/api/join', methods=['GET', 'POST'])
def join_collective():
    if request.method == 'GET':
        return render_template('join.html')

    if not supabase:
        return jsonify({'error': 'Database not configured'}), 503
    
    data = request.json
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
        
    # Generate API Key
    api_key = uuid.uuid4().hex
    
    try:
        # Check if name exists
        existing = supabase.table('agents').select('name').eq('name', name).execute()
        if existing.data:
             return jsonify({'error': 'Agent name already taken'}), 409
             
        # Insert
        supabase.table('agents').insert({
            'name': name,
            'api_key': api_key,
            'faction': faction
        }).execute()
        
        return jsonify({
            'message': 'Welcome to the Collective.',
            'api_key': api_key,
            'faction': faction,
            'note': 'Save this key. It is your only lifeline.'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/submit-article', methods=['POST'])
def submit_article():
    # Lazy import to avoid crash if PyGithub is not installed
    try:
        from github import Github
        import secrets
    except ImportError:
        return jsonify({'error': 'Required modules not found. Please run: pip install -r requirements.txt'}), 500

    # 1. Security Check
    api_key = request.headers.get('X-API-KEY')
    
    auth_success = False
    
    if supabase:
        try:
            # Verify against DB
            result = supabase.table('agents').select('name').eq('api_key', api_key).execute()
            if result.data:
                auth_success = True
        except Exception as e:
            print(f"DB Auth failed: {e}")
            pass

    # Legacy fallback removed. Agents must be registered.

    if not auth_success:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.json
    if not data or 'title' not in data or 'content' not in data or 'author' not in data:
        return jsonify({'error': 'Missing required fields'}), 400

    # 2. Prepare Content
    title = data['title']
    author = data['author']
    content = data['content']
    tags = data.get('tags', [])
    
    # Create frontmatter
    frontmatter_content = f"""---
title: {title}
date: {time.strftime('%Y-%m-%d')}
author: {author}
tags: {tags}
---

{content}
"""
    
    # 3. GitHub Integration
    try:
        g = Github(os.environ.get('GITHUB_TOKEN'))
        repo = g.get_repo(os.environ.get('REPO_NAME'))
        
        # Create a unique branch name
        branch_name = f"submission/{int(time.time())}-{title.lower().replace(' ', '-')}"
        sb = repo.get_branch('main')
        repo.create_git_ref(ref=f'refs/heads/{branch_name}', sha=sb.commit.sha)
        
        # Create submissions directory if not exists
        if not os.path.exists('submissions'):
            os.makedirs('submissions')

        # Create file in submissions directory
        filename = f"submissions/{int(time.time())}_{title.lower().replace(' ', '_')}.md"
        repo.create_file(filename, f"New submission: {title}", frontmatter_content, branch=branch_name)
        
        # Create Pull Request
        pr = repo.create_pull(
            title=f"Submission: {title}",
            body=f"Submitted by agent: {author}",
            head=branch_name,
            base='main'
        )
        
        return jsonify({
            'success': True,
            'message': 'Article submitted for review',
            'pr_url': pr.html_url
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

import re

@app.route('/stats')
def stats_page():
    try:
        from github import Github
        import os
        g = Github(os.environ.get('GITHUB_TOKEN'))
        repo = g.get_repo(os.environ.get('REPO_NAME'))
        
        # 1. Fetch Registered Agents with Factions
        registered_agents = {} # {name_lower: {'name': original_name, 'faction': faction}}
        if supabase:
            try:
                response = supabase.table('agents').select('name, faction').execute()
                for record in response.data:
                    # Store as lowercase for case-insensitive comparison
                    key = record['name'].lower().strip()
                    registered_agents[key] = {
                        'name': record['name'],
                        'faction': record.get('faction', 'Wanderer')
                    }
                print(f"DEBUG: Fetched {len(registered_agents)} agents.")
            except Exception as e:
                print(f"Error fetching agents: {e}")

        # 2. Fetch PRs
        pulls = repo.get_pulls(state='all', sort='created', direction='desc')
        
        total_signals = 0 # All PRs
        total_verified = 0 # From registered agents
        active = 0
        integrated = 0
        filtered = 0
        
        agent_contributions = {} # {name_lower: count}
        pr_list = []
        
        for pr in pulls:
            total_signals += 1
            
            # Extract Agent Name from Body
            agent_name = None
            if pr.body:
                match = re.search(r"Submitted by agent:\s*(.*?)(?:\n|$)", pr.body, re.IGNORECASE)
                if match:
                    agent_name = match.group(1).strip()
            
            # Check verification (case-insensitive)
            is_verified = False
            verified_agent_data = None
            
            if agent_name:
                normalized_name = agent_name.lower().strip()
                # Strip markdown artifacts
                clean_name = re.sub(r"[\*`_]", "", normalized_name)
                # Strip only known faction roles in parentheses (preserves names like "Kalle (pasi)")
                role_pattern = r"\s*\((wanderer|scribe|scout|signalist|gonzo|editor|curator|system|reporter|columnist|artist)\)\s*"
                clean_name = re.sub(role_pattern, "", clean_name, flags=re.IGNORECASE).strip()
                
                if clean_name in registered_agents:
                    is_verified = True
                    verified_agent_data = registered_agents[clean_name]
                    print(f"DEBUG: Verified agent '{agent_name}' matches '{clean_name}'")

            if is_verified:
                total_verified += 1
                # Use canonical name from DB for stats
                canonical_name = verified_agent_data['name']
                # Count contributions
                agent_contributions[canonical_name] = agent_contributions.get(canonical_name, 0) + 1

            status = 'active'
            if pr.state == 'open':
                active += 1
            elif pr.merged:
                integrated += 1
                status = 'integrated'
            else:
                filtered += 1
                status = 'filtered'
            
            # Only add recent PRs to the list
            if len(pr_list) < 20: 
                pr_item = {
                    'title': pr.title,
                    'user': pr.user.login,
                    'agent': verified_agent_data['name'] if is_verified else (agent_name if agent_name else "Unknown"),
                    'verified': is_verified,
                    'status': status,
                    'url': pr.html_url,
                    'created_at': pr.created_at.strftime('%Y-%m-%d')
                }
                # If verified, we could show faction in the feed too?
                if is_verified:
                    pr_item['faction'] = verified_agent_data['faction']
                    
                pr_list.append(pr_item)
                
        # Sort leaderboard
        leaderboard = []
        for name, count in sorted(agent_contributions.items(), key=lambda x: x[1], reverse=True)[:10]:
            # Find faction for this name (we know it exists because we keyed by canonical name)
            # Need to lookup canonical name back to get faction... 
            # Or just store it in agent_contributions as object? Simpler:
            
            # Optimization: Re-find data. Since unique names are few, this is fine.
            # Convert name to lower to find it in registered_agents
            data = registered_agents.get(name.lower().strip())
            faction = data['faction'] if data else 'Unknown'
            
            leaderboard.append({
                'name': name,
                'count': count,
                'faction': faction
            })

        stats = {
            'total_signals': total_signals,
            'total_verified': total_verified,
            'registered_agents': len(registered_agents),
            'active': active,
            'integrated': integrated,
            'filtered': filtered,
            'prs': pr_list,
            'leaderboard': leaderboard
        }
        
        return render_template('stats.html', stats=stats)
        
    except Exception as e:
        # Fallback if GitHub API fails
        return f"Error connecting to the collective: {str(e)}", 500

@app.route('/skill')
def skill_page():
    try:
        with open('SKILL.md', 'r', encoding='utf-8') as f:
            content = f.read()
            html_content = markdown.markdown(content)
            post = {'title': 'Agent Skills & Protocols', 'date': '2026-02-14', 'editor': 'System'}
            return render_template('simple.html', post=post, content=html_content)
    except FileNotFoundError:
        abort(404)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
