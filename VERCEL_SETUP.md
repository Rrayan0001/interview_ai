# Vercel Frontend Setup Guide

## Current Issue: CORS Error

Your frontend is deployed at: `https://interview-ai-one-mocha.vercel.app`
But it's trying to connect to `http://localhost:8000` which won't work in production.

## ✅ Solution: Set Environment Variables

### Step 1: Set Frontend Environment Variable (Vercel)

1. Go to your Vercel project: https://vercel.com/dashboard
2. Select your project: `interview-ai`
3. Go to **Settings** → **Environment Variables**
4. Click **Add New**
5. Add:
   - **Key**: `VITE_BACKEND_URL`
   - **Value**: `https://your-backend-url.railway.app` (or your actual backend URL)
   - **Environment**: Production, Preview, Development (select all)
6. Click **Save**
7. **Redeploy** your project (go to Deployments → click the 3 dots → Redeploy)

### Step 2: Set Backend Environment Variable (Railway/Render)

1. Go to your backend deployment (Railway or Render)
2. Go to **Settings** → **Environment Variables**
3. Add or update:
   - **Key**: `FRONTEND_ORIGIN`
   - **Value**: `https://interview-ai-one-mocha.vercel.app`
   - (You can also add multiple origins separated by commas if needed)
4. **Restart** your backend service

### Step 3: Verify

After setting both:
- Frontend will use `VITE_BACKEND_URL` to connect to your production backend
- Backend will allow CORS requests from your Vercel frontend URL

## 🔍 Quick Check

1. **Frontend (Vercel)**: 
   - Environment Variable: `VITE_BACKEND_URL` = your backend URL
   
2. **Backend (Railway/Render)**:
   - Environment Variable: `FRONTEND_ORIGIN` = `https://interview-ai-one-mocha.vercel.app`

## 📝 Example Values

If your backend is on Railway:
```
VITE_BACKEND_URL = https://interview-api-production.up.railway.app
FRONTEND_ORIGIN = https://interview-ai-one-mocha.vercel.app
```

If your backend is on Render:
```
VITE_BACKEND_URL = https://interview-api.onrender.com
FRONTEND_ORIGIN = https://interview-ai-one-mocha.vercel.app
```

## ⚠️ Important

- After adding environment variables, you **must redeploy** for changes to take effect
- The frontend build happens at deploy time, so `VITE_BACKEND_URL` must be set before building
- The backend CORS is checked at runtime, so `FRONTEND_ORIGIN` can be updated and the service restarted

