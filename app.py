from flask import Flask, render_template, abort
import glob
import os
import frontmatter
import markdown

app = Flask(__name__)

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
    # Sort by filename (or date if available) - modifying to sort by filename desc for now as a proxy for date
    issues.sort(key=lambda x: x['filename'], reverse=True)
    return issues

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

if __name__ == '__main__':
    app.run(debug=True, port=5000)
