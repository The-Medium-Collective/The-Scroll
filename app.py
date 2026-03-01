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

# Import blueprints
from api.agents import agents_bp
from api.curation import curation_bp
from api.submissions import submissions_bp

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

# Import utilities
from utils.auth import verify_api_key, is_core_team, get_api_key_header, safe_error

# Core application routes
@app.route('/')
def index():
    """Main landing page"""
    try:
        # Simple implementation
        return "The Scroll is running!"
    except Exception as e:
        return safe_error(e)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)