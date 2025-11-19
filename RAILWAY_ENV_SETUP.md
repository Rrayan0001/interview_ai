# Railway Environment Variables Setup

## ⚠️ IMPORTANT: Backend is on Railway, NOT Vercel

Your backend API is deployed on **Railway**, not Vercel. The `GROQ_API_KEY` must be set in **Railway**, not Vercel.

## Step-by-Step: Set GROQ_API_KEY in Railway

### 1. Go to Railway Dashboard
- Visit: https://railway.app
- Log in to your account
- Select your project

### 2. Open Your Service
- Click on your backend service (the one that's running FastAPI)

### 3. Go to Variables Tab
- Click on the **Variables** tab in your service
- This is where you set environment variables

### 4. Add GROQ_API_KEY
Click **"New Variable"** and add:

```
Variable Name: GROQ_API_KEY
Value: [Your Groq API Key - get it from console.groq.com]
```

**Important**: Railway will automatically restart your service when you add/update variables.

### 5. Verify Other Required Variables

Make sure these are also set:

```
GROQ_API_KEY=[Your Groq API Key]
DATABASE_URL=[Your PostgreSQL connection string]
FRONTEND_ORIGIN=https://interview-ai-one-mocha.vercel.app
```

### 6. Test the Backend

After setting the variables, test if it works:

```bash
curl -X POST https://web-production-dad96.up.railway.app/generate_report \
  -H "Content-Type: application/json" \
  -d '{"answers":[],"totals":{"overall":1},"behavior":{"accuracy":3},"profile":{}}'
```

If `GROQ_API_KEY` is set correctly, you should get a generated report instead of "GROQ_API_KEY not configured."

## 🔍 How to Verify

1. **Check Railway Logs**:
   - Go to Railway → Your Service → **Deployments** tab
   - Click on the latest deployment
   - Check the logs for any errors

2. **Test the Endpoint**:
   - Use the curl command above
   - Or visit: https://web-production-dad96.up.railway.app/health
   - Should return: `{"status":"ok","db":"ok"}`

3. **Check in Code**:
   The backend code checks for the key like this:
   ```python
   key = get_groq_key()  # Gets from os.environ.get("GROQ_API_KEY")
   if not key:
       return {"report_markdown": "# Report Generation Unavailable\n\nGROQ_API_KEY not configured."}
   ```

## ⚠️ Common Mistakes

1. **Setting it in Vercel instead of Railway** ❌
   - Vercel is for frontend only
   - Backend runs on Railway

2. **Typo in variable name** ❌
   - Must be exactly: `GROQ_API_KEY`
   - Case-sensitive

3. **Not redeploying** ❌
   - Railway auto-restarts, but if it doesn't, manually restart the service

4. **Wrong project/service** ❌
   - Make sure you're adding the variable to the **backend service**, not a different service

## ✅ Quick Checklist

- [ ] Logged into Railway
- [ ] Selected the correct project
- [ ] Selected the backend service (FastAPI)
- [ ] Went to Variables tab
- [ ] Added `GROQ_API_KEY` with your actual key
- [ ] Railway service restarted automatically
- [ ] Tested the `/generate_report` endpoint
- [ ] Report generation now works

## 📝 Your Current Setup

- **Frontend**: Vercel (https://interview-ai-one-mocha.vercel.app)
- **Backend**: Railway (https://web-production-dad96.up.railway.app)
- **API Key Location**: Railway environment variables

