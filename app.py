"""Flask application entry point."""
import os
from flask import Flask, render_template
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from dotenv import load_dotenv

from backend.utils.logger import setup_logger

load_dotenv()

app = Flask(__name__)
logger = setup_logger('app')

# Configuration
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
app.config['JSON_SORT_KEYS'] = False
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

allowed_origins = [
    origin.strip()
    for origin in os.getenv(
        'CORS_ORIGINS', 
        'http://localhost:3000,http://localhost:5000,https://data-assistant.onrender.com'
    ).split(',')
    if origin.strip()
]

# Initialize Limiter on app instance BEFORE importing or registering blueprints
limiter = Limiter(
    key_func=get_remote_address,
    app=app,
    default_limits=["200 per day", "50 per hour"]
)

# Enable CORS only for trusted origins
CORS(app, resources={r"/api/*": {"origins": allowed_origins}}, supports_credentials=True)

# Register blueprints AFTER limiter is instantiated
from backend.routes.api import api_bp
app.register_blueprint(api_bp)

@app.route('/')
def index():
    """Serve frontend."""
    return render_template('index.html')

@app.route('/health')
def health_check():
    """Lightweight health check endpoint for UptimeRobot monitoring."""
    return {"status": "ok", "message": "Data Assistant is awake"}, 200

@app.route('/api/version')
def version():
    """Return API version."""
    return {'version': '1.0.0', 'status': 'active'}

@app.errorhandler(404)
def not_found(e):
    """Handle 404 errors."""
    return {'error': 'Endpoint not found'}, 404

@app.errorhandler(500)
def internal_error(e):
    """Handle 500 errors."""
    logger.error(f"Internal server error: {e}")
    return {'error': 'Internal server error'}, 500

if __name__ == '__main__':
    port = int(os.getenv('FLASK_PORT', 5000))
    debug = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    
    logger.info(f"Starting Data Assistant API on port {port}")
    app.run(host='0.0.0.0', port=port, debug=debug)