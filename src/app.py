from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from src.config import Config
from src.routes.chat_routes import chat_bp
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

def create_app():
    """Create and configure Flask application"""
    app = Flask(__name__)
    app.config.from_object(Config())
    
    # Enable CORS with better defaults
    CORS(app, resources={
        r"/api/*": {
            "origins": "*",  # Allow all for development
            "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization", "X-Session-ID", "Accept"],
            "expose_headers": ["X-Session-ID"],
            "supports_credentials": True,
            "max_age": 600
        }
    })
    
    # CORS headers middleware for preflight requests
    @app.after_request
    def after_request(response):
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Session-ID')
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        return response
    
    # Initialize JWT (optional)
    jwt = JWTManager(app)
    
    # Register blueprints
    app.register_blueprint(chat_bp)
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            'success': False,
            'error': 'Endpoint not found',
            'code': 'NOT_FOUND'
        }), 404
    
    @app.errorhandler(405)
    def method_not_allowed(error):
        return jsonify({
            'success': False,
            'error': 'Method not allowed',
            'code': 'METHOD_NOT_ALLOWED'
        }), 405
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal server error: {str(error)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'code': 'INTERNAL_SERVER_ERROR'
        }), 500
    
    # Root endpoint
    @app.route('/')
    def index():
        return jsonify({
            'success': True,
            'data': {
                'service': 'SiketBank Chatbot API',
                'version': '1.0.0',
                'endpoints': {
                    'health': '/api/chatbot/health (GET)',
                    'chat': '/api/chatbot/chat (POST)',
                    'history': '/api/chatbot/history (GET)',
                    'feedback': '/api/chatbot/feedback (POST)',
                    'session_start': '/api/chatbot/session/start (POST)'
                },
                'documentation': 'API documentation available at /docs'
            },
            'message': 'Welcome to SiketBank Chatbot API'
        })
    
    # Health endpoint at root level too
    @app.route('/health', methods=['GET'])
    def root_health():
        return jsonify({
            'success': True,
            'data': {
                'status': 'healthy',
                'service': 'SiketBank Chatbot API'
            }
        })
    
    logger.info("Flask application created successfully")
    return app












