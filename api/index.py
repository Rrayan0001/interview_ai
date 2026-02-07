import sys
import os

# Add the project root to sys.path so we can import 'backend' and 'pdf_to_text_groq'
# Vercel places the function in /var/task/api usually, so we go up one level
result_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if result_path not in sys.path:
    sys.path.insert(0, result_path)

print("Vercel: Starting handler initialization...")

try:
    from backend.api import app
    print("Vercel: Successfully imported backend.api")
    handler = app
except Exception as e:
    import traceback
    error_trace = traceback.format_exc()
    print(f"Vercel: Import FAILED. Error:\n{error_trace}")
    
    from fastapi import FastAPI
    from fastapi.responses import PlainTextResponse
    
    debug_app = FastAPI()
    
    # Explicitly handle all methods to prevent 405
    @debug_app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD", "PATCH"])
    def catch_all(path: str):
        print(f"Vercel: Catch-all triggered for path: {path}")
        return PlainTextResponse(f"Server Startup Error:\n\n{error_trace}", status_code=500)
        
    handler = debug_app
