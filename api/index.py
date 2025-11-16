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

try:
    from api import app
    from mangum import Mangum
    
    # Wrap FastAPI app with Mangum for AWS Lambda/Vercel compatibility
    mangum_handler = Mangum(app, lifespan="off")
    
except Exception as e:
    print(f"Failed to import app: {e}")
    print(traceback.format_exc())
    mangum_handler = None

def handler(event, context):
    """Vercel serverless function entry point"""
    if mangum_handler is None:
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "error": "Failed to initialize app",
                "detail": "Check server logs for import errors"
            })
        }
    
    try:
        return mangum_handler(event, context)
    except Exception as e:
        print(f"Error in handler: {e}")
        print(traceback.format_exc())
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "error": str(e),
                "detail": "Internal server error"
            })
        }

