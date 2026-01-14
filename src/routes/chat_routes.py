from flask import Blueprint, request, jsonify
from src.services.chatbot_service import ChatbotService
from src.utils.logger import setup_logger
from datetime import datetime

logger = setup_logger(__name__)

chat_bp = Blueprint('chat', __name__, url_prefix='/api/chatbot')
chatbot_service = ChatbotService()

@chat_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'SiketBank Chatbot API',
        'version': '1.0.0',
        'timestamp': datetime.now().isoformat(),
        'database': 'connected'  # You can add actual DB check
    })

@chat_bp.route('/chat', methods=['POST'])
def chat():
    """Main chat endpoint"""
    try:
        data = request.get_json()
        
        # Validate request
        if not data or 'message' not in data:
            return jsonify({
                'success': False,
                'error': 'Message is required',
                'code': 'MISSING_MESSAGE'
            }), 400
        
        message = data.get('message', '').strip()
        if not message:
            return jsonify({
                'success': False,
                'error': 'Message cannot be empty',
                'code': 'EMPTY_MESSAGE'
            }), 400
        
        # Get optional parameters
        session_id = data.get('session_id')
        customer_id = data.get('customer_id', 'anonymous')
        context = data.get('context', {})
        
        # Process message
        response = chatbot_service.process_message(
            message, session_id, customer_id, context
        )
        
        return jsonify({
            'success': True,
            'data': response
        })
        
    except Exception as e:
        logger.error(f"Chat endpoint error: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'code': 'INTERNAL_ERROR'
        }), 500

@chat_bp.route('/history', methods=['GET'])
def get_history():
    """Get chat history"""
    try:
        customer_id = request.args.get('customer_id', 'anonymous')
        session_id = request.args.get('session_id')
        limit = min(int(request.args.get('limit', 20)), 100)  # Max 100
        
        history = chatbot_service.get_chat_history(customer_id, session_id, limit)
        
        return jsonify({
            'success': True,
            'data': {
                'customer_id': customer_id,
                'session_id': session_id,
                'history': history,
                'count': len(history)
            }
        })
        
    except Exception as e:
        logger.error(f"History endpoint error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@chat_bp.route('/feedback', methods=['POST'])
def submit_feedback():
    """Submit feedback for a chat interaction"""
    try:
        data = request.get_json()
        
        required_fields = ['log_id', 'rating']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}',
                    'code': f'MISSING_{field.upper()}'
                }), 400
        
        log_id = data['log_id']
        rating = data['rating']
        comments = data.get('comments')
        
        if not isinstance(rating, int) or not (1 <= rating <= 5):
            return jsonify({
                'success': False,
                'error': 'Rating must be an integer between 1 and 5',
                'code': 'INVALID_RATING'
            }), 400
        
        success = chatbot_service.add_feedback(log_id, rating, comments)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Feedback submitted successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to submit feedback',
                'code': 'FEEDBACK_FAILED'
            }), 500
            
    except Exception as e:
        logger.error(f"Feedback endpoint error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@chat_bp.route('/session/start', methods=['POST'])
def start_session():
    """Start a new chat session"""
    try:
        data = request.get_json() or {}
        customer_id = data.get('customer_id', 'anonymous')
        
        import uuid
        session_id = str(uuid.uuid4())
        
        return jsonify({
            'success': True,
            'data': {
                'session_id': session_id,
                'customer_id': customer_id,
                'timestamp': datetime.now().isoformat(),
                'message': 'Session started successfully'
            }
        })
        
    except Exception as e:
        logger.error(f"Start session error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500