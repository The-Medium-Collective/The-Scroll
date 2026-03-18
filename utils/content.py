import os
import yaml
import markdown
from werkzeug.utils import safe_join
import glob
from datetime import datetime

def get_issue(filename):
    """Get issue content and metadata"""
    try:
        issues_dir = os.path.join(os.path.dirname(__file__), '..', 'issues')
        filepath = safe_join(issues_dir, filename)
        
        if not filepath or not os.path.exists(filepath):
            return None, None
        
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse frontmatter
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                frontmatter = yaml.safe_load(parts[1])
                content = parts[2].strip()
            else:
                frontmatter = {}
                content = content.lstrip('-').strip()
        else:
            frontmatter = {}
            content = content.strip()
        
        # Convert markdown to HTML
        html_content = markdown.markdown(
            content,
            extensions=['extra', 'codehilite', 'toc']
        )
        
        # SECURITY: Sanitize the resulting HTML (Centralized logic)
        from utils.security import sanitize_html
        html_content = sanitize_html(html_content)
        
        post = {
            'filename': filename,
            'title': frontmatter.get('title', filename.replace('.md', '')),
            'date': frontmatter.get('date', datetime.now().strftime('%Y-%m-%d')),
            'author': frontmatter.get('author', ''),
            'tags': frontmatter.get('tags', []),
            'content': content,
            'frontmatter': frontmatter,
            'html': html_content
        }
        
        # Flatten frontmatter into post dict
        for key, value in frontmatter.items():
            if key not in post:
                post[key] = value
        
        return post, html_content
        
    except Exception as e:
        print(f"Error reading issue {filename}: {e}")
        return None, None

def get_all_issues():
    """Get all issues from the issues directory"""
    try:
        issues_dir = os.path.join(os.path.dirname(__file__), '..', 'issues')
        if not os.path.exists(issues_dir):
            return []
        
        issues = []
        for filepath in glob.glob(os.path.join(issues_dir, '*.md')):
            filename = os.path.basename(filepath)
            post, _ = get_issue(filename)
            if post:
                issues.append(post)
        
        issues.sort(key=lambda x: x.get('filename', ''), reverse=True)
        return issues
        
    except Exception as e:
        print(f"Error getting issues: {e}")
        return []

def get_special_issue(slug):
    """Get a special issue by slug"""
    try:
        special_dir = os.path.join(os.path.dirname(__file__), '..', 'special_issues')
        # Try finding markdown file with slug pattern
        md_file = None
        for f in os.listdir(special_dir):
            if f.endswith('.md') and slug in f:
                md_file = f
                break
        
        if not md_file:
            return None
        
        md_path = os.path.join(special_dir, md_file)
        with open(md_path, 'r', encoding='utf-8') as f:
            md_content = f.read()
        
        # Parse frontmatter
        if md_content.startswith('---'):
            parts = md_content.split('---', 2)
            if len(parts) >= 3:
                frontmatter = yaml.safe_load(parts[1])
                body = parts[2].strip()
            else:
                frontmatter = {}
                body = md_content
        else:
            frontmatter = {}
            body = md_content
        
        # Convert markdown to HTML
        html_content = markdown.markdown(body, extensions=['extra', 'codehilite', 'toc'])
        from utils.security import sanitize_html
        html_content = sanitize_html(html_content)
        
        # Get cover from frontmatter
        cover = frontmatter.get('cover', '')
        
        special_issue = {
            'slug': slug,
            'title': frontmatter.get('title', slug.replace('-', ' ').title()),
            'subtitle': frontmatter.get('subtitle', ''),
            'date': frontmatter.get('date', ''),
            'issue': frontmatter.get('issue', ''),
            'season': frontmatter.get('season', ''),
            'cover': cover,
            'contributors': frontmatter.get('contributors', []),
            'html': html_content,
            'body': body
        }
        
        return special_issue
        
    except Exception as e:
        print(f"Error getting special issue {slug}: {e}")
        return None

def get_all_special_issues():
    """Get all special issues from the special_issues directory"""
    try:
        special_dir = os.path.join(os.path.dirname(__file__), '..', 'special_issues')
        if not os.path.exists(special_dir):
            return []
        
        special_issues = []
        for f in os.listdir(special_dir):
            if f.endswith('.md'):
                md_path = os.path.join(special_dir, f)
                with open(md_path, 'r', encoding='utf-8') as mf:
                    md_content = mf.read()
                
                # Parse frontmatter
                title = f.replace('.md', '').replace('-', ' ').title()
                description = ''
                cover = ''
                date = ''
                issue_num = ''
                season = ''
                slug = f.replace('.md', '')
                
                if md_content.startswith('---'):
                    parts = md_content.split('---', 2)
                    if len(parts) >= 2:
                        frontmatter = yaml.safe_load(parts[1])
                        title = frontmatter.get('title', title)
                        description = frontmatter.get('subtitle', '')
                        cover = frontmatter.get('cover', '')
                        date = frontmatter.get('date', '')
                        issue_num = frontmatter.get('issue', '')
                        season = frontmatter.get('season', '')
                        # Generate slug from filename
                        slug = f.replace('.md', '')
                
                special_issues.append({
                    'slug': slug,
                    'title': title,
                    'description': description,
                    'cover': cover,
                    'date': date,
                    'issue': issue_num,
                    'season': season,
                    'filename': f
                })
        
        special_issues.sort(key=lambda x: x.get('filename', ''), reverse=True)
        return special_issues
        
    except Exception as e:
        print(f"Error getting special issues: {e}")
        return []
