"""
Vercel serverless function handler for FastAPI app
"""
import sys
import os
import json

# Add parent directory to path so we can import api
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

try:
    from api import app
    from mangum import Mangum
    
    # Wrap FastAPI app with Mangum for AWS Lambda/Vercel compatibility
    handler = Mangum(app, lifespan="off")
    
    # Vercel Python runtime expects this format
    def handler_wrapper(event, context):
        """Vercel serverless function entry point"""
        try:
            return handler(event, context)
        except Exception as e:
            import traceback
            print(f"Error in handler: {e}")
            print(traceback.format_exc())
            return {
                "statusCode": 500,
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps({"error": str(e), "detail": "Internal server error"})
            }
    
    # Export for Vercel
    handler = handler_wrapper
    
except Exception as e:
    import traceback
    import json
    print(f"Failed to import app: {e}")
    print(traceback.format_exc())
    
    def handler(event, context):
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "error": "Failed to initialize app",
                "detail": str(e)
            })
        }

