# Streamlit Cloud Backend Deployment Guide

## ⚠️ Important Note

Streamlit Cloud is designed for Streamlit apps, not FastAPI. However, you can deploy FastAPI on Streamlit Cloud by creating a wrapper. For production, **Railway or Render are recommended**.

## Current Setup

If you've already deployed on Streamlit Cloud, follow these steps:

### Step 1: Get Your Streamlit Cloud URL

Your backend should be accessible at:
```
https://your-app-name.streamlit.app
```

**Note**: Streamlit Cloud serves apps at `/`, so you'll need to create a Streamlit wrapper that runs FastAPI, OR use a different entry point.

### Step 2: Configure Environment Variables in Streamlit Cloud

1. Go to: https://share.streamlit.io/
2. Select your app
3. Go to **Settings** → **Secrets** (or **Environment Variables**)
4. Add these variables:

```
GROQ_API_KEY=your_groq_api_key_here
DATABASE_URL=your_postgresql_connection_string
FRONTEND_ORIGIN=https://interview-ai-one-mocha.vercel.app
```

### Step 3: Update Vercel Frontend

1. Go to Vercel Dashboard
2. Your project → **Settings** → **Environment Variables**
3. Add/Update:
   - **Key**: `VITE_BACKEND_URL`
   - **Value**: `https://your-app-name.streamlit.app` (your Streamlit Cloud URL)
   - **Environments**: Production, Preview, Development
4. **Redeploy** your frontend

## 🔧 Better Solution: Create Streamlit Wrapper for FastAPI

If you want to keep using Streamlit Cloud, create a `streamlit_app.py` file:

```python
import subprocess
import sys
import os

# Start FastAPI server
if __name__ == "__main__":
    os.chdir("backend")
    subprocess.run([sys.executable, "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8501"])
```

But this is **not recommended**. Streamlit Cloud is not ideal for FastAPI.

## ✅ Recommended: Migrate to Railway or Render

For a proper FastAPI backend, use:

### Option 1: Railway (Easiest)
1. Go to https://railway.app
2. New Project → Deploy from GitHub
3. Select repository: `Rrayan0001/interview_ai`
4. **Root Directory**: `backend`
5. Add environment variables:
   - `GROQ_API_KEY`
   - `DATABASE_URL`
   - `FRONTEND_ORIGIN=https://interview-ai-one-mocha.vercel.app`
6. Railway auto-detects FastAPI and deploys
7. Copy the URL (e.g., `https://your-app.up.railway.app`)

### Option 2: Render
1. Go to https://render.com
2. New → Web Service
3. Connect GitHub repo
4. **Root Directory**: `backend`
5. **Build Command**: `pip install -r requirements.txt`
6. **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
7. Add environment variables (same as Railway)

## 📝 Quick Fix for Current Setup

If you want to keep Streamlit Cloud temporarily:

1. **Get your Streamlit URL**: `https://your-app-name.streamlit.app`
2. **In Vercel**: Set `VITE_BACKEND_URL` = your Streamlit URL
3. **In Streamlit Cloud**: Set `FRONTEND_ORIGIN` = `https://interview-ai-one-mocha.vercel.app`
4. **Redeploy both**

**However**, Streamlit Cloud may not properly serve FastAPI endpoints. You'll likely need to migrate to Railway/Render for a working backend.

