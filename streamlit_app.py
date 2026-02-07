"""
Streamlit wrapper for FastAPI backend on Streamlit Cloud.
⚠️ IMPORTANT: Streamlit Cloud cannot serve FastAPI REST endpoints.
This is just a status page. For production, deploy backend on Railway/Render.
"""

import os
import sys
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
st.error("""
⚠️ **Streamlit Cloud Limitation**: Streamlit Cloud cannot serve FastAPI REST endpoints.

**Your FastAPI endpoints will NOT work on Streamlit Cloud.**

For production, deploy your backend on:
- **Railway** (Recommended): https://railway.app  
- **Render**: https://render.com
""")

# Display environment status
st.sidebar.header("Environment Status")
groq_key = os.getenv("GROQ_API_KEY")
db_url = os.getenv("DATABASE_URL")
frontend_origin = os.getenv("FRONTEND_ORIGIN")

st.sidebar.write("**GROQ_API_KEY:**", "✅ Set" if groq_key else "❌ Missing")
st.sidebar.write("**DATABASE_URL:**", "✅ Set" if db_url else "⚠️ Optional")
st.sidebar.write("**FRONTEND_ORIGIN:**", "✅ Set" if frontend_origin else "⚠️ Not set")

# Try to import FastAPI app (for validation)
try:
    from backend.main import app
    st.success("✅ FastAPI app can be imported")
    
    # Display available endpoints (for reference)
    st.subheader("API Endpoints (when deployed on Railway/Render)")
    endpoints = [
        ("GET", "/", "API info"),
        ("GET", "/health", "Health check"),
        ("POST", "/parse", "Parse resume PDF"),
        ("POST", "/upload-resume", "Upload resume (alias)"),
        ("POST", "/users", "Create/get user"),
        ("POST", "/select_questions", "Select questions"),
        ("POST", "/responses", "Save responses"),
        ("POST", "/generate-report", "Generate report"),
    ]
    
    for method, path, desc in endpoints:
        st.code(f"{method} {path} - {desc}")
        
except Exception as e:
    st.error(f"❌ Failed to import FastAPI app: {str(e)}")
    st.exception(e)

# Migration guide
st.subheader("🚀 Quick Migration to Railway")
st.markdown("""
1. Go to https://railway.app
2. **New Project** → **Deploy from GitHub**
3. Select: `Rrayan0001/interview_ai`
4. **Root Directory**: `backend`
5. Add environment variables:
   - `GROQ_API_KEY`
   - `DATABASE_URL`
   - `FRONTEND_ORIGIN=https://interview-ai-one-mocha.vercel.app`
6. Copy the Railway URL
7. Update Vercel's `VITE_BACKEND_URL` to the Railway URL
""")
