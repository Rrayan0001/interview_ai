# Railway Backend Setup - Final Configuration

## ✅ Backend Deployed on Railway

Now you need to connect your Vercel frontend to your Railway backend.

## Step 1: Get Your Railway Backend URL

1. Go to https://railway.app
2. Select your project
3. Click on your service
4. Go to **Settings** → **Networking**
5. Copy your **Public Domain** (e.g., `https://your-app.up.railway.app`)

**Your Railway URL should look like:**
```
https://your-app-name.up.railway.app
```

## Step 2: Configure Railway Environment Variables

1. In Railway, go to your service
2. Click on **Variables** tab
3. Add/Update these variables:

```
GROQ_API_KEY=your_groq_api_key_here
DATABASE_URL=your_postgresql_connection_string
FRONTEND_ORIGIN=https://interview-ai-one-mocha.vercel.app
```

**Important**: Make sure `FRONTEND_ORIGIN` is set to your exact Vercel URL.

## Step 3: Configure Vercel Frontend

1. Go to https://vercel.com/dashboard
2. Select your project: `interview-ai`
3. Go to **Settings** → **Environment Variables**
4. Add/Update:
   - **Key**: `VITE_BACKEND_URL`
   - **Value**: Your Railway URL (e.g., `https://your-app.up.railway.app`)
   - **Environments**: Production, Preview, Development (select all)
5. Click **Save**
6. **Redeploy**: Go to **Deployments** → Click the 3 dots (⋯) on the latest deployment → **Redeploy**

## Step 4: Verify Connection

### Test Backend Health:
```bash
curl https://your-railway-url.up.railway.app/health
```

Should return: `{"status":"ok","db":"ok"}`

### Test CORS:
```bash
curl -H "Origin: https://interview-ai-one-mocha.vercel.app" \
     https://your-railway-url.up.railway.app/health
```

Should include: `access-control-allow-origin: https://interview-ai-one-mocha.vercel.app`

## Step 5: Test Frontend

1. Visit: https://interview-ai-one-mocha.vercel.app
2. Try uploading a resume
3. Check browser console for any errors

## 🔧 Troubleshooting

### CORS Error?
- Verify `FRONTEND_ORIGIN` in Railway matches your Vercel URL exactly
- Restart Railway service after adding environment variables

### 404 Errors?
- Check that Railway service is running
- Verify the Railway URL is correct in Vercel's `VITE_BACKEND_URL`

### Environment Variables Not Working?
- In Vercel: Redeploy after adding `VITE_BACKEND_URL` (Vite env vars are embedded at build time)
- In Railway: Restart service after adding variables

## ✅ Checklist

- [ ] Railway backend deployed and running
- [ ] Railway environment variables set (GROQ_API_KEY, DATABASE_URL, FRONTEND_ORIGIN)
- [ ] Railway URL copied
- [ ] Vercel `VITE_BACKEND_URL` set to Railway URL
- [ ] Vercel frontend redeployed
- [ ] Backend health check works
- [ ] Frontend can connect to backend

