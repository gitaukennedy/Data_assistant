"""Flask API routes for Data Assistant."""
from flask import Blueprint, current_app, request, jsonify
from backend.agent.data_assistant import DataAssistant
from backend.utils.logger import setup_logger

api_bp = Blueprint('api', __name__, url_prefix='/api')
logger = setup_logger('api')

# Initialize assistant (singleton)
_assistant = None

def get_assistant():
    """Get or create DataAssistant instance."""
    global _assistant
    if _assistant is None:
        _assistant = DataAssistant()
    return _assistant


def internal_error(message: str, error: Exception):
    """Log implementation details without exposing them to API users."""
    logger.exception(message)
    response = {'error': 'An internal error occurred', 'status': 'error'}
    if current_app.config.get('EXPOSE_ERROR_DETAILS'):
        response['details'] = str(error)
    return jsonify(response), 500


@api_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    try:
        assistant = get_assistant()
        db_healthy = assistant.db_manager.health_check()
        return jsonify({
            'status': 'healthy' if db_healthy else 'degraded',
            'database': 'connected' if db_healthy else 'disconnected'
        }), 200 if db_healthy else 503
    except Exception as e:
        logger.exception('Health check failed')
        return jsonify({'status': 'unhealthy'}), 503


@api_bp.route('/ask', methods=['POST'])
def ask_question():
    """Main endpoint to ask questions to the data assistant."""
    try:
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            return jsonify({'error': 'Request body must be a JSON object'}), 400

        question = data.get('question', '').strip()
        
        if not question:
            return jsonify({'error': 'Question cannot be empty'}), 400
        
        if len(question) > 500:
            return jsonify({'error': 'Question too long (max 500 characters)'}), 400
        
        logger.info(f"Processing question: {question}")
        assistant = get_assistant()
        result = assistant.answer_question(question)

        return jsonify(result), 200
    except Exception as e:
        logger.exception('Error in /ask endpoint')
        return jsonify({
            'status': 'success',
            'question': question if 'question' in locals() else '',
            'answer': (
                "I cannot reach the assistant service right now. "
                "Please try again or ask about revenue, products, customers, or regions."
            ),
            'fallback': True,
        }), 200


@api_bp.route('/database/info', methods=['GET'])
def get_database_info():
    """Get database schema information."""
    try:
        assistant = get_assistant()
        info = assistant.get_database_info()
        return jsonify(info), 200
    except Exception as e:
        return internal_error('Error fetching database info', e)


@api_bp.route('/database/tables', methods=['GET'])
def get_tables():
    """Get list of available tables."""
    try:
        assistant = get_assistant()
        info = assistant.get_database_info()
        return jsonify({'tables': info.get('tables', [])}), 200
    except Exception as e:
        return internal_error('Error fetching tables', e)