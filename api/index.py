"""
Vercel serverless function handler for FastAPI app
"""
import sys
import os
import json
import traceback

# Log startup for debugging
print("=" * 50)
print("Vercel handler starting...")
print(f"Python version: {sys.version}")
print(f"Current directory: {os.getcwd()}")
print(f"Python path: {sys.path[:3]}")

# Add parent directory to path so we can import api
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.insert(0, parent_dir)
    print(f"Added to path: {parent_dir}")

print("Attempting to import api module...")
try:
    from api import app
    print("✓ Successfully imported app")
except Exception as e:
    print(f"✗ Failed to import api: {e}")
    print(traceback.format_exc())
    app = None

print("Attempting to import Mangum...")
try:
    from mangum import Mangum
    print("✓ Successfully imported Mangum")
except Exception as e:
    print(f"✗ Failed to import Mangum: {e}")
    print(traceback.format_exc())
    Mangum = None

if app and Mangum:
    try:
        mangum_handler = Mangum(app, lifespan="off")
        print("✓ Successfully created Mangum handler")
    except Exception as e:
        print(f"✗ Failed to create Mangum handler: {e}")
        print(traceback.format_exc())
        mangum_handler = None
else:
    mangum_handler = None

print("=" * 50)

def handler(event, context):
    """Vercel serverless function entry point"""
    print(f"\n[Handler] Request received: {event.get('path', 'unknown')}")
    print(f"[Handler] Method: {event.get('httpMethod', 'unknown')}")
    
    if mangum_handler is None:
        error_msg = "Failed to initialize app - check import logs"
        print(f"[Handler] ERROR: {error_msg}")
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "error": "Failed to initialize app",
                "detail": error_msg,
                "traceback": traceback.format_exc() if app is None or Mangum is None else None
            })
        }
    
    try:
        print("[Handler] Calling mangum_handler...")
        result = mangum_handler(event, context)
        print(f"[Handler] Success: {result.get('statusCode', 'unknown')}")
        return result
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"[Handler] EXCEPTION: {e}")
        print(error_trace)
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({
                "error": str(e),
                "detail": "Internal server error",
                "type": type(e).__name__,
                "traceback": error_trace
            })
        }

