# Deployment Guide

## Backend Deployment (FastAPI)

### Required Environment Variables

Set these in your deployment platform:

```
GROQ_API_KEY=your_groq_api_key_here
DATABASE_URL=postgresql://user:password@host/db?sslmode=require
FRONTEND_ORIGIN=https://your-frontend-domain.vercel.app
```

### Deployment Platforms

#### Render / Railway / Fly.io

1. Connect your GitHub repository
2. Set environment variables above
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn api:app --host 0.0.0.0 --port $PORT`

The `Procfile` is already configured for these platforms.

#### Vercel / Netlify Functions

Not recommended for FastAPI. Use Render/Railway instead.

### Verify Deployment

1. Check root endpoint: `https://your-backend-url.com/`
2. Check health: `https://your-backend-url.com/health`
3. Check docs: `https://your-backend-url.com/docs`

---

## Frontend Deployment (React/Vite)

### Required Environment Variables

Create `.env.production` or set in your deployment platform:

```
VITE_BACKEND_URL=https://your-backend-url.com
```

### Deployment Platforms

#### Vercel

1. Connect GitHub repository
2. Root directory: `frontend`
3. Build command: `npm run build`
4. Output directory: `dist`
5. Add environment variable: `VITE_BACKEND_URL`

#### Netlify

1. Connect GitHub repository
2. Base directory: `frontend`
3. Build command: `npm run build`
4. Publish directory: `frontend/dist`
5. Add environment variable: `VITE_BACKEND_URL`

### Verify Deployment

1. Open your frontend URL
2. Check browser console for API calls
3. Test resume upload flow

---

## Troubleshooting 404 Errors

### If you see "404: NOT_FOUND"

1. **Check backend is running:**
   - Visit `https://your-backend-url.com/health`
   - Should return `{"status":"ok","db":"ok"}`

2. **Check frontend backend URL:**
   - Ensure `VITE_BACKEND_URL` is set correctly
   - No trailing slash: `https://api.example.com` (not `https://api.example.com/`)

3. **Check CORS:**
   - Set `FRONTEND_ORIGIN` in backend to your frontend URL
   - Example: `FRONTEND_ORIGIN=https://your-app.vercel.app`

4. **Check endpoint exists:**
   - Visit `https://your-backend-url.com/docs` to see all available endpoints
   - Verify the endpoint you're calling exists

5. **Check network tab:**
   - Open browser DevTools → Network
   - See what URL the frontend is actually calling
   - Verify it matches your backend URL

---

## Common Issues

### CORS Errors

- Set `FRONTEND_ORIGIN` in backend to your exact frontend URL
- Include protocol: `https://your-app.vercel.app` (not just `your-app.vercel.app`)

### Environment Variables Not Loading

- Restart your deployment after adding env vars
- Check variable names are exact (case-sensitive)
- For Vite: Variables must start with `VITE_` to be exposed to frontend

### Database Connection Failed

- Verify `DATABASE_URL` is correct
- Check database allows connections from your deployment platform
- Ensure SSL is enabled: `?sslmode=require`

---

## Quick Test

After deployment, test these endpoints:

```bash
# Backend root
curl https://your-backend-url.com/

# Health check
curl https://your-backend-url.com/health

# API docs
open https://your-backend-url.com/docs
```

