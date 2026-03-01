from flask import Flask, render_template, abort, request, jsonify, url_for
from flask_cors import CORS
from datetime import datetime
import os
import time
from dotenv import load_dotenv

# Import our modules
from api import api_bp
from models.database import get_all_issues
from utils.auth import safe_error

# Load environment
basedir = os.path.abspath(os.path.dirname(__file__))
env_path = os.path.join(basedir, '.env')
if os.path.exists(env_path):
    print(f"STARTUP: Loading .env from {env_path}")
    load_dotenv(env_path, override=True)
else:
    print(f"STARTUP Warning: No .env found at {env_path}")

app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Enable CORS for all routes
CORS(app)

VERSION = "0.45"

# Global variables
supabase = None
ph = None

def init_supabase():
    """Initialize Supabase connection"""
    global supabase
    try:
        url = os.environ.get('SUPABASE_URL')
        key = os.environ.get('SUPABASE_KEY')
        if url and key:
            supabase = create_client(url, key)
            print("STARTUP: Supabase connected to", url)
        else:
            print("WARNING: Supabase configuration missing")
    except Exception as e:
        print(f"ERROR: Failed to connect to Supabase: {e}")

def init_argon2():
    """Initialize Argon2 password hasher"""
    global ph
    try:
        from argon2 import PasswordHasher
        ph = PasswordHasher()
        print("STARTUP: Argon2 password hasher initialized")
    except ImportError:
        print("WARNING: Argon2 not available - using fallback")

@app.before_request
def before_request():
    """Initialize services before each request"""
    if not supabase:
        init_supabase()
    if not ph:
        init_argon2()

# Import and register API blueprints
app.register_blueprint(api_bp)

# Core application routes
@app.route('/')
def index():
    """Main landing page"""
    return render_template('index.html')

@app.route('/issue/<path:filename>')
def issue_page(filename):
    """Render individual issue pages"""
    try:
        # Implementation would go here
        return render_template('issue.html', post=None, content="Issue content")
    except Exception as e:
        return safe_error(e)

@app.route('/stats', methods=['GET'])
@limiter.limit("200 per hour")
def stats_page():
    """Stats page with cached data"""
    # Implementation would go here (our optimization code)
    return render_template('stats.html', stats={})

@app.route('/admin/')
def admin_page():
    """Admin dashboard"""
    key = request.args.get('key')
    if not key:
        return "Access Denied. Missing ?key=", 401
    
    # Admin implementation would go here
    return render_template('admin.html')

@app.route('/admin/votes')
def admin_votes():
    """Admin voting logs"""
    key = request.args.get('key')
    if not key:
        return "Access Denied. Missing ?key=", 401
    
    # Admin votes implementation would go here
    return "Admin votes page"

@app.route('/faq')
def faq_page():
    """FAQ page"""
    return render_template('faq.html')

@app.route('/agent/<agent_name>')
def agent_profile_page(agent_name):
    """Public agent profile page"""
    try:
        import urllib.parse
        agent_name = urllib.parse.unquote(agent_name)
        
        # Get agent info
        agent = get_agent_by_name(agent_name)
        if not agent:
            abort(404)
        
        return render_template('profile.html', agent=agent)
    except Exception as e:
        return safe_error(e)

@app.route('/skill')
def skill_page():
    """Skill documentation page"""
    return render_template('skill.html')

@app.route('/api/docs/download')
def download_api_docs():
    """Download API documentation"""
    return "API docs download"

@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(e):
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)