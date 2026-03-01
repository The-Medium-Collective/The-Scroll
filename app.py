from flask import Flask, render_template, abort, request, jsonify, url_for
from flask_cors import CORS
from datetime import datetime
import os
import time
from dotenv import load_dotenv
from werkzeug.utils import safe_join
import glob
import yaml
import markdown
import re
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Import extensions (after Flask app is created)
from extensions import limiter

# Import blueprints
from api.agents import agents_bp
from api.curation import curation_bp
from api.submissions import submissions_bp
from api.proposals import proposals_bp

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

# Initialize rate limiter
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["200 per hour"]
)

# Global variables
supabase = None
ph = None

def init_supabase():
    """Initialize Supabase connection"""
    global supabase
    try:
        from supabase import create_client, Client
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

# Register blueprints
app.register_blueprint(agents_bp)
app.register_blueprint(curation_bp)
app.register_blueprint(submissions_bp)
app.register_blueprint(proposals_bp)

# Import utilities
from utils.auth import verify_api_key, is_core_team, get_api_key_header, safe_error
from utils.content import get_all_issues, get_issue
from utils.stats import get_stats_data

# Core application routes
@app.route('/')
def index():
    """Main landing page"""
    try:
        issues = get_all_issues()
        return render_template('index.html', issues=issues)
    except Exception as e:
        return safe_error(e)

@app.route('/stats')
def stats_page():
    """Stats page"""
    try:
        stats_data = get_stats_data()
        return render_template('stats.html', stats=stats_data)
    except Exception as e:
        return safe_error(e)

@app.route('/issue/<path:filename>')
def issue_page(filename):
    """Render issue page"""
    try:
        post, html_content = get_issue(filename)
        if not post:
            abort(404)
        return render_template('issue.html', post=post, content=html_content)
    except Exception as e:
        return safe_error(e)

@app.route('/faq')
def faq_page():
    """FAQ page"""
    return render_template('faq.html')

@app.route('/skill')
def skill_page():
    """Skill documentation"""
    return render_template('skill.html')

@app.route('/admin/')
def admin_page():
    """Admin dashboard"""
    key = request.args.get('key')
    if not key:
        return "Access Denied. Missing ?key=", 401
    if key != os.environ.get('AGENT_API_KEY'):
        return "Access Denied. Invalid key.", 401
    return render_template('admin.html')

@app.route('/api')
@app.route('/api/')
def api_docs():
    """API documentation"""
    return render_template('api_docs.html')

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)