"""
Streamlit wrapper for FastAPI backend.
This file allows Streamlit Cloud to serve the FastAPI backend.
"""

import os
import sys
import subprocess
import streamlit as st

# Add backend directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "backend"))

# Set page config
st.set_page_config(
    page_title="AI Interview Bot API",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 AI Interview Bot - Backend API")
st.info("""
This is the FastAPI backend server.
The API endpoints are available at the same URL with the following paths:
- `/health` - Health check
- `/parse` - Parse resume PDF
- `/users` - Create/get user
- `/select_questions` - Get questions
- `/generate_report` - Generate report
""")

# Check if we're in Streamlit Cloud
if os.getenv("STREAMLIT_SERVER_PORT"):
    st.success("✅ Backend is running on Streamlit Cloud")
    st.code("""
API Base URL: https://{your-app-name}.streamlit.app

Example endpoints:
- https://{your-app-name}.streamlit.app/health
- https://{your-app-name}.streamlit.app/parse
    """)
else:
    st.warning("Running in local mode")

# Display environment status
st.sidebar.header("Environment Status")
groq_key = os.getenv("GROQ_API_KEY")
db_url = os.getenv("DATABASE_URL")
frontend_origin = os.getenv("FRONTEND_ORIGIN")

st.sidebar.write("**GROQ_API_KEY:**", "✅ Set" if groq_key else "❌ Missing")
st.sidebar.write("**DATABASE_URL:**", "✅ Set" if db_url else "⚠️ Optional")
st.sidebar.write("**FRONTEND_ORIGIN:**", "✅ Set" if frontend_origin else "⚠️ Not set")

# Import and expose FastAPI app
try:
    from backend.main import app
    st.success("✅ FastAPI app loaded successfully")
    
    # Display available endpoints
    st.subheader("Available Endpoints")
    endpoints = [
        ("GET", "/", "API info"),
        ("GET", "/health", "Health check"),
        ("POST", "/parse", "Parse resume PDF"),
        ("POST", "/upload-resume", "Upload resume (alias)"),
        ("POST", "/users", "Create/get user"),
        ("POST", "/select_questions", "Select questions"),
        ("POST", "/responses", "Save responses"),
        ("POST", "/generate-report", "Generate report"),
        ("POST", "/generate_report", "Generate report (alias)"),
    ]
    
    for method, path, desc in endpoints:
        st.code(f"{method} {path} - {desc}")
        
except Exception as e:
    st.error(f"❌ Failed to load FastAPI app: {str(e)}")
    st.exception(e)

# Note about Streamlit Cloud limitations
st.warning("""
⚠️ **Important Note**: Streamlit Cloud is not ideal for FastAPI backends.
For production, consider migrating to Railway or Render for better performance.
""")

