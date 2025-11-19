"""
Vercel serverless function handler for FastAPI app
"""
import sys
import os
import json
import traceback

# Add parent directory to path so we can import api
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)

# Import app and Mangum
try:
    from api import app
    from mangum import Mangum
    handler = Mangum(app, lifespan="off")
except Exception as e:
    # If import fails, create a minimal error handler
    def handler(event, context):
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "error": "Failed to initialize app",
                "detail": str(e),
                "traceback": traceback.format_exc()
            })
        }

