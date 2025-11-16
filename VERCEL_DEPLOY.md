# Vercel Deployment Guide

## Quick Fix for FUNCTION_INVOCATION_FAILED

### 1. Check Vercel Logs
- Go to: Vercel Dashboard → Your Project → Functions → View Logs
- Look for Python import errors, missing dependencies, or environment variable issues

### 2. Set Environment Variables in Vercel
**Project Settings → Environment Variables:**
```
GROQ_API_KEY=your_groq_key
DATABASE_URL=your_neon_url
FRONTEND_ORIGIN=https://your-frontend.vercel.app
```

### 3. Verify File Structure
Your project should have:
```
/
├── api/
│   └── index.py          # Vercel serverless handler
├── api.py                # FastAPI app
├── vercel.json           # Vercel config
├── requirements.txt      # Python dependencies
└── ...
```

### 4. Common Issues

#### Missing Dependencies
If you see `ModuleNotFoundError`:
- Check `requirements.txt` includes all packages
- Redeploy after adding dependencies

#### Environment Variables Not Loading
- Variables must be set in Vercel dashboard (not just `.env`)
- Redeploy after adding env vars
- Check variable names are exact (case-sensitive)

#### Import Errors
- Ensure `api.py` is in the root directory
- Check `api/index.py` path imports are correct

### 5. Test Locally with Vercel CLI
```bash
npm i -g vercel
vercel dev
```

This will show errors before deploying.

### 6. Alternative: Deploy Backend Separately

**Recommended:** Deploy FastAPI backend to Render/Railway instead of Vercel:

1. **Backend (Render/Railway):**
   - Connect GitHub repo
   - Set env vars
   - Use `Procfile`: `web: uvicorn api:app --host 0.0.0.0 --port $PORT`

2. **Frontend (Vercel):**
   - Deploy `frontend/` directory
   - Set `VITE_BACKEND_URL` to your Render/Railway URL

This is more reliable than serverless functions for FastAPI.

---

## If Still Failing

Share the exact error from Vercel logs and I'll help debug.

