#!/usr/bin/env python3
"""Main entry point for running the Data Assistant.

Supports both CLI and web server modes:
- CLI Mode: Direct terminal interaction
- Web Mode: Flask API server with frontend
"""

import os
import sys
import argparse
from dotenv import load_dotenv

load_dotenv()

def run_cli_mode():
    """Run Data Assistant in interactive CLI mode."""
    from backend.agent.data_assistant import DataAssistant
    from backend.utils.logger import setup_logger
    
    logger = setup_logger('cli')
    logger.info("Starting Data Assistant in CLI mode...")
    
    try:
        assistant = DataAssistant()
        
        print("\n" + "="*60)
        print("Enterprise Text-to-SQL Data Assistant")
        print("="*60)
        print("Type your question or 'quit' to exit\n")
        
        while True:
            question = input("You: ").strip()
            
            if question.lower() in ['quit', 'exit', 'q']:
                print("\nGoodbye!")
                break
            
            if not question:
                continue
            
            result = assistant.answer_question(question)
            print(f"\nAssistant: {result['answer']}\n")
    
    except Exception as e:
        logger.error(f"Error in CLI mode: {e}")
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

def run_web_mode():
    """Run Data Assistant as web server."""
    from app import app
    from backend.utils.logger import setup_logger
    
    logger = setup_logger('web')
    port = int(os.getenv('FLASK_PORT', 5000))
    
    logger.info(f"Starting Data Assistant in Web mode on port {port}...")
    print(f"\nWeb UI available at http://localhost:{port}")
    
    app.run(
        host='0.0.0.0',
        port=port,
        debug=os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
    )

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Enterprise Text-to-SQL Data Assistant'
    )
    parser.add_argument(
        '--mode',
        choices=['cli', 'web'],
        default='web',
        help='Run mode: cli for terminal, web for web server (default: web)'
    )
    
    args = parser.parse_args()
    
    # Verify environment
    if not os.getenv('DATABASE_URL'):
        print("Error: DATABASE_URL not set. Please check your .env file.", file=sys.stderr)
        sys.exit(1)

    if not os.getenv('GEMINI_API_KEY'):
        print("Warning: GEMINI_API_KEY is not set. Common dashboard questions still work; custom questions will be unavailable.", file=sys.stderr)
    
    # Run selected mode
    if args.mode == 'cli':
        run_cli_mode()
    else:
        run_web_mode()

if __name__ == '__main__':
    main()
