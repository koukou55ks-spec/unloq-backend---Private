"""
収益化バージョン起動スクリプト
"""
import os
import sys
import logging

# Add app directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.main_monetized import app

if __name__ == '__main__':
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

  # Run the application
    port = int(os.getenv('PORT', 8080))
    app.run(
        host='0.0.0.0',
        port=port,
        debug=False
    )
