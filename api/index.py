import sys
import os

# Add the project root to sys.path so we can import 'backend' and 'pdf_to_text_groq'
# Vercel places the function in /var/task/api usually, so we go up one level
result_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if result_path not in sys.path:
    sys.path.insert(0, result_path)

from backend.api import app

# Vercel supports FastAPI/ASGI natively. 
# We just need to expose the 'app' object.
handler = app
