import sys
import os

# Add the project root to sys.path so we can import 'backend' and 'pdf_to_text_groq'
# Vercel places the function in /var/task/api usually, so we go up one level
result_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if result_path not in sys.path:
    sys.path.insert(0, result_path)

from backend.api import app

# Vercel needs 'app' to be exposed
# But for serverless function strict compat, we use Mangum if needed, 
# or Vercel's python runtime can handle FastAPI directly if we expose 'app'.
# However, for advanced features like streaming, Mangum is safer.
try:
    from mangum import Mangum
    handler = Mangum(app, lifespan="off")
except ImportError:
    # Fallback if Mangum not present (though it should be in requirements.txt)
    handler = app
