import sys
import os

# Add the project root to sys.path so we can import 'backend' and 'pdf_to_text_groq'
# Vercel places the function in /var/task/api usually, so we go up one level
result_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if result_path not in sys.path:
    sys.path.insert(0, result_path)

try:
    from backend.api import app
    handler = app
except Exception as e:
    import traceback
    error_trace = traceback.format_exc()
    from fastapi import FastAPI
    from fastapi.responses import PlainTextResponse
    
    debug_app = FastAPI()
    
    @debug_app.get("/{path:path}")
    def catch_all(path: str):
        return PlainTextResponse(f"Server Startup Error:\n\n{error_trace}", status_code=500)
        
    handler = debug_app
