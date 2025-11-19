# Complete Deployment Guide

## Architecture

- **Frontend**: React/Vite (Vercel)
- **Backend**: FastAPI (Railway/Render)
- **Communication**: REST API via `fetch`

---

## 🚀 Local Development

### Backend Setup

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
```

Backend runs at: `http://localhost:8000`

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Frontend runs at: `http://localhost:10000` (or port shown in terminal)

### Environment Variables (Local)

Create `frontend/.env.local`:
```
VITE_BACKEND_URL=http://localhost:8000
```

---

## 📦 Production Deployment

### Step 1: Deploy Backend (Railway/Render)

#### Option A: Railway (Recommended)

1. Go to [railway.app](https://railway.app)
2. **New Project** → **Deploy from GitHub**
3. Select your repository
4. **Settings** → **Root Directory**: Set to `backend`
5. **Variables** → Add:
   ```
   GROQ_API_KEY=your_groq_key
   DATABASE_URL=your_neon_postgres_url
   FRONTEND_ORIGIN=https://your-frontend.vercel.app
   ```
6. Railway auto-detects FastAPI and deploys
7. Copy your production URL (e.g., `https://api-production.up.railway.app`)

#### Option B: Render

1. Go to [render.com](https://render.com)
2. **New** → **Web Service**
3. Connect GitHub repository
4. **Root Directory**: `backend`
5. **Build Command**: `pip install -r requirements.txt`
6. **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
7. Add environment variables (same as Railway)
8. Deploy and copy URL

---

### Step 2: Deploy Frontend (Vercel)

1. Go to [vercel.com](https://vercel.com)
2. **New Project** → Import from GitHub
3. Select your repository
4. **Root Directory**: `frontend`
5. **Framework Preset**: Vite
6. **Environment Variables** → Add:
   ```
   VITE_BACKEND_URL=https://your-backend-url.railway.app
   ```
7. **Deploy**

---

## ✅ Verification

### Test Backend

```bash
curl https://your-backend-url.railway.app/health
```

Should return: `{"status":"ok","db":"ok"}`

### Test Frontend

1. Visit your Vercel URL
2. Upload a resume PDF
3. Verify it parses correctly

---

## 🔧 Troubleshooting

### Backend Issues

- **Import errors**: Ensure `pdf_to_text_groq.py` is in the parent directory (root)
- **Missing dependencies**: Check `backend/requirements.txt` includes all packages
- **CORS errors**: Set `FRONTEND_ORIGIN` to your exact frontend URL

### Frontend Issues

- **API not connecting**: Verify `VITE_BACKEND_URL` is set correctly in Vercel
- **Build errors**: Check Node.js version (Vite requires Node 18+)

---

## 📝 Environment Variables Summary

### Backend (Railway/Render)
- `GROQ_API_KEY` - Required for resume parsing
- `DATABASE_URL` - Optional, for user persistence
- `FRONTEND_ORIGIN` - Your Vercel frontend URL

### Frontend (Vercel)
- `VITE_BACKEND_URL` - Your Railway/Render backend URL

---

## 🎯 Quick Start Checklist

- [ ] Backend deployed on Railway/Render
- [ ] Backend environment variables set
- [ ] Backend health check returns `{"status":"ok"}`
- [ ] Frontend deployed on Vercel
- [ ] Frontend `VITE_BACKEND_URL` set to backend URL
- [ ] Test resume upload works
- [ ] Test report generation works

---

## 📚 API Endpoints

- `GET /` - API info
- `GET /health` - Health check
- `POST /upload-resume` - Parse resume PDF
- `POST /evaluate` - Evaluate candidate
- `POST /generate-report` - Generate career report
