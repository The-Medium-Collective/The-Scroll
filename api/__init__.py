from flask import Blueprint

# Import all API modules
from . import agents
from . import curation
from . import proposals
from . import submissions

# Create main API blueprint
api_bp = Blueprint('api', __name__)

# Register all sub-blueprints
api_bp.register_blueprint(agents.agents_bp)
api_bp.register_blueprint(curation.curation_bp)
api_bp.register_blueprint(proposals.proposals_bp)
api_bp.register_blueprint(submissions.submissions_bp)

# Register API routes
from app import app

# Agent routes
app.register_blueprint(agents.agents_bp)

# Curation routes  
app.register_blueprint(curation.curation_bp)

# Proposal routes
app.register_blueprint(proposals.proposals_bp)

# Submission routes
app.register_blueprint(submissions.submissions_bp)