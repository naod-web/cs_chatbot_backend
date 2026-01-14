#!/usr/bin/env python3
import sys
import os

# Add src to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.app import create_app
from src.config import Config
from src.utils.logger import setup_logger

logger = setup_logger(__name__)

def main():
    """Main entry point for the application"""
    
    app = create_app()
    config = Config()
    
    print("=" * 70)
    print("S I K E T B A N K   C H A T B O T   A P I")
    print("=" * 70)
    print(f"Version: 1.0.0")
    print(f"Python: {sys.version.split()[0]}")
    print(f"Environment: {'Development' if config.DEBUG else 'Production'}")
    print(f"Database: {config.DB_SERVER}:{config.DB_PORT}/{config.DB_NAME}")
    print(f"Server: http://localhost:{config.PORT}")
    print(f"API Endpoint: http://localhost:{config.PORT}/api/chatbot/chat")
    print("=" * 70)
    print("Available Endpoints:")
    print(f"  GET  /                    - API information")
    print(f"  GET  /api/chatbot/health  - Health check")
    print(f"  POST /api/chatbot/chat    - Chat with bot")
    print(f"  GET  /api/chatbot/history - Chat history")
    print(f"  POST /api/chatbot/feedback- Submit feedback")
    print("=" * 70)
    print("Press Ctrl+C to stop the server")
    print("=" * 70)
    
    try:
        if config.DEBUG:
            # Development server
            app.run(
                host='0.0.0.0',
                port=config.PORT,
                debug=True,
                threaded=True
            )
        else:
            # Production server (using waitress for Windows compatibility)
            from waitress import serve
            serve(
                app,
                host='0.0.0.0',
                port=config.PORT,
                threads=10
            )
            
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        print("\nServer stopped.")
    except Exception as e:
        logger.error(f"Failed to start server: {str(e)}")
        print(f"\nError starting server: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()